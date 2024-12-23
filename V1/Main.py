import json
import re
import sys
from PyQt5.QtCore import Qt
from MainWindow import Ui_mainWindow
from PyQt5.QtWidgets import QApplication, QMainWindow, QGraphicsDropShadowEffect
from CS_Server_thread import ServerThread
from CS_Client_thread import ClientThread


# -------------------------全局样式方法-------------------------
# 去除窗口标题栏和空背景
def window_attribute_effect(self):
    self.setWindowFlag(Qt.FramelessWindowHint)  # 隐藏标题栏
    self.setAttribute(Qt.WA_TranslucentBackground)  # 隐藏空背景


# 增加窗口阴影
def window_shadow_effect(self):
    # 创建一个QGraphicsDropShadowEffect对象
    shadow_effect = QGraphicsDropShadowEffect(self)
    # 设置阴影的参数
    shadow_effect.setBlurRadius(20)  # 模糊半径
    shadow_effect.setColor(Qt.black)  # 阴影颜色
    shadow_effect.setOffset(3, 3)  # 偏移量
    # 将阴影应用到窗口
    self.setGraphicsEffect(shadow_effect)


class LoadMainWindow(QMainWindow):
    def __init__(self):
        # -----------------初始化窗口----------------
        super().__init__()
        self.ui = Ui_mainWindow()
        self.ui.setupUi(self)
        # window_attribute_effect(self)
        # window_shadow_effect(self)
        # ------------------点击事件-----------------
        self.pushbutton_connect()
        self.show()
        # -----------------pyqt多线程-----------------
        # 创建 ServerThread 和 ClientThread 的实例
        self.server_thread = ServerThread(host='127.0.0.1', port=8080)
        self.client_thread = ClientThread(host='127.0.0.1', port=8080)

        # 连接信号与槽，接收线程更新信息
        self.server_thread.server_thread_signal.connect(self.refresh_server_message)
        self.client_thread.client_thread_signal.connect(self.refresh_client_message)



    # -----------------点击逻辑------------------
    def pushbutton_connect(self):
        # pass
        self.ui.pushButton.clicked.connect(self.start_server_button)
        self.ui.pushButton_2.clicked.connect(self.start_client_button)
        self.ui.pushButton_3.clicked.connect(self.commit_client_button)
        self.ui.pushButton_4.clicked.connect(self.commit_server_button)
        # self.ui.pushButton.clicked.connect(self.start_server_button())
        # self.ui.pushButton.clicked.connect(self.start_server_button())

    # ----------------点击调用函数--------------------
    def start_server_button(self):
        if not self.server_thread.isRunning():
            self.server_thread.start()  # 启动线程

    def start_client_button(self):
        if not self.client_thread.isRunning():
            self.client_thread.start()  # 启动线程

    def commit_server_button(self):
        password = self.ui.lineEdit_2.text()
        self.client_thread.update_password(password)


    def commit_client_button(self):
        password = self.ui.lineEdit.text()
        self.client_thread.update_password(password)


    # -----------------数据更新----------------
    def refresh_server_message(self, message):
        # print(message)
        # 【接收】收到下位机数据:
        # {"methane": 2.71, "temperature": 15.26, "oxygen": 18.9, "fan1": 0, "fan2": 0, "timestamp": 1734855768.426581, "machine": 0}
        # |4f279ca90f9eb49a492bfe0441f5c4f5
        if '【接收】收到下位机数据:'in message:
            match = re.search(r'\{(.*?)\}', message)
            if match:
                # 提取到的 JSON 字符串
                json_str = match.group(0)
                # 将 JSON 字符串转换为字典
                data = json.loads(json_str)
                for key, value in data.items():
                    if key == 'methane':
                        self.ui.lineEdit_5.setText(str(value))
                    if key == 'temperature':
                        self.ui.lineEdit_4.setText(str(value))
                    if key == 'oxygen':
                        self.ui.lineEdit_6.setText(str(value))
                    if key == 'fan1':
                        self.ui.lineEdit_7.setText(str(value))
                    if key == 'fan2':
                        self.ui.lineEdit_8.setText(str(value))
                    if key == 'timestamp':
                        self.ui.lineEdit_3.setText(str(int(value)))
                    if key == 'machine':
                        self.ui.lineEdit_9.setText(str(value))

        self.ui.textBrowser.append(message)

    def refresh_client_message(self, message):
        if '【发送】甲烷浓度:'in message:
            match = re.search(r'\{(.*?)\}', message)
            if match:
                # 提取到的 JSON 字符串
                json_str = match.group(0)
                # 将 JSON 字符串转换为字典
                data = json.loads(json_str)
                for key, value in data.items():
                    pass
        self.ui.textBrowser_2.append(message)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    # win = QtWidgets.QMainWindow() # 做成LoadMainWindow类
    # ui = Ui_MainWindow() # 在类里创建Ui_MainWindow对象
    # ui.setupUi(win) # 初始化LoadMainWindow类
    # win.show()

    win = LoadMainWindow()
    sys.exit(app.exec_())
