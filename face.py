import time
import torch
import argparse
import os
from typing import *
import cv2
import numpy as np
import pyttsx3
from cv2.typing import *
from paddleocr import PaddleOCR
from ultralytics import YOLO

USE_CUDA = False
if USE_CUDA:
    from cv2.cuda import CascadeClassifier
else:
    from cv2 import CascadeClassifier

Img: TypeAlias = MatLike


class FaceDetector:
    yolo = YOLO(r"yolov8n-oiv7.pt")
    if USE_CUDA:
        face_cascade: cv2.cuda.CascadeClassifier = CascadeClassifier.create("haarcascade_frontalface_default_cuda.xml")
    else:
        face_cascade: cv2.CascadeClassifier = CascadeClassifier("haarcascade_frontalface_alt2.xml")

    @classmethod
    def detect_face(cls, img: Img) -> tuple[np.ndarray | None, Rect | None]:
        """裁剪图片,只保留脸部"""
        if USE_CUDA:
            _gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            gray = cv2.cuda.GpuMat()
            gray.upload(_gray)
        else:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        # print(gray)
        if not USE_CUDA:
            faces = FaceDetector.face_cascade.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=1)
        else:
            _faces = FaceDetector.face_cascade.detectMultiScale(gray)
            # print("_faces", _faces)
            faces: MatLike = _faces.download()
            if faces is None:
                return None, None
            faces = list(faces[0, :, :])
            # FaceDetector.face_cascade.convert(faces, _faces)
        # print("faces", faces)
        
        if len(faces) == 0:
            return None, None
        # print(faces[0, :, :])
        (x, y, w, h) = faces[0]
        # return (gray[y: y + w, x: x + h], faces[0])
        _ret = gray.download()
        return _ret[y: y + h, x: x + w], faces[0]

    @classmethod
    def detect_face_yolo(cls, image0: MatLike) -> tuple[np.ndarray | None, Rect | None]:
        image = image0.copy()
        results = cls.yolo.predict(image, verbose=False, classes=[264])
        for result in results:
            for box in result.boxes:
                if box.conf[0] > 0.5:  # Human Face
                    _box: torch.Tensor = box.xywh
                    (x, y, w, h) = tuple(map(int, _box.cpu().numpy()[0]))
                    (x, y, w, h) = x - w // 2, y - h // 2, w, h
                    return (cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)[y: y + h, x: x + w],
                            (x, y, w, h))
        # for result in results:
        #     for box in result.boxes:
        #         if box.cls[0] == 264 and box.conf[0] > 0.5:  # Human Face
        #             _box: torch.Tensor = box.xywh
        #             (x, y, w, h) = tuple(map(int, _box.cpu().numpy()[0]))
        #             (x, y, w, h) = x - w // 2, y - h // 2, w, h
        #             return (cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)[y: y + h, x: x + w],
        #                     (x, y, w, h))
        return None, None

    @classmethod
    def cvt_img(cls, img: Img) -> tuple[np.ndarray, Rect]:
        size = img.shape
        if len(size) != 3:
            raise RuntimeError("Unexpected dimensions of numpy.ndarray as an image: " + repr(size))
        return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), (0, 0, size[0], size[1])

    @classmethod
    def walk_files(cls, dir_path) -> list[Img]:
        faces = []
        for file in os.listdir(dir_path):
            if os.path.isfile(os.path.join(dir_path, file)):
                c = os.path.basename(file)
                name = dir_path + "\\" + c
                img = cv2.imread(name)
                face, _ = FaceDetector.detect_face(img)
                if face is not None:
                    faces.append(face)
        return faces

    @classmethod
    def draw_rect(cls, img: Img, rect: Rect) -> None:
        (x, y, w, h) = rect
        cv2.rectangle(img, (x, y), (x + w, y + h), (255, 255, 255), 1)

    @classmethod
    def draw_text(cls, img: MatLike, text: str, x: int, y: int) -> None:
        cv2.putText(img, text, (x, y), cv2.FONT_HERSHEY_COMPLEX, 1, (128, 128, 0), 2)

    def __init__(self) -> None:
        self.recognizer = cv2.face.LBPHFaceRecognizer.create()
        self.ready = False

    def fit(self, train_data: list[Img], train_label: np.ndarray, output: str = "train.yml") -> None:
        self.recognizer.train(train_data, train_label)
        self.recognizer.write(output)
        self.ready = True

    def infer(self, _img: Img, labels: list[str], read_from_disk: bool = False,
              _input: str = "train.yml") -> tuple[Img, tuple[int, float]]:
        if not self.ready:
            self.recognizer.read(_input)

        if read_from_disk:
            self.recognizer.read(_input)
        img = _img.copy()
        time_ = int(time.time() * 1000)
        (face, rect) = FaceDetector.detect_face_yolo(img)
        # print("Face det used", int(time.time() * 1000) - time_, "ms")
        if rect is None:
            return img, (-1, float("inf"))
        (x, y, _, _) = rect
        label = self.recognizer.predict(face)
        # label[1]数值越低，可信度越高
        if label[1] <= 50:
            label_text = labels[label[0]]
            l = label_text + str(label[1])
            # print(l)
            FaceDetector.draw_rect(img, rect)
            FaceDetector.draw_text(img, l, x, y)
            return img, label
        else:
            FaceDetector.draw_rect(img, rect)
            FaceDetector.draw_text(img, "(%s %d)" % (labels[label[0]], label[1]), x, y)
            return img, label


