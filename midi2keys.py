import ctypes
import json
import logging
import logging.handlers
import queue
import os
import threading
import time
import sys
from typing import Dict, Optional

try:
    import mido
except Exception as e:
    print("Missing dependencies: mido and python-rtmidi are required.")
    print("Install with: pip install mido python-rtmidi")
    raise
try:
    import mido.backends.rtmidi
    import rtmidi
    mido.set_backend("mido.backends.rtmidi")
except Exception:
    pass


INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_SCANCODE = 0x0008
KEYEVENTF_UNICODE = 0x0004
MAPVK_VK_TO_VSC = 0
PTR_ULONG = ctypes.c_ulong if ctypes.sizeof(ctypes.c_void_p) == 4 else ctypes.c_ulonglong
SCAN_CACHE: Dict[int, int] = {}

class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", ctypes.c_ushort),
        ("wScan", ctypes.c_ushort),
        ("dwFlags", ctypes.c_uint),
        ("time", ctypes.c_uint),
        ("dwExtraInfo", PTR_ULONG),
    ]

class INPUT_I(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT)]

class INPUT(ctypes.Structure):
    _anonymous_ = ("i",)
    _fields_ = [("type", ctypes.c_uint), ("i", INPUT_I)]

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
user32.SendInput.argtypes = [ctypes.c_uint, ctypes.POINTER(INPUT), ctypes.c_int]
user32.SendInput.restype = ctypes.c_uint
user32.MapVirtualKeyW.argtypes = [ctypes.c_uint, ctypes.c_uint]
user32.MapVirtualKeyW.restype = ctypes.c_uint
user32.keybd_event.argtypes = [ctypes.c_ubyte, ctypes.c_ubyte, ctypes.c_uint, PTR_ULONG]
user32.keybd_event.restype = None

VK_SPECIAL = {
    "SPACE": 0x20,
    "ENTER": 0x0D,
    "TAB": 0x09,
    "ESC": 0x1B,
    "LEFT": 0x25,
    "UP": 0x26,
    "RIGHT": 0x27,
    "DOWN": 0x28,
    "BACKSPACE": 0x08,
}

def to_vk(key: str) -> Optional[int]:
    if not key:
        return None
    k = key.strip()
    up = k.upper()
    if up in VK_SPECIAL:
        return VK_SPECIAL[up]
    if len(k) == 1:
        c = k.upper()
        oc = ord(c)
        if ("A" <= c <= "Z") or ("0" <= c <= "9"):
            return oc
        if k in (";", ",", ".", "/"):
            if k == ";":
                return 0xBA
            if k == ",":
                return 0xBC
            if k == ".":
                return 0xBE
            if k == "/":
                return 0xBF
    return None

def vk_to_scan(vk: int) -> int:
    try:
        return int(user32.MapVirtualKeyW(vk, MAPVK_VK_TO_VSC))
    except Exception:
        return 0
def get_scan_code(vk: int) -> int:
    sc = SCAN_CACHE.get(vk)
    if sc is None:
        sc = vk_to_scan(vk)
        SCAN_CACHE[vk] = sc
    return sc

def send_input_checked(ki: KEYBDINPUT):
    inp = INPUT()
    inp.type = INPUT_KEYBOARD
    inp.i.ki = ki
    ret = user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))
    if ret != 1:
        return False, int(kernel32.GetLastError())
    return True, 0
def error_text(err: int) -> str:
    buf = ctypes.create_unicode_buffer(512)
    flags = 0x00001000 | 0x00000200
    kernel32.FormatMessageW(flags, None, err, 0, buf, len(buf), None)
    return buf.value.strip()

def key_down(vk: int):
    sc = get_scan_code(vk)
    if sc:
        ki = KEYBDINPUT(wVk=0, wScan=sc, dwFlags=KEYEVENTF_SCANCODE, time=0, dwExtraInfo=0)
        ok, err = send_input_checked(ki)
        if ok:
            return ok, err
    ki2 = KEYBDINPUT(wVk=vk, wScan=0, dwFlags=0, time=0, dwExtraInfo=0)
    return send_input_checked(ki2)

