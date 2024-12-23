import socket
import time
import json
import random
import hashlib


# 下位机类
class Client:
    def __init__(self, host='127.0.0.1', port=12345):
        self.host = host
        self.port = port
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connect_to_server()  # 连接到服务器
        self.sensor_data = {
            'methane': 0.0,
            'temperature': 20.0,
            'oxygen': 20.0,
            'fan1': 1,
            'fan2': 1,
            'timestamp': time.time()
        }

    def connect_to_server(self):
        """连接服务器，并添加异常处理机制"""
        try:
            self.client_socket.connect((self.host, self.port))
            print("连接到服务器成功！")
        except (ConnectionRefusedError, socket.error) as e:
            print(f"连接到服务器失败: {e}")
            time.sleep(5)  # 等待5秒后重试
            self.connect_to_server()  # 递归重试连接

    def get_sensor_data(self):
        self.sensor_data['timestamp'] = time.time()
        self.sensor_data['methane'] = round(random.uniform(0.0, 6.0), 2)  # 模拟甲烷浓度变化
        self.sensor_data['temperature'] = round(random.uniform(15.0, 35.0), 2)  # 模拟温度变化
        self.sensor_data['oxygen'] = round(random.uniform(15.0, 23.0), 2)  # 模拟氧气浓度变化
        self.sensor_data['fan1'] = random.choice([0, 1])  # 模拟风机状态
        self.sensor_data['fan2'] = random.choice([0, 1])  # 模拟风机状态

    def send_sensor_data(self):
        """上传传感器数据"""
        try:
            # self.sensor_data['timestamp'] = time.time()
            # self.sensor_data['methane'] = 4  # 模拟甲烷浓度变化
            # self.sensor_data['temperature'] = 36  # 模拟温度变化
            # self.sensor_data['oxygen'] = 19  # 模拟氧气浓度变化
            # self.sensor_data['fan1'] = 0  # 模拟风机状态
            # self.sensor_data['fan2'] = 0  # 模拟风机状态

            # 将数据编码为 JSON 格式并计算校验和
            message = json.dumps(self.sensor_data)
            checksum = self.compute_checksum(message)
            full_message = f"{message}|{checksum}"

            # 发送数据到服务器
            self.client_socket.send(full_message.encode('utf-8'))
            print("传感器数据已发送")
        except (ConnectionAbortedError, ConnectionResetError) as e:
            print(f"发送数据时发生错误: {e}")
            self.client_socket.close()  # 关闭当前连接
            self.connect_to_server()  # 重新连接服务器
            self.send_sensor_data()  # 重新尝试发送数据

    def receive_command(self):
        """接收上位机的指令并执行"""
        while True:
            try:
                data = self.client_socket.recv(1024)
                if not data:
                    break

                message = data.decode('utf-8')
                print(f"收到上位机指令: {message}")

                # 解析指令并执行
                command_data, checksum = self.extract_data_and_checksum(message)
                computed_checksum = self.compute_checksum(command_data)

                if checksum != computed_checksum:
                    print("指令数据校验失败！")
                    continue  # 跳过不合法的指令

                # 执行命令
                if 'cut_power' in command_data:
                    print("执行断电指令！")
                    # 上位机要立即报警，不可自动解除，设置手动解除报警机制
                elif 'fan' in command_data:
                    print("执行开启风机指令！")
                elif 'sync_time' in command_data:
                    print("校时指令，时间同步！")
                    self.sync_time()
                elif 'alarm' in command_data:
                    print("报警！手动解除！")
                    # 设置手动解除报警机制，下位机必须输入解除报警指令
                    self.resolve_alarm()
                elif 'resend' in command_data:
                    print('重新发送报文！')
                    self.resend_message()
                elif 'next_message' or 'success' in command_data:
                    break

                # 发送确认报文
                # self.send_confirmation('success', "The order is executed!")
                confirmation_message = json.dumps({"status": 'success', "message": "The order is executed!"})
                self.compute_checksum(confirmation_message)

            except Exception as e:
                print(f"接收指令时出错: {e}")
                break

    # ----------------------------复杂命令--------------------------------
    def sync_time(self):
        """同步下位机时间"""
        current_time = time.time()
        print('时钟校正值：' + current_time)
        # self.client_socket.send(f"SYNC_TIME {current_time}".encode('utf-8'))

    def resolve_alarm(self):
        """手动解除报警"""
        while True:
            resolve_command = input('输入解除警报密码：')
            if resolve_command == '0721':
                # self.client_socket.send(b"ALARM_RESOLVED")
                print('警报解除')
                break
            else:
                print('密码错误！')
                continue

    def resend_message(self):
        self.send_sensor_data()

    # ----------------------------------------------------------------

    # def send_confirmation(self, status, message):
    #     """发送指令执行的确认报文"""
    #     confirmation = json.dumps({"status": status, "message": message})
    #     self.client_socket.send(confirmation.encode('utf-8'))

    def compute_checksum(self, data):
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

    # ------------------------启动-----------------------
    def start(self):
        """开始上传数据并接收指令"""
        while True:
            self.get_sensor_data()
            self.send_sensor_data()
            self.receive_command()
            print('-----------------------------------------------')
            time.sleep(0.1)


# 启动下位机
client = Client()
client.start()
