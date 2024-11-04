import cv2
import argparse
from PyQt5.QtWidgets import QApplication
from ui import *
import _thread as thread
import pyttsx3
import time

def tts_loop_thread():
    """启动 TTS 的循环线程"""
    while True:
        try:
            if not GeneralDataStorage.tts.isBusy():
                print("[tts_loop\t\t] TTS Driver is busy now")
            GeneralDataStorage.tts.runAndWait()
        except (Exception, OSError) as e:
            print(e)
        time.sleep(0.5)


def __main__() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--capture", "-c", default=0, type=int, help="摄像头索引")
    parser.add_argument("--autofocus", action="store_true", help="尝试为摄像头启用自动对焦")
    parser.add_argument("--timeout", default=None, type=int, help="指定音频录制的超时时间。默认是 None。")
    args = parser.parse_args()

    # 初始化 TTS 引擎
    tts = pyttsx3.init()
    
    # 初始化人脸数据存储
    face_data = FaceData()

    # 存储全局数据
    GeneralDataStorage.args = args
    GeneralDataStorage.tts = tts
    GeneralDataStorage.face_data = face_data  # 确保已初始化 face_data

    # 启动 TTS 线程
    thread.start_new_thread(tts_loop_thread, ())

    # 启动应用
    app = QApplication([])
    window = MainWindow()  # 使用 ui.py 中的 MainWindow
    GeneralDataStorage.window = window
    window.show()

    app.exec()



if __name__ == "__main__":
    __main__()