def key_up(vk: int):
    sc = get_scan_code(vk)
    if sc:
        ki = KEYBDINPUT(wVk=0, wScan=sc, dwFlags=KEYEVENTF_KEYUP | KEYEVENTF_SCANCODE, time=0, dwExtraInfo=0)
        ok, err = send_input_checked(ki)
        if ok:
            return ok, err
    ki2 = KEYBDINPUT(wVk=vk, wScan=0, dwFlags=KEYEVENTF_KEYUP, time=0, dwExtraInfo=0)
    return send_input_checked(ki2)

def key_tap(vk: int, ms: int):
    ok1, e1 = key_down(vk)
    if not ok1:
        return False, e1
    time.sleep(max(ms, 0) / 1000.0)
    ok2, e2 = key_up(vk)
    if not ok2:
        return False, e2
    return True, 0
def unicode_tap(ch: str, ms: int):
    if not ch or len(ch) != 1:
        return False, 87
    code = ord(ch)
    ki_down = KEYBDINPUT(wVk=0, wScan=code, dwFlags=KEYEVENTF_UNICODE, time=0, dwExtraInfo=0)
    ok1, e1 = send_input_checked(ki_down)
    if not ok1:
        return False, e1
    time.sleep(max(ms, 0) / 1000.0)
    ki_up = KEYBDINPUT(wVk=0, wScan=code, dwFlags=KEYEVENTF_UNICODE | KEYEVENTF_KEYUP, time=0, dwExtraInfo=0)
    ok2, e2 = send_input_checked(ki_up)
    if not ok2:
        return False, e2
    return True, 0
def keybd_event_tap(vk: int, ms: int):
    sc = get_scan_code(vk)
    try:
        user32.keybd_event(ctypes.c_ubyte(vk), ctypes.c_ubyte(sc), 0, PTR_ULONG(0))
        time.sleep(max(ms, 0) / 1000.0)
        user32.keybd_event(ctypes.c_ubyte(vk), ctypes.c_ubyte(sc), KEYEVENTF_KEYUP, PTR_ULONG(0))
        return True, 0
    except Exception:
        return False, 87
def keybd_event_down(vk: int):
    sc = get_scan_code(vk)
    try:
        user32.keybd_event(ctypes.c_ubyte(vk), ctypes.c_ubyte(sc), 0, PTR_ULONG(0))
        return True, 0
    except Exception:
        return False, 87
def keybd_event_up(vk: int):
    sc = get_scan_code(vk)
    try:
        user32.keybd_event(ctypes.c_ubyte(vk), ctypes.c_ubyte(sc), KEYEVENTF_KEYUP, PTR_ULONG(0))
        return True, 0
    except Exception:
        return False, 87
def key_down_any(vk: int, backend: str):
    if backend == "sendinput":
        ok, err = key_down(vk)
        return ok, err
    if backend == "keybd":
        ok, err = keybd_event_down(vk)
        return ok, err
    ok, err = key_down(vk)
    if ok:
        return ok, err
    ok2, err2 = keybd_event_down(vk)
    if ok2:
        return ok2, 0
    return False, err
def key_up_any(vk: int, backend: str):
    if backend == "sendinput":
        ok, err = key_up(vk)
        return ok, err
    if backend == "keybd":
        ok, err = keybd_event_up(vk)
        return ok, err
    ok, err = key_up(vk)
    if ok:
        return ok, err
    ok2, err2 = keybd_event_up(vk)
    if ok2:
        return ok2, 0
    return False, err
def key_tap_any(vk: int, ms: int):
    ok, err = key_tap(vk, ms)
    if ok:
        return ok, err
    ok2, err2 = keybd_event_tap(vk, ms)
    if ok2:
        return ok2, 0
    return False, err

def midi_note_name(note: int) -> str:
    names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    n = int(note)
    return f"{names[n % 12]}{(n // 12) - 1}"

