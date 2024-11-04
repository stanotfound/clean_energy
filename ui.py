import sys
import time
import os
import openai
import cv2
import requests
import hashlib
import random
import face_recognition
import numpy as np
import torch
import ultralytics
from sparkai.core.messages import ChatMessage
from ultralytics import YOLO
import ultralytics.engine.results
from face import *
from com import *
from serial.tools.list_ports_windows import comports
import numpy as np
from pydub import AudioSegment
import wave
import pyaudio
import iat_ws_voice
import _thread as thread
import pytesseract
import threading
from paddleocr import PaddleOCR
from PIL import Image
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve
from PyQt5.QtWidgets import (
    QLabel,
    QMainWindow,
    QSpinBox,
    QComboBox,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QTabWidget,
    QPushButton,
    QLineEdit,
    QSizePolicy,
    QSplitter,
    QStyleFactory,
    QApplication
)
from PyQt5.QtGui import QCloseEvent, QPixmap, QImage, QShowEvent, QFont, QColor, QPalette,QLinearGradient

from openai import OpenAI

os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
client = OpenAI(
    api_key="sk-wREI9QrEF4Gp00cy3WJ2V2T7EKjr2xvQo6Y3WmtGOWYgtmem",
    base_url="https://api.chatanywhere.tech/v1"
)

APP_ID = '20241021002182052'  # 替换为你自己的 APP ID
SECRET_KEY = 'TmZuzW8zBAruOvpwY8sN'  # 替换为你的密钥

def baidu_translate(query, from_lang='zh', to_lang='en'):
    """ 使用百度翻译 API 进行翻译 """
    url = "https://fanyi-api.baidu.com/api/trans/vip/translate"
    salt = str(random.randint(32768, 65536))
    sign = hashlib.md5((APP_ID + query + salt + SECRET_KEY).encode('utf-8')).hexdigest()
    
    params = {
        'q': query,
        'from': from_lang,
        'to': to_lang,
        'appid': APP_ID,
        'salt': salt,
        'sign': sign
    }

    try:
        response = requests.get(url, params=params)
        result = response.json()
        if "trans_result" in result:
            return result['trans_result'][0]['dst']  # 返回翻译后的文本
        else:
            return None
    except Exception as e:
        print(f"百度翻译 API 请求失败: {e}")
        return None
    
CLEAN_ENERGY_CATEGORIES = [
    "潮汐能", "太阳能", "沼气能", "风能", "水能", "地热能", "生物能"
]

class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setFixedSize(800,600)
        self.setWindowTitle("\"智能博物之清洁能源\"主页")

        self.setStyleSheet("""
            QMainWindow {
                background-color: #2B2B2B;
            }
            QTabWidget::pane {
                border: 1px solid #444;
                background-color: #1C1C1C;
            }
            QTabBar::tab {
                background-color: #444;
                color: white;
                padding: 10px;
                border-radius: 5px;
            }
            QTabBar::tab:selected {
                background-color: #00BFFF;
                color: white;
            }
            QLabel {
                color: white;
                font-size: 16px;
            }
            QPushButton {
                background-color: #3A3A3A;
                color: white;
                border: 1px solid #555;
                border-radius: 10px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #00BFFF;
                border: 1px solid #00BFFF;
            }
            QComboBox {
                background-color: #3A3A3A;
                color: white;
                border-radius: 5px;
                padding: 5px;
            }
            QSpinBox {
                background-color: #3A3A3A;
                color: white;
                border-radius: 5px;
                padding: 5px;
            }
        """)

        # 添加一个渐变背景效果
        self.setAutoFillBackground(True)
        palette = self.palette()
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0, QColor("#141E30"))
        gradient.setColorAt(1, QColor("#243B55"))
        palette.setBrush(QPalette.Window, gradient)
        self.setPalette(palette)

        self.face_recognition = FaceRecognitionWidget()
        self.method_q_a = MethodQAWidget()
        self.text_recognition = TextRecognitionWidget()
        self.com_manager = ComManagerWidget()

        self.tab = QTabWidget(self)
        self.tab.setTabPosition(QTabWidget.TabPosition.North)
        self.tab.addTab(self.face_recognition, "聚焦领域领军人物")
        self.tab.addTab(self.method_q_a, "清洁能源定义探析")
        self.tab.addTab(self.text_recognition, "清洁能源认知深化")
        self.tab.addTab(self.com_manager, "端口管理")
        self.tab.currentChanged.connect(self._on_tab_changed)
        self.previous = self.tab.currentWidget()
        self.setCentralWidget(self.tab)

    def _on_tab_changed(self, index: int):
        tab = self.previous
        self.previous = self.tab.currentWidget()
        try:
            capture: cv2.VideoCapture = tab.capture
            if isinstance(capture, cv2.VideoCapture):
                if capture.isOpened():
                    tab.disable_capture()
        except AttributeError:
            print("[mainwindow\t\t] Ignored")


class ComManagerWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.tea_map = ["安吉白茶", "安吉白茶", "西湖龙井", "西湖龙井", "武夷铁观音", "武夷铁观音"]
        self.com_list = list(comports())

        layout = QVBoxLayout()

        self.refresh_button = QPushButton("刷新端口列表")
        self.refresh_button.clicked.connect(self._refresh)

        self.com_combobox = QComboBox()
        self.com_combobox.addItems(map(lambda _com: _com.name, self.com_list))

        self.baudrate_spinbox = QSpinBox()
        self.baudrate_spinbox.setRange(0, 2147483647)
        self.baudrate_spinbox.setPrefix("波特率: ")
        self.baudrate_spinbox.setValue(115200)

        self.start_thread_button = QPushButton("开始监听")
        self.start_thread_button.clicked.connect(self._start_thread)

        self.stop_thread_button = QPushButton("停止监听")
        self.stop_thread_button.clicked.connect(self._stop_thread)

        self.update_timer = QTimer()
        self.update_timer.setInterval(200)
        self.update_timer.timeout.connect(self._update)
        self.update_timer.start()

        layout.addWidget(self.refresh_button)
        layout.addWidget(self.com_combobox)
        layout.addWidget(self.baudrate_spinbox)
        layout.addWidget(self.start_thread_button)
        layout.addWidget(self.stop_thread_button)
        self.setLayout(layout)

        self.listener = SerialListener(self.com_combobox.currentText(), self._callback)

    def _update(self):
        self.com_combobox.setEnabled(not self.listener.is_alive())
        self.baudrate_spinbox.setEnabled(not self.listener.is_alive())
        self.start_thread_button.setEnabled(not self.listener.is_alive() and self.com_combobox.count() != 0)
        self.stop_thread_button.setEnabled(self.listener.is_alive())

    def _refresh(self):
        if self.listener.is_alive():
            self.listener.terminate()
            time.sleep(1.)
        if self.listener.is_alive():
            return
        self.com_list = list(comports())
        self.com_combobox.clear()
        self.com_combobox.addItems(map(lambda _com: _com.name, self.com_list))
        self.listener = SerialListener(self.com_combobox.currentText(), self._callback)

    def _stop_thread(self):
        if self.listener.is_alive():
            self.listener.terminate()

    def _start_thread(self):
        if not self.listener.is_alive():
            if self.listener._started.is_set():
                self.listener = SerialListener(self.com_combobox.currentText(), self._callback)
            self.listener.start()

    def _callback(self, msg: str):
        cmd = tuple(msg.strip().split())
        print(cmd)
        match cmd:
            case ("say", sentence):
                GeneralDataStorage.tts.say(sentence)
            case ("tea", tea_id) if tea_id.isdigit():
                name = self.tea_map[int(tea_id)]
                thread.start_new_thread(self._intro_tea, (name,))
            case ("start_voice", *_):
                window = GeneralDataStorage.window
                window.tab.setCurrentIndex(1)
                window.method_q_a.start_button.click()
            case ("start_face", *_):
                window: MainWindow = GeneralDataStorage.window
                window.tab.setCurrentIndex(0)
                window.face_recognition.switch_camera.click()

    # def _intro_tea(self, name: str):
    #     response = spark_chat.get_response("请介绍一下" + name)
    #     GeneralDataStorage.tts.say(response.generations[0][0].text)


class TextRecognitionWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()

        self.yolo = YOLO(r"yolov8n-oiv7.pt")  # YOLO 模型加载
        self.textpic = None
        self.capture = None

        # 初始化 PaddleOCR
        self.ocr = PaddleOCR(use_angle_cls=True, lang='ch')  # 支持中文

        # 创建主布局，使用 QVBoxLayout 进行垂直布局
        main_layout = QVBoxLayout()

        # 添加用于捕获和检测的区域
        self.capture_frame = QLabel()
        self.capture_frame.setAlignment(Qt.AlignCenter)

        self.camera_id_box = QSpinBox()
        self.camera_id_box.setPrefix("设备号: ")
        self.camera_id_box.setAlignment(Qt.AlignBottom)

        self.switch_camera = QPushButton("开启/关闭摄像头")
        self.switch_camera.clicked.connect(self._on_switch_clicked)
        self.detect_button = QPushButton("检测")
        self.detect_button.clicked.connect(self._on_detect_clicked)

        # 添加控件到布局
        main_layout.addWidget(self.capture_frame)   # 摄像头画面区域
        main_layout.addWidget(self.camera_id_box)   # 设备号输入框
        main_layout.addWidget(self.switch_camera)   # 开启/关闭摄像头按钮
        main_layout.addWidget(self.detect_button)   # 检测按钮

        # 播报内容标签：单独显示并保持不消失
        self.broadcast_label = QLabel("播报内容将在这里显示")
        self.broadcast_label.setAlignment(Qt.AlignCenter)
        self.broadcast_label.setWordWrap(True)  # 支持换行显示
        self.broadcast_label.setStyleSheet("font-size: 16px;")  # 适当设置字体大小

        # 添加播报内容标签到布局底部
        main_layout.addWidget(self.broadcast_label)

        # 将主布局设置为窗口的布局
        self.setLayout(main_layout)

        self.timer = QTimer()
        self.timer.timeout.connect(self._update_frame)

        self.disable_capture()

    def _on_switch_clicked(self) -> None:
        if self.capture is not None and self.capture.isOpened():
            self.disable_capture()
        else:
            self.enable_capture()

    def _on_detect_clicked(self) -> None:
        """处理点击检测按钮后的事件"""
        if self.textpic is not None:
            try:
                pic0 = self.textpic
                pic = cv2.cvtColor(pic0, cv2.COLOR_BGR2GRAY)
                cv2.fastNlMeansDenoising(pic, pic)
                pic = cv2.adaptiveThreshold(pic, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 11, 2)
                
                def job():
                    try:
                        # 调用 PaddleOCR 获取识别结果
                        text_cn = self.extract_text_from_frame()
                        if text_cn:
                            print("[text_recognition] OCR识别到的文本:", text_cn)
                            # 使用 GPT 模型进行能源识别
                            self._process_energy_recognition(text_cn)
                        else:
                            print("[text_recognition] OCR未能识别到文本")
                    except Exception as e:
                        print(f"[text_recognition] OCR 或 GPT 处理出错: {e}")
                
                # 启动新线程来执行识别任务
                thread = threading.Thread(target=job)
                thread.start()
            except Exception as e:
                print(f"检测过程中出现错误: {e}")
        else:
            print("[text_recognition] textpic 为 None，未检测到图像")

    def extract_text_from_frame(self):
        """ 从当前捕获的帧中提取文本 """
        if hasattr(self, 'frame'):
            # 保存帧到临时图像文件
            temp_img_path = 'temp_frame.png'
            cv2.imwrite(temp_img_path, self.frame)

            # 使用 PaddleOCR 识别文本
            result = self.ocr.ocr(temp_img_path, cls=True)
            text_cn = ''.join([line[1][0] for line in result[0]])  # 提取识别的文本
            print(f"OCR识别到的文本: {text_cn}")  # 输出识别结果用于调试
            return text_cn.strip()
        return None

    def _process_energy_recognition(self, text_cn: str):
        """使用 AI 模型处理识别到的文本，提取能源类别"""
        gpt_result = self.classify_energy_using_gpt(text_cn)
        if gpt_result:
            print(f"GPT 识别到的结果: {gpt_result}")

            # 显示并播报 GPT 返回的结果
            self._display_and_broadcast(gpt_result)
        else:
            self.capture_frame.setText("未能识别出有效的能源类别或人名")
            print("未能识别出有效的能源类别或人名")

    def classify_energy_using_gpt(self, sentence: str) -> str:
        try:
            completion = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "你是一个清洁能源分类专家。"},
                    {"role": "user", "content": f"请分析以下句子，并判断它描述的能源类型（生物能、海洋能），人物名一般为前两个字，并按照格式输出：“<人物名>在介绍<能源类型>”。请确保输出只有一次介绍，不要重复。\n\n句子：'{sentence}'"}
                ],
                stream=False
            )
            result = completion.choices[0].message.content.strip()
            print(f"[GPT 结果] {result}")  # 调试信息
            return result
        except Exception as e:
            print(f"调用 GPT 失败: {e}")
            return None

    def _display_and_broadcast(self, sentence_cn: str):
        """更新 UI 显示并通过 TTS 播报结果"""
        # 更新显示播报内容
        self.broadcast_label.setText(sentence_cn)
        
        # TTS 播报
        tts_thread = threading.Thread(target=self._tts_worker, args=(sentence_cn,))
        tts_thread.start()
    

    def _tts_worker(self, sentence_cn: str):
        GeneralDataStorage.tts.say(sentence_cn)
        GeneralDataStorage.tts.runAndWait()

        # 播报结束后，保持播报内容不变
        self.broadcast_label.setText(sentence_cn)


    def enable_capture(self) -> None:
        try:
            self.capture = cv2.VideoCapture(self.camera_id_box.value())
            if not self.capture.isOpened():
                print("[text] 无法打开摄像头")
                self.capture_frame.setText(f"无法打开摄像头 {self.camera_id_box.value()}!")
                return
            
            print("[text] 成功打开摄像头")
            self.timer.start()
            self.capture_frame.setEnabled(True)
        except Exception as e:
            print(f"[text] 打开摄像头错误: {e}")
            self.capture_frame.setText("打开摄像头失败!")

    def disable_capture(self) -> None:
        self.textpic = None
        if self.capture is not None:
            self.capture.release()
            self.capture = None
        self.timer.stop()
        self.capture_frame.setEnabled(False)
        self.capture_frame.setText("摄像头未开启，请点击按钮。")

    def _update_frame(self) -> None:
        if not self.capture.isOpened():
            print("[text_recognition] 无法打开摄像头！")
            return

        succ, frame = self.capture.read()

        if succ:
            self.textpic = frame  # 更新 textpic 以便后续使用
            self.frame = frame  # 保留原始帧

            height, width, channel = frame.shape
            bytes_per_line = channel * width
            q_img = QImage(frame.data, width, height, bytes_per_line, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(q_img)
            self.capture_frame.setPixmap(pixmap)
        else:
            print("[text_recognition] 无法从摄像头读取帧")


class MethodQAWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()

        main_layout = QVBoxLayout(self)  # 主布局使用垂直布局

        splitter = QSplitter(self)

        # 显示摄像头画面
        self.capture_frame = QLabel("等待识别...")
        self.capture_frame.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.capture_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        splitter.addWidget(self.capture_frame)

        self.tts_display_label = QLabel("TTS 播报内容将显示在这里")
        self.tts_display_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.tts_display_label.setWordWrap(True)  # 启用自动换行
        self.tts_display_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        splitter.addWidget(self.tts_display_label)

        main_layout.addWidget(splitter)  # 将 splitter 添加到主布局中

        self.camera_id_box = QSpinBox()
        self.camera_id_box.setPrefix("设备号: ")

        self.switch_camera = QPushButton("开启/关闭摄像头")
        self.switch_camera.clicked.connect(self._on_switch_clicked)

        self.generate_sentence_button = QPushButton("生成说明句子并翻译播报")
        self.generate_sentence_button.clicked.connect(self._generate_sentence_and_broadcast)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.camera_id_box)
        button_layout.addWidget(self.switch_camera)
        button_layout.addWidget(self.generate_sentence_button)

        main_layout.addLayout(button_layout)

        self.capture = None

        self.timer = QTimer()
        self.timer.timeout.connect(self._update_frame)
        self.disable_capture()

        self.ocr = PaddleOCR(use_angle_cls=True, lang='ch')  # 支持中文

    def _on_switch_clicked(self):
        if self.capture is not None and self.capture.isOpened():
            self.disable_capture()
        else:
            self.enable_capture()

    def enable_capture(self) -> None:
        try:
            self.capture = cv2.VideoCapture(self.camera_id_box.value())
            if not self.capture.isOpened():
                print("[method] 无法打开摄像头")
                self.capture_frame.setText(f"无法打开摄像头 {self.camera_id_box.value()}!")
                return
            
            print("[method] 成功打开摄像头")
            self.timer.start()
            self.capture_frame.setEnabled(True)
        except Exception as e:
            print(f"[method] 打开摄像头错误: {e}")
            self.capture_frame.setText("打开摄像头失败!")

    def disable_capture(self) -> None:
        if self.capture is not None:
            self.capture.release()
            self.capture = None
        self.timer.stop()
        self.capture_frame.setEnabled(False)
        self.capture_frame.setText("摄像头未开启")

    def _update_frame(self) -> None:
        if not self.capture.isOpened():
            return
        ret, frame = self.capture.read()
        if ret:
            self.frame = frame
            height, width, channel = frame.shape
            bytes_per_line = channel * width
            q_img = QImage(frame.data, width, height, bytes_per_line, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(q_img)
            self.capture_frame.setPixmap(pixmap)

    def extract_text_from_frame(self):
        """ 从当前捕获的帧中提取文本 """
        if hasattr(self, 'frame'):
            temp_img_path = 'temp_frame.png'
            cv2.imwrite(temp_img_path, self.frame)
            result = self.ocr.ocr(temp_img_path, cls=True)
            text_cn = ''.join([line[1][0] for line in result[0]])  # 提取识别的文本
            print(f"OCR识别到的文本: {text_cn}")  # 输出识别结果用于调试
            return text_cn.strip()
        return None

    def _generate_sentence_and_broadcast(self):
        print("点击了生成说明句子并翻译播报按钮")

        text_cn = self.extract_text_from_frame()
        if text_cn:
            print(f"提取到的中文文本: {text_cn}")

            detected_energies = []
            for energy in CLEAN_ENERGY_CATEGORIES:
                if energy in text_cn:
                    detected_energies.append(energy)
            
            if detected_energies:
                energy_str = "、".join(detected_energies)
                sentence_cn = f"清洁能源，是指不排放污染物、能够直接用于生产生活的能源，例如‘{energy_str}’是一种清洁能源。"
                print(f"生成的中文句子: {sentence_cn}")
                
                sentence_en = baidu_translate(sentence_cn)
                if sentence_en:
                    print(f"翻译成英文的句子: {sentence_en}")
                else:
                    self.capture_frame.setText("翻译失败，请检查网络连接或重试。")
                    return

                self.capture_frame.setText(f"中文: {sentence_cn}\n英文: {sentence_en}")
                
                self.tts_broadcast(sentence_cn, sentence_en)
            else:
                self.capture_frame.setText("未识别到清洁能源类别")
                print("未识别到清洁能源类别")
        else:
            self.capture_frame.setText("未检测到中文文本")
            print("未检测到中文文本")

    def tts_broadcast(self, sentence_cn: str, sentence_en: str):
        self.tts_display_label.setText(f"TTS 播报中...\n中文: {sentence_cn}\n英文: {sentence_en}")
        
        tts_thread = threading.Thread(target=self._tts_worker, args=(sentence_cn, sentence_en))
        tts_thread.start()

    def _tts_worker(self, sentence_cn: str, sentence_en: str):
        GeneralDataStorage.tts.say(f"中文: {sentence_cn}")
        GeneralDataStorage.tts.say(f"英文: {sentence_en}")
        GeneralDataStorage.tts.runAndWait()

        self.tts_display_label.setText("TTS 播报完成")


class FaceRecognitionWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        # 初始化摄像头
        self.capture = None  # 先不创建VideoCapture对象
        self.known_faces = {}
        self.load_known_faces()

        layout = QVBoxLayout()

        self.name_label = QLabel("等待AI检测结果...")
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.name_label.setWordWrap(False)

        font = QFont()
        font.setPointSize(16)
        self.name_label.setFont(font)

        self.capture_frame = QLabel()  
        self.capture_frame.setAlignment(Qt.AlignCenter)

        self.camera_id_box = QSpinBox()
        self.camera_id_box.setPrefix("设备号: ")

        self.switch_camera = QPushButton("开启/关闭摄像头")
        self.switch_camera.clicked.connect(self._on_switch_clicked)

        self.detect_button = QPushButton("检测")
        self.detect_button.clicked.connect(self._on_detect_clicked)

        layout.addWidget(self.name_label)
        layout.addWidget(self.capture_frame)
        layout.addWidget(self.camera_id_box)
        layout.addWidget(self.switch_camera)
        layout.addWidget(self.detect_button)
        self.setLayout(layout)

        self.timer = QTimer()
        self.timer.timeout.connect(self._update_frame)
        self.disable_capture()

    def load_known_faces(self):
        faces_dir = 'test'
        if not os.path.exists(faces_dir):
            print(f"Error: Directory {faces_dir} does not exist.")
            return

        for file_name in os.listdir(faces_dir):
            file_path = os.path.join(faces_dir, file_name)
            print(f"Trying to load: {file_path}")

            if not os.path.isfile(file_path):
                print(f"Error: {file_path} is not a valid file.")
                continue

            try:
                pil_image = Image.open(file_path)
                img = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
            except Exception as e:
                print(f"Failed to load image at {file_path}: {e}")
                continue

            label = os.path.splitext(file_name)[0]
            face_encoding = self.get_face_encoding(img)
            if face_encoding is not None:
                self.known_faces[label] = face_encoding
                print(f"Loaded face for {label}")
            else:
                print(f"No face found in {file_name}")

    def get_face_encoding(self, img):
        rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        face_locations = face_recognition.face_locations(rgb_img)
        
        if len(face_locations) == 0:
            print("No faces found in the image.")
            return None

        encodings = face_recognition.face_encodings(rgb_img, face_locations)
        if len(encodings) > 0:
            return encodings[0]
        
        return None

    def _on_switch_clicked(self) -> None:
        if self.capture is not None and self.capture.isOpened():
            self.disable_capture()
        else:
            self.enable_capture()

    def enable_capture(self) -> None:
        try:
            # 创建新的VideoCapture对象
            self.capture = cv2.VideoCapture(self.camera_id_box.value())
            if not self.capture.isOpened():
                print("[face] 无法打开摄像头")
                self.capture_frame.setText(f"无法打开摄像头 {self.camera_id_box.value()}!")
                return
            
            print("[face] 成功打开摄像头")
            self.timer.start()
            self.capture_frame.setEnabled(True)
        except Exception as e:
            print(f"[face] 打开摄像头错误: {e}")
            self.capture_frame.setText("打开摄像头失败!")

    def disable_capture(self) -> None:
        if self.capture is not None:
            self.capture.release()
            self.capture = None
        self.timer.stop()
        self.capture_frame.setEnabled(False)
        self.capture_frame.setText("摄像头未开启，请点击按钮。")

    def _update_frame(self) -> None:
        if not self.capture.isOpened():
            return

        ret, frame = self.capture.read()
        if ret:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            self.__draw_frame(rgb_frame)

    def _on_detect_clicked(self):
        if not self.capture.isOpened():
            print("Camera is not opened.")
            return

        ret, frame = self.capture.read()
        if ret:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            face_encodings = face_recognition.face_encodings(rgb_frame)

            for face_encoding in face_encodings:
                matches = face_recognition.compare_faces(list(self.known_faces.values()), face_encoding)
                if True in matches:
                    match_index = matches.index(True)
                    person_name = list(self.known_faces.keys())[match_index]
                    self._display_and_speak_result(person_name)
                    return

            self.name_label.setText("No face detected or not recognized.")

    def _display_and_speak_result(self, person_name: str) -> None:
        introductions = {
            "he": "这是贺德馨，中国空气动力研究与发展中心原总工程师。",
            "peng": "这是彭士禄，中国核动力领域的开拓者和奠基者之一。",
            "panjia": "这是潘家铮，水工结构和水电建设专家。",
            "zheng": "这是郑守仁，长江三峡工程总设计师。",
            "zhangguang": "这是张光斗，中国水利水电事业的主要开拓者之一。"
        }

        intro_text = introductions.get(person_name, f"这是{person_name}")

        self.name_label.setText(intro_text)

        QTimer.singleShot(1500, lambda: self._speak_text(intro_text))

    def _speak_text(self, text: str) -> None:
        GeneralDataStorage.tts.say(text)
        GeneralDataStorage.tts.runAndWait()

    def __draw_frame(self, frame) -> None:
        height, width, channel = frame.shape
        bytes_per_line = 3 * width
        q_image = QImage(frame.data, width, height, bytes_per_line, QImage.Format_RGB888)
        
        pixmap = QPixmap.fromImage(q_image)
        self.capture_frame.setPixmap(pixmap)
        self.capture_frame.setAlignment(Qt.AlignCenter)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle(QStyleFactory.create("Fusion"))

    dark_palette = QPalette()
    dark_palette.setColor(QPalette.Window, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.WindowText, Qt.white)
    dark_palette.setColor(QPalette.Base, QColor(42, 42, 42))
    dark_palette.setColor(QPalette.AlternateBase, QColor(66, 66, 66))
    dark_palette.setColor(QPalette.ToolTipBase, Qt.white)
    dark_palette.setColor(QPalette.ToolTipText, Qt.white)
    dark_palette.setColor(QPalette.Text, Qt.white)
    dark_palette.setColor(QPalette.Button, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.ButtonText, Qt.white)
    dark_palette.setColor(QPalette.BrightText, Qt.red)
    dark_palette.setColor(QPalette.Link, QColor(42, 130, 218))

    app.setPalette(dark_palette)

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
