import sys
import serial
import serial.tools.list_ports
import threading
from typing import Callable
import ctypes
import _thread


class SerialListener(threading.Thread):
    def __init__(self, com_name: str, recv_callback: Callable[[str], None], baudrate: int = 115200):
        super().__init__(name="Com Listener", daemon=True)
        self.com_name = com_name
        self.baudrate = baudrate
        self.callback = recv_callback

    def run(self):
        try:
            _serial = serial.Serial(self.com_name, self.baudrate)
            if _serial.is_open:
                while True:
                    b = _serial.readline().strip()
                    b = b.removeprefix(b"\x00\xfe")
                    b = b.replace(b"\x00", b"")
                    b = b.replace(b"\xfe", b"")
                    # print(b)
                    msg = str(b, encoding="gbk", errors="ignore").strip()
                    print("[serial_thread\t] recv: " + msg)
                    if msg.endswith("stop"):
                        break
                    self.callback(msg)
            else:
                sys.stderr.write("Cannot open %s\n" % self.name)
        except InterruptedError:
            print("[serial_thread\t] Com Listener exit")
            pass
        except serial.SerialException:
            print("[serial_thread\t] Serial closed")

    def terminate(self):
        # hacky
        ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_ulong(self.ident), ctypes.py_object(InterruptedError))