class Mapping:
    def __init__(self, notes: Dict[int, str]):
        self._note_to_vk: Dict[int, int] = {}
        self._note_to_key: Dict[int, str] = {}
        for k, v in notes.items():
            try:
                n = int(k)
                vk = to_vk(v)
                if vk is not None:
                    self._note_to_vk[n] = vk
                    self._note_to_key[n] = v
            except:
                pass

    def vk_for_note(self, note: int) -> Optional[int]:
        return self._note_to_vk.get(note)
    def key_for_note(self, note: int) -> Optional[str]:
        return self._note_to_key.get(note)

class MidiMapper:
    def __init__(self, mapping: Mapping, mode: str, tap_ms: int, velocity_threshold: int, channel: Optional[int], logger: logging.Logger, verbose: bool, per_event: bool, backend: str, log_mode: str):
        self.mapping = mapping
        self.mode = mode
        self.tap_ms = tap_ms
        self.velocity_threshold = velocity_threshold
        self.channel = channel
        self.logger = logger
        self.verbose = verbose
        self.per_event = per_event
        self.backend = backend
        self.log_mode = (log_mode or "info").lower()
        self._lock = threading.Lock()
        self._pressed: Dict[int, int] = {}
        self._onpress = set()
        self._count = 0
        self._start = time.time()
        self._lat_sum = 0.0
        self._lat_cnt = 0

    def stats_line(self) -> str:
        elapsed = max(time.time() - self._start, 1e-6)
        rate = self._count / elapsed
        avg = (self._lat_sum / self._lat_cnt) if self._lat_cnt > 0 else 0.0
        return f"events:{self._count} rate:{rate:.1f}/s pressed:{len(self._pressed)} avg_latency:{avg:.1f}ms"

    def handle(self, msg):
        try:
            if getattr(self, "log_mode", "info") == "debug":
                try:
                    ts_ms = int(time.time() * 1000)
                    ch = (getattr(msg, "channel", 0) or 0) + 1
                    n = getattr(msg, "note", None)
                    v = getattr(msg, "velocity", None)
                    print(f"[DEBUG midi2keys] {ts_ms} type:{msg.type} ch:{ch} note:{int(n) if n is not None else '-'} vel:{int(v) if v is not None else '-'} raw:{msg}")
                except Exception:
                    pass
            if msg.type == "note_on" and msg.velocity == 0:
                msg = mido.Message("note_off", note=msg.note, channel=getattr(msg, "channel", 0))
            t = msg.type
            if t not in ("note_on", "note_off"):
                return
            if self.channel is not None and getattr(msg, "channel", None) is not None:
                if msg.channel != self.channel:
                    return
            note = msg.note
            vk = self.mapping.vk_for_note(note)
            if vk is None:
                if self.verbose:
                    self.logger.debug(f"Unmapped note:{note}")
                return
            if self.mode == "press":
                if t == "note_on":
                    with self._lock:
                        if note in self._onpress:
                            return
                        self._onpress.add(note)
                        self._count += 1
                    st = time.perf_counter()
                    ok, err = key_tap_any(vk, self.tap_ms) if self.backend == "auto" else (
                        key_tap(vk, self.tap_ms) if self.backend == "sendinput" else
                        keybd_event_tap(vk, self.tap_ms)
                    )
                    lat = (time.perf_counter() - st) * 1000.0
                    with self._lock:
                        self._lat_sum += lat
                        self._lat_cnt += 1
                    keyname = self.mapping.key_for_note(note)
                    nname = midi_note_name(note)
                    if ok:
                        if getattr(self, "log_mode", "info") == "debug":
                            try:
                                ts_ms = int(time.time() * 1000)
                                print(f"[DEBUG midi2keys] {ts_ms} map:{nname}->{keyname} vk:{vk} mods:none rule:notes latency:{lat:.1f}ms")
                            except Exception:
                                pass
                    else:
                        if keyname and len(keyname) == 1:
                            st2 = time.perf_counter()
                            ok2, err2 = unicode_tap(keyname, self.tap_ms)
                            lat2 = (time.perf_counter() - st2) * 1000.0
                            with self._lock:
                                self._lat_sum += lat2
                                self._lat_cnt += 1
                            if ok2:
                                if getattr(self, "log_mode", "info") == "debug":
                                    try:
                                        ts_ms = int(time.time() * 1000)
                                        print(f"[DEBUG midi2keys] {ts_ms} map:{nname}->{keyname} vk:unicode mods:none rule:notes latency:{lat2:.1f}ms")
                                    except Exception:
                                        pass
                            else:
                                if getattr(self, "log_mode", "info") == "debug":
                                    try:
                                        ts_ms = int(time.time() * 1000)
                                        print(f"[DEBUG midi2keys] {ts_ms} map_failed:{nname}->{keyname} err:{err} fb_err:{err2}")
                                    except Exception:
                                        pass
                else:
                    with self._lock:
                        if note in self._onpress:
                            self._onpress.remove(note)
                        self._count += 1
                return
            if t == "note_on":
                if msg.velocity < self.velocity_threshold:
                    return
                with self._lock:
                    self._count += 1
                if self.mode == "tap":
                    st = time.perf_counter()
                    ok, err = key_tap_any(vk, self.tap_ms) if self.backend == "auto" else (
                        key_tap(vk, self.tap_ms) if self.backend == "sendinput" else
                        keybd_event_tap(vk, self.tap_ms)
                    )
                    lat = (time.perf_counter() - st) * 1000.0
                    with self._lock:
                        self._lat_sum += lat
                        self._lat_cnt += 1
                    if getattr(self, "log_mode", "info") == "debug":
                        try:
                            ts_ms = int(time.time() * 1000)
                            if ok:
                                print(f"[DEBUG midi2keys] {ts_ms} tap note:{note} vk:{vk} latency:{lat:.1f}ms")
                            else:
                                print(f"[DEBUG midi2keys] {ts_ms} tap_failed note:{note} vk:{vk} err:{err}")
                        except Exception:
                            pass
                else:
                    with self._lock:
                        if note not in self._pressed:
                            self._pressed[note] = vk
                            okd, errd = key_down_any(vk, self.backend)
                            if getattr(self, "log_mode", "info") == "debug":
                                try:
                                    ts_ms = int(time.time() * 1000)
                                    if okd:
                                        print(f"[DEBUG midi2keys] {ts_ms} down note:{note} vk:{vk}")
                                    else:
                                        print(f"[DEBUG midi2keys] {ts_ms} down_failed note:{note} vk:{vk} err:{errd}")
                                except Exception:
                                    pass
            else:
                with self._lock:
                    self._count += 1
                if self.mode == "hold":
                    with self._lock:
                        vk2 = self._pressed.pop(note, None)
                    if vk2 is not None:
                        oku, erru = key_up_any(vk2, self.backend)
                        if getattr(self, "log_mode", "info") == "debug":
                            try:
                                ts_ms = int(time.time() * 1000)
                                if oku:
                                    print(f"[DEBUG midi2keys] {ts_ms} up note:{note} vk:{vk2}")
                                else:
                                    print(f"[DEBUG midi2keys] {ts_ms} up_failed note:{note} vk:{vk2} err:{erru}")
                            except Exception:
                                pass
        except Exception as e:
            if getattr(self, "log_mode", "info") != "nolog":
                self.logger.error(f"Failed to handle message: {e}")

