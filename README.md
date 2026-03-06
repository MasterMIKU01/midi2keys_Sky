语言/Language: [中文](#zh-cn) | [English](#en)

<a id="zh-cn"></a>
# MIDI 到键盘按键映射（Windows）

这是一个“纯交互式”的小工具：把你的 MIDI 键盘琴键事件，实时映射为计算机键盘按键。适用于在浏览器、记事本、IDE 或游戏中用 MIDI 键盘进行输入或演奏（如《SKY》光遇内的乐器场景）。

- 支持模式：press（一次触发）、tap（点击）、hold（长按）、monitor（监控）
- 交互式操作，无需命令行参数
- 低延迟注入（SendInput 优先，失败回退 keybd_event；必要时 Unicode 兜底）
- 滚动与异步日志，默认每 5 秒输出统计

## 1. 准备环境
- Windows 10/11
- MIDI 键盘（USB 或已安装驱动）
- Python 运行方式（开发调试）：

```bash
pip install mido python-rtmidi
python midi2keys.py
```

- exe 运行方式（推荐发布与使用）：
  - 将 mapping.json 放在 exe 同目录（用于自定义映射）
  - 双击或在终端运行 exe 即可进入交互流程

## 2. 交互流程（纯交互，无参数）
程序启动后，按提示依次选择：
- 语言选择：1 中文 / 2 English
- 设备选择：显示“序号 名称 | 标识”，支持“输入序号”或“输入名称子串的唯一匹配”
- 模式选择：1.press 2.tap 3.hold 4.monitor
- 注入后端：1.auto 2.sendinput 3.keybd
- 日志级别：1.DEBUG 2.INFO 3.WARNING 4.ERROR

随后会显示“程序运行中，按 Ctrl+C 退出”，开始工作。

### 模式说明
- press（一次触发）：每次 Note-On 执行一次按键点击（Down→短暂停→Up）
- tap（点击）：Note-On 执行一次点击，时长为 tap_ms（毫秒）
- hold（长按）：Note-On 按下键，Note-Off 抬起键
- monitor（监控）：终端打印 note_on/note_off（十进制 note 与 vel），不注入键盘事件

## 3. 配置文件 mapping.json
程序会自动查找 mapping.json（优先 exe 同目录，其次打包资源目录，最后源码目录）。如需定制映射，请将 mapping.json 放在 exe 同目录。

示例：

```json
{
  "tap_ms": 0,
  "velocity_threshold": 1,
  "channel": null,
  "notes": {
    "48": "Y",
    "50": "U",
    "52": "I",
    "53": "O",
    "55": "P",
    "57": "H",
    "59": "J",
    "60": "K",
    "62": "L",
    "64": ";",
    "65": "N",
    "67": "M",
    "69": ",",
    "71": ".",
    "72": "/"
  }
}
```

重要说明：
- 文件必须是“标准 JSON”（不支持 // 注释）
- 字段含义：
  - tap_ms：tap 模式点击时长（毫秒）。建议 8–15，0 可能被部分应用忽略
  - velocity_threshold：触发最小力度；设为 0 表示忽略力度
  - channel：限定 MIDI 通道（0–15）。MIDI-OX 的 CHAN 1 对应这里的 0。null 表示不限制
  - notes：音符号到键盘键的映射（键支持字母/数字；标点 ; , . /；特殊键 SPACE/ENTER/TAB/ESC/LEFT/RIGHT/UP/DOWN/BACKSPACE）
- 音符号为“十进制”。如需从 MIDI-OX 日志换算：
  - 0x30→48 (C3)，0x32→50 (D3)，0x34→52 (E3)，0x35→53 (F3)
  - 0x37→55 (G3)，0x39→57 (A3)，0x3B→59 (B3)
  - 0x3C→60 (C4)，0x3E→62 (D4)，0x40→64 (E4)，0x41→65 (F4)
  - 0x43→67 (G4)，0x45→69 (A4)，0x47→71 (B4)，0x48→72 (C5)

## 4. 打包为 exe（推荐发布）
使用 PyInstaller 打包（包含后端与默认映射）：

```bash
pip install pyinstaller mido python-rtmidi
pyinstaller -F midi2keys.py --hidden-import mido.backends.rtmidi --hidden-import rtmidi --add-data "mapping.json;."
```

提示：
- 将 mapping.json 放在 exe 同目录以覆盖默认映射
- 若出现 “ModuleNotFoundError: mido.backends.rtmidi”，请确认：
  - 已安装 python-rtmidi
  - 打包命令包含 --hidden-import mido.backends.rtmidi 与 --hidden-import rtmidi

## 5. 日志模式（Log Modes）
- debug：输出所有 MIDI 事件与按键映射，前缀为 [DEBUG midi2keys]，携带毫秒级时间戳；便于排查（控制台较为繁忙）
- info：仅输出程序启动/退出、映射表加载成功、异常等重要信息；不输出逐条事件；默认推荐
- nolog：不输出任何控制台日志，也不写文件日志；内部异常被捕获并静默（适合演出/录制时保持窗口纯净与高性能）
- 性能差异：debug > info > nolog（开销从高到低）；在 nolog 模式下，每秒 1000 条 MIDI 事件的 CPU 增量不超过约 1%

## 6. 验证与使用
- 打开前台文本框（记事本、浏览器地址栏、IDE 编辑器）
- 运行程序并完成交互
- 按下对应琴键应出现映射字符或按键行为；monitor 模式打印十进制 note/vel
- 日志每 5 秒输出统计（事件数、速率、平均延迟）

## 7. 常见问题
- 未检测到输入设备：确认 MIDI 键盘连接并安装驱动
- 映射无效或延迟不稳：尝试注入后端选择 keybd/sendinput；将 tap_ms 设为 10–15；以管理员权限运行（若目标前台为管理员）
- 字母大小写不一致：大小写受 Shift/CapsLock/输入法影响
- 标点不生效：程序已内置 ; , . / 的 VK；若布局特殊，尝试 keybd 后端

## 8. 免责声明
- 仅用于个人和开发场景。请遵守应用/平台使用条款
- 注入可能被安全软件拦截；可调整权限或切换后端

---

<a id="en"></a>
# MIDI to Keyboard Key Mapping (Windows)

This is a “pure interactive” tool that maps your MIDI keyboard notes to computer keyboard keys in real time. Works with foreground apps (browser, Notepad, IDE) and game instrument scenes (e.g., SKY).

- Modes: press (one-shot), tap (click), hold (press/release), monitor (no injection)
- Interactive flow, no command-line arguments
- Low-latency injection (SendInput first, fallback keybd_event; Unicode for single chars)
- Rotating & async logging; stats every 5 seconds

## 1. Environment
- Windows 10/11
- MIDI keyboard (USB or driver installed)
- Python run (for development):

```bash
pip install mido python-rtmidi
python midi2keys.py
```

- exe run (recommended for release):
  - Put mapping.json beside the exe (for custom mapping)
  - Launch the exe to enter the interactive flow

## 2. Interactive Flow (no CLI args)
- Language: 1 Chinese / 2 English
- Device: shows “index name | id”, select by index or unique name substring
- Mode: 1.press 2.tap 3.hold 4.monitor
- Injection backend: 1.auto 2.sendinput 3.keybd
- Log level: 1.DEBUG 2.INFO 3.WARNING 4.ERROR

Then it prints “Running... press Ctrl+C to exit” and starts working.

### Modes
- press: single tap on Note-On
- tap: tap with tap_ms duration on Note-On
- hold: Down on Note-On, Up on Note-Off
- monitor: prints note_on/note_off with decimal note/velocity; no injection

## 3. mapping.json
The program auto-locates mapping.json (exe directory → PyInstaller _MEIPASS → source directory). To customize mapping, put mapping.json next to the exe.

Example:

```json
{
  "tap_ms": 0,
  "velocity_threshold": 1,
  "channel": null,
  "notes": {
    "48": "Y",
    "50": "U",
    "52": "I",
    "53": "O",
    "55": "P",
    "57": "H",
    "59": "J",
    "60": "K",
    "62": "L",
    "64": ";",
    "65": "N",
    "67": "M",
    "69": ",",
    "71": ".",
    "72": "/"
  }
}
```

Notes:
- Strict JSON (no comments)
- Fields:
  - tap_ms: click duration in ms for tap mode (8–15 recommended; 0 may be ignored)
  - velocity_threshold: minimum velocity to trigger; set 0 to ignore velocity
  - channel: 0–15 (MIDI-OX CHAN 1 → 0); null for all channels
  - notes: decimal MIDI note number → keyboard key (letters/digits; punctuation ; , . /; specials SPACE/ENTER/TAB/ESC/LEFT/RIGHT/UP/DOWN/BACKSPACE)
- Conversions (MIDI-OX hex → decimal):
  - 0x30→48 (C3), 0x32→50 (D3), 0x34→52 (E3), 0x35→53 (F3)
  - 0x37→55 (G3), 0x39→57 (A3), 0x3B→59 (B3)
  - 0x3C→60 (C4), 0x3E→62 (D4), 0x40→64 (E4), 0x41→65 (F4)
  - 0x43→67 (G4), 0x45→69 (A4), 0x47→71 (B4), 0x48→72 (C5)

## 4. Packaging to exe
Build with PyInstaller (include backend and default mapping):

```bash
pip install pyinstaller mido python-rtmidi
pyinstaller -F midi2keys.py --hidden-import mido.backends.rtmidi --hidden-import rtmidi --add-data "mapping.json;."
```

Tips:
- Keep mapping.json beside the exe to override defaults
- For “ModuleNotFoundError: mido.backends.rtmidi”, ensure:
  - python-rtmidi installed
  - --hidden-import mido.backends.rtmidi and --hidden-import rtmidi present

## 5. Log Modes
- debug: prints every MIDI event and mapped key info with prefix [DEBUG midi2keys] and millisecond timestamps; helpful for troubleshooting (busy console)
- info: prints only important messages (start/exit, mapping loaded, errors); no per-event logs; recommended default
- nolog: no console logs, no file logs; internal exceptions are caught silently (best for performance/clean window)
- Performance: debug > info > nolog. In nolog, CPU overhead stays below ~1% at 1000 MIDI events/sec

## 6. Validate & Use
- Open a foreground text field (Notepad, browser, IDE)
- Run the program and complete the interactive steps
- Press mapped notes to see input; monitor prints decimal note/velocity
- Logs print stats every 5 seconds

## 7. FAQ
- No input devices detected: check keyboard connection/driver
- Mapping/latency issues: try keybd/sendinput backend; set tap_ms to 10–15; match privileges (Admin if target is Admin)
- Letter case unexpected: affected by Shift/CapsLock/IME
- Punctuation fails: ; , . / VK included; try keybd backend for unusual layouts

## 8. Disclaimer
- For personal and development use; follow app/platform terms
- Some security software may block injection; adjust permissions or backend

