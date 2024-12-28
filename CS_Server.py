import socket
import time
import json
import random
import hashlib

# 服务器类
class Server:
    # ---------------------上位机初始化----------------------
    def __init__(self, host='127.0.0.1', port=8081):
        self.host = host
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        self.clients = None
        self.alarm_active = False
        self.last_sensor_data = {}
        self.private_massage_checksum = 0

    # --------------------------上位机开机----------------------------
    def start(self):
        print(f"【启动】服务器启动，监听 {self.host}:{self.port}...")
        while True:
            client_socket, client_address = self.server_socket.accept()
            print(f"【启动】新客户端连接：{client_address}")
            self.clients = client_socket
            # 多线程
            self.handle_client(client_socket)

    # ------------------------校验方法-------------------------
    def compute_checksum(self, data):
        """计算数据的校验和（使用MD5）"""
        if isinstance(data, dict):
            data = json.dumps(data)
        return hashlib.md5(data.encode('utf-8')).hexdigest()

    def extract_data_and_checksum(self, message):
        """提取数据和校验和"""
        if "|" in message:
            data, checksum = message.rsplit("|", 1)
            data = json.loads(data)
            return data, checksum
        return {}, ""

    # -----------------------接收处理下位机数据-------------------
    def handle_client(self, client_socket):
        while True:
            try:
                data = client_socket.recv(1024)
                if not data:
                    continue

                # 接收并校验下位机数据
                message = data.decode('utf-8')
                print(f"【接收】收到下位机数据: {message}")
                sensor_data, received_checksum = self.extract_data_and_checksum(message)
                computed_checksum = self.compute_checksum(sensor_data)


                received_checksum = '123'


                # 进一步检查校验信息
                if self.private_massage_checksum == computed_checksum or computed_checksum == '\"':
                    print("【校验】数据曾校验！读取下一个下位机数据！")
                    self.send_command_to_client('next_message', True)
                    break

                elif received_checksum != computed_checksum:
                    print("【校验】数据校验失败！请求下位机重新发送数据！")
                    self.send_command_to_client('resend', True)
                    while True:
                        try:
                            # 接收下位机的响应
                            data = self.clients.recv(1024)
                            if not data:
                                time.sleep(1)
                                continue
                            message = data.decode('utf-8')
                            print(f"【接收】收到下位机数据: {message}")
                            sensor_data2, received_checksum = self.extract_data_and_checksum(message)
                            # 校验响应数据
                            computed_checksum = self.compute_checksum(sensor_data2)
                            if received_checksum != computed_checksum:
                                print("【警告】上位机接收到的响应校验失败，继续重发命令...")
                                self.send_command_to_client('fan', 'both_on')
                                continue
                            if sensor_data2.get('action') == 'true':
                                print(f"【接收】重新发送数据成功")

                            break
                        except Exception as e:
                            print(f"【警告】发送指令时发生错误: {e}")
                            break
                    continue

                if received_checksum == computed_checksum:
                    self.private_massage_checksum = computed_checksum
                    print("【校验】数据校验成功！执行数据处理程序！")

                    # 数据分析
                    self.process_sensor_data(sensor_data)

                    # 发送确认报文
                    if self.alarm_active is True:
                        print('【发送】数据分析/指令发送完毕！等待下位机手动输入解除报警指令...')
                        # self.send_command_to_client('wait_alarm_message', True)
                        continue
                    elif self.alarm_active is False:
                        self.send_command_to_client('success', True)
                        # self.alarm_active = False
                        print('【发送】数据分析/指令发送完毕！等待接收下一组信息...')
                        print('---------------------------------------------------')

            except Exception as e:
                print(f"【处理】处理客户端数据时出错: {e}")
                break

        client_socket.close()

    # ------------------------数据处理-------------------------
    def process_sensor_data(self, sensor_data):


       # sensor_data['timestamp'] -= 3


        """处理下位机上传的传感器数据"""
        if 'alarm_message' in sensor_data:
            # self.send_command_to_client('success', True)
            self.alarm_active = False
            print('【发送】警报已解除！')
            # print('---------------------------------------------------')

        # 时间同步
        elif abs(time.time() - sensor_data['timestamp']) > 2:
            print("【警告】时间误差过大，要求下位机校时！")
            self.send_command_to_client('sync_time', time.time())
            while True:
                try:
                    # 接收下位机的响应
                    data = self.clients.recv(1024)
                    if not data:
                        time.sleep(1)
                        continue
                    message = data.decode('utf-8')
                    print(f"【接收】收到下位机数据: {message}")
                    sensor_data2, received_checksum = self.extract_data_and_checksum(message)
                    # 校验响应数据
                    computed_checksum = self.compute_checksum(sensor_data2)
                    if received_checksum != computed_checksum:
                        print("【警告】上位机接收到的响应校验失败，继续重发命令...")
                        self.send_command_to_client('fan', 'both_on')
                        continue
                    if sensor_data2.get('action') == 'true':
                        print(f"【接收】下位机时间矫正成功成功")

                    break
                except Exception as e:
                    print(f"【警告】发送指令时发生错误: {e}")
                    break

        elif sensor_data['fan1'] == 0 and sensor_data['fan2'] == 0:
            print("【报警】报警：主备风机都关闭！")
            self.alarm_active = True
            self.send_command_to_client('alarm', True)

        elif sensor_data['methane'] > 5.0:
            print("【报警】甲烷浓度过高，断电开采设备！")
            self.send_command_to_client('cut_power', True)
            while True:
                try:
                    # 接收下位机的响应
                    data = self.clients.recv(1024)
                    if not data:
                        time.sleep(1)
                        continue
                    message = data.decode('utf-8')
                    print(f"【接收】收到下位机数据: {message}")
                    sensor_data2, received_checksum = self.extract_data_and_checksum(message)
                    # 校验响应数据
                    computed_checksum = self.compute_checksum(sensor_data2)
                    if received_checksum != computed_checksum:
                        print("【警告】上位机接收到的响应校验失败，继续重发命令...")
                        self.send_command_to_client('cut_power', True)
                        continue
                    if sensor_data2.get('action') == 'true':
                        print(f"【接收】断电成功")
                        sensor_data_now = sensor_data['methane']
                        while True:
                            print(f'【警告】当前甲烷浓度：{round(sensor_data_now, 2)}')
                            if sensor_data_now <= 5.0:
                                print('甲烷浓度在预警值以下！')
                                self.send_command_to_client('methane_safe', True)
                                break
                            time.sleep(2)
                            sensor_data_now -= round(random.uniform(0.2, 0.5), 2)

                        # print('设备已断断电！')
                    elif sensor_data2.get('action') == 'false':
                        print("【接收】断电失败")
                        print('设备断电失败！报警！')
                        self.alarm_active = True
                        self.send_command_to_client('alarm', True)
                    break
                except Exception as e:
                    print(f"【警告】发送指令时发生错误: {e}")
                    break

        # 检查温度和氧气浓度是否需要开启风机
        elif sensor_data['temperature'] > 25 or sensor_data['oxygen'] < 18:
            print("【警告】温度过高或氧气浓度过低，开启主备风机！")
            self.send_command_to_client('fan', 'both_on')
            while True:
                try:
                    # 接收下位机的响应
                    data = self.clients.recv(1024)
                    if not data:
                        time.sleep(1)
                        continue
                    message = data.decode('utf-8')
                    print(f"【接收】收到下位机数据: {message}")
                    sensor_data2, received_checksum = self.extract_data_and_checksum(message)
                    # 校验响应数据
                    computed_checksum = self.compute_checksum(sensor_data2)
                    if received_checksum != computed_checksum:
                        print("【警告】上位机接收到的响应校验失败，继续重发命令...")
                        self.send_command_to_client('fan', 'both_on')
                        continue
                    if sensor_data2.get('action') == 'true':
                        print(f"【接收】主备风机开启成功")

                    break
                except Exception as e:
                    print(f"【警告】发送指令时发生错误: {e}")
                    break

        elif sensor_data['temperature'] <= 28 or sensor_data['oxygen'] >= 18:
            print('温度和氧气浓度适宜！')
            self.send_command_to_client('temp_safe', True)

    # -------------------------下发指令--------------------
    def send_command_to_client(self, command, value):
        """发送指令到下位机"""
        command_data = json.dumps({command: value})
        checksum = self.compute_checksum(command_data)
        message = f"{command_data}|{checksum}"
        self.clients.send(message.encode('utf-8'))

if __name__ == '__main__':
    # 启动服务器
    server = Server()
    server.start()
