import socket
import time
import json
import random
import hashlib
from PyQt5.QtCore import QThread, pyqtSignal, QMutex, QWaitCondition


# 下位机类
class ClientThread(QThread):
    # 通过信号通知主线程
    client_thread_signal = pyqtSignal(str)

    # def run(self):
    #     self.run()

    # ------------------------初始化下位机-----------------------
    def __init__(self, host='127.0.0.1', port=8080):
        super().__init__()  # 调用 QThread 的初始化方法
        # self.password = None
        self.host = host
        self.port = port
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # self.connect_to_server()
        self.sensor_data = {
            'methane': 0.0,
            'temperature': 20.0,
            'oxygen': 20.0,
            'fan1': 1,
            'fan2': 1,
            'timestamp': time.time()
        }
        self.dialog_state = None

        # ------------------互斥锁，用来进行密码判定-----------------------
        self.mutex = QMutex()  # 创建互斥锁
        self.wait_condition = QWaitCondition()  # 创建等待条件
        self.password = None  # 用于存储从主程序传来的数据

    # ------------------------下位机启动-----------------------
    def run(self):
        self.connect_to_server()
        while True:

            self.get_sensor_data()
            self.send_sensor_data()
            self.receive_command()
            time.sleep(5)

    # -----------------------传感器数据仿真----------------------------
    def get_sensor_data(self):
        # self.sensor_data['timestamp'] = time.time()
        self.sensor_data['timestamp'] = 1
        # self.sensor_data['methane'] = round(random.uniform(4.0, 7.0), 2)  # 模拟甲烷浓度变化
        self.sensor_data['methane'] = 5
        self.sensor_data['temperature'] = round(random.uniform(26.0, 90.0), 2)  # 模拟温度变化
        # self.sensor_data['temperature'] = 70
        self.sensor_data['oxygen'] = round(random.uniform(15.0, 23.0), 2)  # 模拟氧气浓度变化
        self.sensor_data['fan1'] = random.choice([0, 1])  # 模拟风机状
        self.sensor_data['fan2'] = random.choice([0, 1])  # 模拟风机状态
        # self.sensor_data['fan1'] =1# 模拟风机状态
        # self.sensor_data['fan2'] = 0  # 模拟风机状态
        self.sensor_data['machine'] = random.choice([0, 1])  # 模拟继电器状态
        # self.sensor_data['machine'] = 1



    # -------------------------连接上位机-----------------------
    def connect_to_server(self):
        try:
            self.client_socket.connect((self.host, self.port))
            self.dialog_client('connect_to_server_success')
        except (ConnectionRefusedError, socket.error) as e:
            self.dialog_client('connect_to_server_success', e)
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
                    break  # 跳出while

                message = data.decode('utf-8')
                # print(f"【接收】收到上位机指令: {message}")
                self.dialog_client('receive_command_success', message)

                # 解析指令
                command_data, checksum = self.extract_data_and_checksum(message)
                computed_checksum = self.compute_checksum(command_data)
                if checksum != computed_checksum:
                    # print("【接收】指令数据校验失败！")
                    self.dialog_client('receive_command_failure')
                    break  # 跳过不合法的指令

                # 执行命令
                if 'cut_power' in command_data:
                    self.dialog_state = 1
                    # print("【执行】执行断电指令！")
                    # 上位机要立即报警，不可自动解除，设置手动解除报警机制
                    self.dialog_client(self.dialog_state)
                elif 'methane_safe' in command_data:
                    self.dialog_state = 11
                    # print('关闭备用风机，保持主风机开启!')
                    self.dialog_client(self.dialog_state)



                elif 'fan' in command_data:
                    self.dialog_state = 2
                    # print("【执行】执行开启风机指令！")
                    self.dialog_client(self.dialog_state)
                elif 'temp_safe' in command_data:
                    self.dialog_state = 21
                    # print('关闭备用风机，保持主风机开启！')
                    self.dialog_client(self.dialog_state)
                elif 'sync_time' in command_data:
                    self.dialog_state = 3
                    # print("【执行】执行校时指令！")
                    self.dialog_client(self.dialog_state)
                    self.sync_time()

                elif 'alarm' in command_data:
                    self.dialog_state = 4
                    # print("【执行】报警！请手动解除！")
                    # 设置手动解除报警机制，下位机必须输入解除报警指令
                    self.dialog_client(self.dialog_state)
                    self.resolve_alarm()
                    continue

                elif 'resend' in command_data:
                    self.dialog_state = 5
                    # print('【执行】重新发送报文...')
                    self.dialog_client(self.dialog_state)
                    self.resend_message()



                elif 'next_message' or 'success' in command_data:
                    # 指令执行完毕，发送确认报文
                    self.dialog_client('command_execution_completed')
                    # print('【执行】指令执行完毕！')
                    # print('-----------------------------------------------')
                    break

                # self.dialog_client(self.dialog_state)

            except Exception as e:
                self.dialog_client('receive_command_error', e)
                # print(f"【接收】接收指令时出错: {e}")
                break

    # ----------------------------执行复杂指令--------------------------------
    def sync_time(self):
        """同步下位机时间"""
        current_time = str(time.time())
        print(f'时钟校正值：{current_time}')

    def update_password(self,password):
        self.mutex.lock()  # 锁住线程，防止数据修改时其他线程访问
        self.password = password  # 设置数据
        self.wait_condition.wakeOne()  # 唤醒等待中的线程
        self.mutex.unlock()  # 解锁

    def resolve_alarm(self):
        """手动解除报警"""
        while True:
            self.mutex.lock()  # 锁住线程，防止数据未到时继续执行
            self.wait_condition.wait(self.mutex)  # 等待信号来唤醒
            self.mutex.unlock()  # 解锁
            # resolve_command = input('输入解除警报密码：')
            resolve_command = str(self.password)
            if resolve_command == '0721':
                # self.client_socket.send(b"ALARM_RESOLVED")
                self.dialog_client('alarm_true')
                # print('警报解除！')
                confirmation_message = {"alarm_message": "False"}
                message = json.dumps(confirmation_message)
                checksum = self.compute_checksum(message)
                full_message = f"{message}|{checksum}"
                self.client_socket.send(full_message.encode('utf-8'))
                self.dialog_client('alarm_message_to_server')
                # print('【执行】警报解除报文已发送！')
                break
            else:
                self.dialog_client('alarm_false')
                # print('密码错误！')
                continue

    def resend_message(self):
        self.send_sensor_data()

    # ----------------------------日志反馈------------------------
    def dialog_client(self, message_type, error=None):
        if message_type == 'connect_to_server_success':
            # print("【上传】传感器数据已发送")
            message = '【上传】传感器数据已发送'
            self.client_thread_signal.emit(message)
        elif message_type == 'connect_to_server_failure':
            # print(f"【上传】发送数据时发生错误: {error}")
            message = f'【上传】发送数据时发生错误: {error}'
            self.client_thread_signal.emit(message)
        elif message_type == 'receive_command_success':
            # print(f"【接收】收到上位机指令: {error}")
            message = f'【接收】收到上位机指令: {error}'
            self.client_thread_signal.emit(message)
        elif message_type == 'receive_command_failure':
            # print("【接收】指令数据校验失败！")
            message = '【接收】指令数据校验失败！'
            self.client_thread_signal.emit(message)
        elif message_type == 1:
            # print("【执行】执行断电指令！")
            message = '【执行】执行断电指令！'
            self.client_thread_signal.emit(message)
        elif message_type == 11:
            # print('【执行】关闭备用风机，保持主风机开启!')
            message = '【执行】关闭备用风机，保持主风机开启!'
            self.client_thread_signal.emit(message)
        elif message_type == 2:
            # print("【执行】执行开启风机指令！")
            message = '"【执行】执行开启风机指令！'
            self.client_thread_signal.emit(message)
        elif message_type == 21:
            # print('【执行】关闭备用风机，保持主风机开启！')
            message = '【执行】关闭备用风机，保持主风机开启！'
            self.client_thread_signal.emit(message)
        elif message_type == 3:
            # print("【执行】执行校时指令！")
            message = '【执行】执行校时指令！'
            self.client_thread_signal.emit(message)
        elif message_type == 4:
            # print("【执行】报警！请手动解除！")
            message = '【执行】报警！请手动解除！'
            self.client_thread_signal.emit(message)
        elif message_type == 5:
            # print('【上传】重新发送报文...')
            message = '【上传】重新发送报文...'
            self.client_thread_signal.emit(message)
        elif message_type == 'receive_command_error':
            # print(f"【接收】接收指令时出错: {error}")
            message = f"【接收】接收指令时出错: {error}"
            self.client_thread_signal.emit(message)
        elif message_type == 'command_execution_completed':
            # print('【执行】指令执行完毕！\n---------------')
            message = '【执行】指令执行完毕！\n---------------'
            self.client_thread_signal.emit(message)
        elif message_type == 'alarm_true':
            # print('【提醒】警报已解除！')
            message = '【提醒】警报已解除！'
            self.client_thread_signal.emit(message)
        elif message_type == 'alarm_false':
            # print('【提醒】密码错误！')
            message = '【提醒】密码错误！'
            self.client_thread_signal.emit(message)
        elif message_type == 'alarm_message_to_server':
            # print('【上传】警报解除报文已发送！')
            message = '【上传】警报解除报文已发送！'
            self.client_thread_signal.emit(message)

        # 启动下位机


# if __name__ == '__main__':
    # client = Client()
    # client.start()