class FaceData:
    def __init__(self) -> None:
        face_data: MutableMapping[tuple[int, str], list[Img]] = {}
        self.face_data = face_data
        pass

    def add_image(self, label: str, img: Img) -> None:
        keys = list(self.face_data.keys())
        found = False
        found_key = None
        for key in keys:
            (_, name) = key
            if name == label:
                if found:
                    raise RuntimeError("Find duplicated label: " + repr(found_key) + " and " + repr(key))
                images = self.face_data[key]
                if images is not None:
                    images.append(img)
                else:
                    self.face_data[key] = [img]
                found_key = key
                found = True
        else:
            if not found:
                index = max(map(lambda l: l[0], keys)) + 1
                self.face_data[(index, label)] = [img]

    def add_label(self, name: str, index: int | None):
        keys = list(self.face_data.keys())
        if index is None:
            index = max(map(lambda l: l[0], keys)) + 1
            self.face_data[(index, name)] = []
        else:
            for key in keys:
                (_, _name) = key
                if _name == name:
                    raise RuntimeError("Find duplicated label: " + repr((index, name)) + " and " + repr(key))
            self.face_data[(index, name)] = []

    def get_labels(self) -> list[str]:
        return list(map(lambda l: l[1], sorted(list(self.face_data.keys()))))

    def get_name(self, _index: int) -> str | None:
        for (label, _) in self.face_data.items():
            if _index == label[0]:
                return label[1]
        return None

    def genenrate_train_data(self) -> tuple[list[Img], list[int]]:
        images = []
        labels = []
        assert isinstance(list(self.face_data.keys())[0], tuple)
        for (label, _imgs) in self.face_data.items():
            for img in _imgs:
                images.append(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY))
                labels.append(label[0])
        return images, labels


class OCR:
    def __init__(self):
        ocr = PaddleOCR(use_angle_cls=True, lang="ch")
        self.ocr = ocr

    def get_text(self, img: Img) -> tuple[str | None, float | None]:
        results = self.ocr.ocr(img)
        if len(results) == 0:
            return None, None
        results = results[0]
        if results is None:
            return None, None
        _max = max(results, key=lambda d: d[1][1])
        return _max[1][0], _max[1][1]


class GeneralDataStorage:
    window: Any
    args: argparse.Namespace
    detector: FaceDetector
    ocr: OCR
    tts: pyttsx3.Engine
    face_data: FaceData
    # labels: list[str]
    privilege: list[int] = [0, 0, 0, 0]
    found: bool = False
    threshold = 70
    FACE_FILE_DATA: list[tuple[str, str]]

    @classmethod
    def get_labels(cls) -> list[str]:
        return cls.face_data.get_labels()
