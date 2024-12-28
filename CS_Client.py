import socket
import time
import json
import random
import hashlib

# 下位机类
class Client:
    # ------------------------初始化下位机-----------------------
    def __init__(self, host='127.0.0.1', port=8081):
        self.host = host
        self.port = port
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connect_to_server()
        self.sensor_data = {
            'methane': 0.0,
            'temperature': 20.0,
            'oxygen': 20.0,
            'fan1': 1,
            'fan2': 1,
            'timestamp': time.time()
        }
        self.dialog_state = None

    # ------------------------下位机启动-----------------------
    def start(self):
        while True:
            self.get_sensor_data()
            self.send_sensor_data()
            self.receive_command()
            time.sleep(2)

    # -----------------------传感器数据仿真----------------------------
    def get_sensor_data(self):
        self.sensor_data['timestamp'] = time.time()
        self.sensor_data['methane'] = round(random.uniform(0.0, 7.0), 2)  # 模拟甲烷浓度变化
        # self.sensor_data['temperature'] = 70  # 模拟温度变化
        # self.sensor_data['oxygen'] = 15  # 模拟氧气浓度变化
        self.sensor_data['temperature'] = round(random.uniform(15.0, 35.0), 2)  # 模拟温度变化
        self.sensor_data['oxygen'] = round(random.uniform(15.0, 23.0), 2)  # 模拟氧气浓度变化
        self.sensor_data['fan1'] = random.choice([0, 1])  # 模拟风机状态
        self.sensor_data['fan2'] = random.choice([0, 1])  # 模拟风机状态
        # self.sensor_data['fan1'] = 1  # 模拟风机状态
        # self.sensor_data['fan2'] = 0  # 模拟风机状态
        # self.sensor_data['machine'] = random.choice([0, 1])  # 模拟继电器状态
        self.sensor_data['machine'] = 1 # 开采设备保持运行状态

    # -------------------------连接上位机-----------------------
    def connect_to_server(self):
        try:
            self.client_socket.connect((self.host, self.port))
            print("【上传】传感器数据已发送")
        except (ConnectionRefusedError, socket.error) as e:
            print(f"【上传】发送数据时发生错误: {e}")
            time.sleep(5)  # 等待5秒后重试
            self.connect_to_server()  # 递归重试连接

    # ----------------------校验方法----------------------
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

    # -----------------------下位机上传信息---------------------------
    def send_sensor_data(self):
        """上传传感器数据"""
        try:
            # 生成校验合
            message = json.dumps(self.sensor_data)
            checksum = self.compute_checksum(message)
            full_message = f"{message}|{checksum}"
            # 发送数据到服务器
            self.client_socket.send(full_message.encode('utf-8'))
            print(f"【上传】传感器数据为:{full_message}")

        except (ConnectionAbortedError, ConnectionResetError) as e:

            self.client_socket.close()  # 关闭当前连接
            self.connect_to_server()  # 重新连接服务器
            self.send_sensor_data()  # 重新尝试发送数据

    # -------------------------接收执行上位机指令-----------------------------
    def receive_command(self):
        """接收上位机的指令并执行"""
        while True:
            try:
                data = self.client_socket.recv(1024)
                if not data:
                    continue  # 没有数据 继续接收数据

                message = data.decode('utf-8')
                print(f"【接收】收到上位机指令: {message}")
                # 解析指令
                command_data, checksum = self.extract_data_and_checksum(message)
                computed_checksum = self.compute_checksum(command_data)
                if checksum != computed_checksum:
                    print("【接收】指令数据校验失败！")
                    break  # 跳过不合法的指令

                # 执行命令
                if 'cut_power' in command_data:
                    print("【执行】执行断电指令！")
                    random_integer = random.randint(0, 1)
                    if random_integer == 0:
                        print(f"【上传】断电成功")
                        response_data = json.dumps({"action": "true"})
                        response_checksum = self.compute_checksum(response_data)
                        self.client_socket.send(f"{response_data}|{response_checksum}".encode('utf-8'))
                    elif random_integer == 1:
                        print(f"【上传】断电失败")
                        response_data = json.dumps({"action": "false"})
                        response_checksum = self.compute_checksum(response_data)
                        self.client_socket.send(f"{response_data}|{response_checksum}".encode('utf-8'))

                elif 'methane_safe' in command_data:
                    print('【执行】关闭备用风机，保持主风机开启!')

                elif 'fan' in command_data:
                    print("【执行】执行开启风机指令！")
                    response_data = json.dumps({"action": "true"})
                    response_checksum = self.compute_checksum(response_data)
                    self.client_socket.send(f"{response_data}|{response_checksum}".encode('utf-8'))
                    print(f"【上传】开启主备风机成功")

                elif 'temp_safe' in command_data:
                    print('【执行】关闭备用风机，保持主风机开启！')

                elif 'sync_time' in command_data:

                    print("【执行】执行校时指令！")
                    self.sync_time()
                    response_data = json.dumps({"action": "true"})
                    response_checksum = self.compute_checksum(response_data)
                    self.client_socket.send(f"{response_data}|{response_checksum}".encode('utf-8'))
                    print(f"【上传】时间矫正成功")

                elif 'alarm' in command_data:
                    print("【执行】报警！请手动解除！")
                    self.resolve_alarm()
                    continue

                elif 'resend' in command_data:
                    print('【上传】重新发送报文...')
                    response_data = json.dumps({"action": "true"})
                    response_checksum = self.compute_checksum(response_data)
                    self.client_socket.send(f"{response_data}|{response_checksum}".encode('utf-8'))
                    self.resend_message()
                    print(f"【上传】重新发送数据成功")

                elif 'next_message' in command_data or 'success' in command_data:
                    print('【执行】指令执行完毕！\n-----------------------------------------------')
                    break

            except Exception as e:
                print(f"【接收】接收指令时出错: {e}")
                break

    # ----------------------------执行复杂指令--------------------------------
    def sync_time(self):
        """同步下位机时间"""
        current_time = str(time.time())
        #print(f'时钟校正值：{current_time}')

    def resolve_alarm(self):
        """手动解除报警"""
        while True:
            resolve_command = input('输入解除警报密码：')
            if resolve_command == '123':
                # self.client_socket.send(b"ALARM_RESOLVED")
                print('【提醒】警报已解除！')
                # print('警报解除！')
                confirmation_message = {"alarm_message": "False"}
                message = json.dumps(confirmation_message)
                checksum = self.compute_checksum(message)
                full_message = f"{message}|{checksum}"
                self.client_socket.send(full_message.encode('utf-8'))
                print('【执行】警报解除报文已发送！')
                break
            else:
                print('【提醒】密码错误！')
                continue

    def resend_message(self):
        self.send_sensor_data()

if __name__ == '__main__':
    # 启动客户机
    client = Client()
    client.start()
