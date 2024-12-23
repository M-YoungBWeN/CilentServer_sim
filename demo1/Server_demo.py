import socket
import time
import json
import threading
import hashlib

# 服务器类
class Server:
    def __init__(self, host='127.0.0.1', port=12345):
        self.host = host
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        self.clients = []
        self.alarm_active = False
        self.last_sensor_data = {}
        self.private_massage_checksum = 0

    def handle_client(self, client_socket):
        """处理客户端连接"""
        while True:
            try:
                data = client_socket.recv(1024)
                if not data:
                    break

                message = data.decode('utf-8')
                print(f"收到下位机数据: {message}")

                # 解析数据并验证校验码
                sensor_data, received_checksum = self.extract_data_and_checksum(message)
                computed_checksum = self.compute_checksum(sensor_data)

                 # 检查该校验和是否是此前有过的
                if self.private_massage_checksum == computed_checksum or computed_checksum=='\"':
                    print("数据曾校验！")
                    # re_send_message = json.dumps({"status": 'next_message', "message": "Send next message!"})
                    # self.compute_checksum(re_send_message)
                    self.send_command_to_client('next_message', True)
                    break

                elif received_checksum != computed_checksum:
                    print("数据校验失败！")
                    # re_send_message = json.dumps({"status": 'resend', "message": "Resend message!"})
                    # self.compute_checksum(re_send_message)
                    self.send_command_to_client('resend', True)
                    continue

                if received_checksum == computed_checksum:
                    self.private_massage_checksum = computed_checksum
                    # continue  # 跳过本次数据处理

                # 处理数据
                self.process_sensor_data(sensor_data)

                # 发送确认报文
                # self.send_command_to_client('status','success')
                # client_socket.send(confirmation.encode('utf-8'))
                # confirmation_message = json.dumps({"status": 'success', "message": "The order is executed!"})
                # self.compute_checksum(confirmation_message)
                self.send_command_to_client('success', True)
                print('---------------------------------------------------')

            except Exception as e:
                print(f"处理客户端数据时出错: {e}")
                break

        client_socket.close()

    def process_sensor_data(self, sensor_data):
        """处理下位机上传的传感器数据"""
        # 检查是否有报警情况
        # self.check_alarms(sensor_data)

        # 例如：检测甲烷浓度
        if sensor_data['methane'] > 5.0:
            print("甲烷浓度过高，断电开采设备！")
            self.send_command_to_client('cut_power', True)

        # 检查温度和氧气浓度是否需要开启风机
        elif sensor_data['temperature'] > 60 or sensor_data['oxygen'] < 18:
            print("温度过高或氧气浓度过低，开启主备风机！")
            self.send_command_to_client('fan', 'both_on')

        # 判断通风风机的状态
        elif sensor_data['fan1'] == 0 and sensor_data['fan2'] == 0:
            print("报警：主备风机都关闭！")
            self.alarm_active = True
            self.send_command_to_client('alarm', True)

        # 时间同步
        elif abs(time.time() - sensor_data['timestamp']) > 2:
            print("时间误差过大，要求下位机校时！")
            self.send_command_to_client('sync_time', True)

    def send_command_to_client(self, command, value):
        """发送指令到下位机"""
        for client in self.clients:
            command_data = json.dumps({command: value})
            checksum = self.compute_checksum(command_data)
            message = f"{command_data}|{checksum}"
            client.send(message.encode('utf-8'))
    # ------------------------校验-------------------------
    def compute_checksum(self, data):
        """计算数据的校验和（使用MD5）"""
        # return hashlib.md5(data.encode('utf-8')).hexdigest()
        """计算数据的校验和（使用MD5）"""
        if isinstance(data, dict):
            # 如果数据是字典，先转换为 JSON 字符串
            data = json.dumps(data)
        return hashlib.md5(data.encode('utf-8')).hexdigest()

    def extract_data_and_checksum(self, message):
        """提取数据和校验和"""
        if "|" in message:
            data, checksum = message.rsplit("|", 1)
            # 确保提取的数据是字典类型
            data = json.loads(data)
            return data, checksum
        return {}, ""


    # --------------------------启动----------------------------
    def start(self):
        """启动服务器并监听客户端连接"""
        print(f"服务器启动，监听 {self.host}:{self.port}...")
        while True:
            client_socket, client_address = self.server_socket.accept()
            print(f"新客户端连接：{client_address}")
            self.clients.append(client_socket)

            # 启动新线程处理客户端数据
            client_thread = threading.Thread(target=self.handle_client, args=(client_socket,))
            client_thread.start()


# 启动服务器
server = Server()
server.start()
