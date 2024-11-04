import dataclasses

import cv2
import numpy as np
from pyzbar.pyzbar import decode


@dataclasses.dataclass
class CodeResult(tuple):
    data: list[bytes]


def mark_code(_frame: cv2.typing.MatLike) -> CodeResult:
    """
    Decodes an image
    :param _frame: The colored image used to draw rects
    :param _binary: The gray-scale image used to find qrcodes & barcodes
    :return:
    """

    _binary = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    _binary = cv2.adaptiveThreshold(_binary, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 35, 2)
    data_ = []
    for code in decode(_binary):
        points = np.array(code.polygon, np.int32)
        rect = code.rect
        data: bytes = code.data
        cv2.polylines(_frame, [points], True, (0, 0, 255), 2, cv2.LINE_AA)
        # cv2.fillPoly(_frame, [points], (0, 0, 255), cv2.LINE_AA)
        cv2.putText(_frame, data.decode("utf-8"), (rect[0], rect[1]), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 1)
        data_.append(data)
    return CodeResult(data_)


if __name__ == "__main__":
    capture = cv2.VideoCapture(0)

    while True:
        if capture.isOpened():
            succ, frame = capture.read()
            if not succ:
                break

            result = mark_code(frame)
            # print("--------------------")
            if len(result.data) != 0:
                for text in map(lambda b: b.decode("utf-8"), result.data):
                    ...
                    if text.isdigit():
                        match int(text):
                            case 1:
                                print("结果为1")
                            case 2:
                                print("结果为2")
                            case n:
                                print("未知数字:", n)
                    else:
                        print(text)
                    # print(text)
                # break

            cv2.imshow("Result", frame)
            if cv2.waitKey(1) == ord("q"):
                break