def setup_logger(log_path: str, verbose: bool, level_name: Optional[str] = None, max_bytes: int = 1048576, backup_count: int = 3, async_log: bool = False, no_file: bool = False):
    logger = logging.getLogger("midi2keys")
    try:
        old_listener = getattr(logger, "_listener", None)
        if old_listener:
            old_listener.stop()
    except Exception:
        pass
    try:
        for h in list(logger.handlers):
            try:
                logger.removeHandler(h)
                try:
                    h.flush()
                except Exception:
                    pass
                try:
                    h.close()
                except Exception:
                    pass
            except Exception:
                pass
    except Exception:
        pass
    level_map = {"info": logging.INFO, "debug": logging.DEBUG, "nolog": logging.CRITICAL}
    level = level_map.get((level_name or "info").lower(), logging.INFO)
    logger.setLevel(level)
    logger.propagate = False
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    if (level_name or "").lower() == "nolog":
        logger.disabled = True
        return logger
    if async_log:
        q = queue.Queue(-1)
        qh = logging.handlers.QueueHandler(q)
        logger.addHandler(qh)
        handlers = []
        sh = logging.StreamHandler(sys.stdout)
        sh.setFormatter(fmt)
        sh.setLevel(level)
        handlers.append(sh)
        if not no_file:
            try:
                fh = logging.handlers.RotatingFileHandler(log_path, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8")
                fh.setFormatter(fmt)
                fh.setLevel(level)
                handlers.append(fh)
            except Exception:
                pass
        listener = logging.handlers.QueueListener(q, *handlers, respect_handler_level=True)
        listener.start()
        logger._listener = listener  # attach for later stop
    else:
        sh = logging.StreamHandler(sys.stdout)
        sh.setFormatter(fmt)
        sh.setLevel(level)
        logger.addHandler(sh)
        if not no_file:
            try:
                fh = logging.handlers.RotatingFileHandler(log_path, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8")
                fh.setFormatter(fmt)
                fh.setLevel(level)
                logger.addHandler(fh)
            except Exception:
                pass
    return logger

def load_config(path: Optional[str]) -> Dict:
    default = {
        "device": "",
        "mode": "tap",
        "tap_ms": 15,
        "velocity_threshold": 1,
        "channel": None,
        "notes": {
            "60": "Y",
            "61": "U",
            "62": "I",
            "63": "O",
            "64": "P"
        }
    }
    if not path:
        return default
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for k in default:
            if k not in data:
                data[k] = default[k]
        return data
    except Exception:
        return default

def list_devices(logger: logging.Logger):
    try:
        ins = mido.get_input_names()
        outs = mido.get_output_names()
        logger.info("Available input devices:")
        for i, n in enumerate(ins):
            logger.info(f"[{i}] {n}")
        logger.info("Available output devices:")
        for i, n in enumerate(outs):
            logger.info(f"[{i}] {n}")
    except Exception as e:
        logger.error(f"Failed to enumerate devices: {e}")

def main():
    def get_config_path():
        try:
            if getattr(sys, "frozen", False):
                exe_dir = os.path.dirname(sys.executable)
                p1 = os.path.join(exe_dir, "mapping.json")
                if os.path.exists(p1):
                    return p1
                meipass = getattr(sys, "_MEIPASS", None)
                if meipass:
                    p2 = os.path.join(meipass, "mapping.json")
                    if os.path.exists(p2):
                        return p2
        except Exception:
            pass
        return os.path.join(os.path.dirname(__file__), "mapping.json")
    config_path = get_config_path()
    cfg = load_config(config_path)

    def interactive():
        def pick_lang():
            print("选择语言 / Choose Language")
            print("1. 中文")
            print("2. English")
            while True:
                s = input("> ").strip().lower()
                if s in ("1", "zh", "cn", "chinese", "中文"):
                    return "zh"
                if s in ("2", "en", "english"):
                    return "en"
                print("输入无效，请重新输入 / Invalid input, please try again")
        def t(zh, en):
            return zh if lang == "zh" else en
        lang = "zh"
        lang = pick_lang()
        # devices
        ins = mido.get_input_names()
        if not ins:
            print("未检测到任何MIDI输入设备" if lang == "zh" else "No MIDI input devices detected")
            return None
        print(t("请选择输入设备（显示：序号 名称 | 标识）：", "Select an input device (shown: index name | id):"))
        for i, n in enumerate(ins):
            print(f"[{i}] {n} | id:{n}")
        sel_name = None
        while True:
            s = input("> ").strip()
            if s.isdigit():
                idx = int(s)
                if 0 <= idx < len(ins):
                    sel_name = ins[idx]
                    break
            # allow substring
            low = s.lower()
            matches = [n for n in ins if low and low in n.lower()]
            if len(matches) == 1:
                sel_name = matches[0]
                break
            print(t("输入无效，请输入序号或名称子串（唯一匹配）", "Invalid input, enter index or a unique name substring"))
        # mode
        print(t("请选择模式：", "Select mode:"))
        print("1.press  2.tap  3.hold  4.monitor")
        sel_mode = None
        while True:
            s = input("> ").strip().lower()
            mmap = {"1": "press", "2": "tap", "3": "hold", "4": "monitor",
                    "press": "press", "tap": "tap", "hold": "hold", "monitor": "monitor"}
            if s in mmap:
                sel_mode = mmap[s]
                break
            print(t("输入无效，请重新输入", "Invalid input, please try again"))
        # injection backend
        print(t("请选择注入后端：", "Select injection backend:"))
        print("1.auto  2.sendinput  3.keybd")
        sel_backend = None
        while True:
            s = input("> ").strip().lower()
            bmap = {"1": "auto", "2": "sendinput", "3": "keybd",
                    "auto": "auto", "sendinput": "sendinput", "keybd": "keybd"}
            if s in bmap:
                sel_backend = bmap[s]
                break
            print(t("输入无效，请重新输入", "Invalid input, please try again"))
        # log mode
        print(t("请选择日志模式：", "Select log mode:"))
        print("1.DEBUG  2.INFO  3.NOLOG")
        sel_mode_log = None
        while True:
            s = input("> ").strip().lower()
            lmap = {"1": "debug", "2": "info", "3": "nolog",
                    "debug": "debug", "info": "info", "nolog": "nolog"}
            if s in lmap:
                sel_mode_log = lmap[s]
                break
            print(t("输入无效，请重新输入", "Invalid input, please try again"))
        # finalize logger
        logger2 = setup_logger(os.path.join(os.path.dirname(__file__), "midi2keys.log"), False, sel_mode_log, async_log=True, no_file=(sel_mode_log == "nolog"))
        # load mapping.json and override device/mode dynamically
        cfg2 = load_config(config_path)
        cfg2["device"] = sel_name
        cfg2["mode"] = sel_mode
        return (logger2, cfg2, sel_name, lang, sel_backend, sel_mode_log)

    # Interactive mode is mandatory
    res = interactive()
    if res is None:
        return
    logger, cfg, sel, lang, backend, log_mode = res
    if log_mode != "nolog":
        print("程序运行中，按 Ctrl+C 退出" if lang == "zh" else "Running... press Ctrl+C to exit")

    if cfg["mode"] == "monitor":
        print(f"device:{sel}")
        def mon_cb(msg):
            t = getattr(msg, "type", "")
            if t in ("note_on", "note_off"):
                ch = (getattr(msg, "channel", 0) or 0) + 1
                n = getattr(msg, "note", None)
                v = getattr(msg, "velocity", None)
                if n is not None:
                    print(f"{t} ch:{ch} note:{int(n)} vel:{int(v) if v is not None else 0}")
        try:
            port = mido.open_input(sel, callback=mon_cb)
        except Exception as e:
            print(f"open failed: {e}")
            return
        print("monitoring... Ctrl+C to exit")
        try:
            while True:
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("exit")
        finally:
            try:
                port.close()
            except Exception:
                pass
        return
    logger.info(f"Selected device: {sel}")

    mapping = Mapping(cfg["notes"])
    mapper = MidiMapper(mapping, cfg["mode"], int(cfg["tap_ms"]), int(cfg["velocity_threshold"]), cfg["channel"], logger, False, False, backend, log_mode)

    def callback(msg):
        mapper.handle(msg)

    try:
        port = mido.open_input(sel, callback=callback)
    except Exception as e:
        logger.error(f"Failed to open device: {e}")
        return

    logger.info("Listening... press Ctrl+C to exit")
    try:
        period = 5.0
        while True:
            time.sleep(period if period > 0 else 0.5)
            if period > 0:
                logger.info(mapper.stats_line())
    except KeyboardInterrupt:
        logger.info("Exiting")
    finally:
        try:
            port.close()
        except Exception:
            pass
        try:
            listener = getattr(logger, "_listener", None)
            if listener:
                listener.stop()
        except Exception:
            pass

if __name__ == "__main__":
    main()

