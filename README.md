语言/Language: [中文](#zh-cn) | [English](#en)

<a id="zh-cn"></a>
# MIDI 到键盘按键映射程序（Windows）

借助 AI 快速实现的轻量级工具：把 MIDI 钢琴信号实时译成键盘按键，专为游戏《SKY》光遇内乐器场景演奏而设计。理论上适用于任何数量按键的类似游戏（只需在配置文件中添加按键映射）。

实测 Minilab3 键盘：press 模式短促音符响应精准，hold 模式长音延留稳定。

这个程序可以把你的 MIDI 音乐键盘（如 Minilab3）上的琴键事件，实时映射为计算机键盘按键输入。在浏览器、记事本、IDE 等前台应用中，按下对应琴键就会像敲键盘一样打字或触发快捷键。

- 支持模式：一次触发（press）、点击（tap）、长按（hold）
- 支持设备枚举与选择、映射表（mapping.json）配置、低延迟注入
- 支持日志记录（可滚动、可异步）、性能统计与可选注入后端

## 快速开始
- 安装依赖（Python 3.8+）：

```bash
pip install mido python-rtmidi
```

- 列出可用设备：

```bash
python midi2keys.py --list
```

- 运行（一次触发 press 模式）：

```bash
python midi2keys.py --mode press --device "Minilab3 MIDI 0" --log-level warning
```

- 运行（长按 hold 模式）：

```bash
python midi2keys.py --mode hold --device "Minilab3 MIDI 0" --log-level info --stats-interval 5
```

提示：device 参数支持名称“子串匹配”，输入设备名的一部分即可匹配到目标设备。

## 目录结构
- midi2keys.py：主程序（命令行工具）
- mapping.json：映射配置（音符号 → 键盘按键）
- midi2keys.log：日志文件（默认滚动保存）
- README.md：使用说明

## 配置文件 mapping.json
示例（已默认配置 15 个白键的映射顺序，从 C3 到 C5）：

```json
{
  "device": "",
  "mode": "press",
  "tap_ms": 15,
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

注意：mapping.json 为标准 JSON 格式，不支持注释（例如 //）。请不要在文件内写注释，否则配置加载会失败。

字段说明：
- device：优先匹配的设备名称子串（留空表示选第一个输入设备）
- mode：工作模式（press/tap/hold）
- tap_ms：Tap 模式下按住时长，单位毫秒；建议 8–15（支持 0，极短可能被个别应用忽略）
- velocity_threshold：Note-On 触发的力度阈值；press/hold 模式通常可设为 0 表示忽略力度
- channel：限定 MIDI 通道（0–15）。MIDI-OX 显示 CHAN 1 对应这里的 0；null 表示不限制通道
- notes：音符号到键盘键的映射，键支持：
  - 单字符字母和数字（如 "A"、"1"）
  - 常见标点：";"、","、"."、"/"
  - 特殊键："SPACE"、"ENTER"、"TAB"、"ESC"、方向键（"LEFT"、"RIGHT"、"UP"、"DOWN"）、"BACKSPACE"

音符号的获取与换算：
- 在 MIDI-OX 日志里，Data1（十六进制）即音符号。需要换算为十进制填写到 notes 里
- 常见换算示例：
  - 0x30→48 (C3)，0x32→50 (D3)，0x34→52 (E3)，0x35→53 (F3)
  - 0x37→55 (G3)，0x39→57 (A3)，0x3B→59 (B3)
  - 0x3C→60 (C4)，0x3E→62 (D4)，0x40→64 (E4)，0x41→65 (F4)
  - 0x43→67 (G4)，0x45→69 (A4)，0x47→71 (B4)，0x48→72 (C5)

## 工作模式说明
- press（一次触发）：
  - 每个音符的 Note-On 仅触发一次按键点击（Down→短暂停→Up），忽略力度；Note-Off 不触发
  - 避免重复触发：按住同一个键时不会重复注入，直到 Note-Off 到来才允许下次触发
- tap（点击）：
  - Note-On 时执行一次点击（Down→延时 tap_ms→Up）
  - 适合需要明确点击的场景
- hold（长按）：
  - Note-On → 键盘按下；Note-Off → 键盘抬起
  - 适合持续按住的场景（如快捷键保持、游戏等）

## 命令行参数详解
- --config <path>：指定配置文件（默认当前目录 mapping.json）
- --device <name>：设备名称“子串匹配”，如 "Minilab3 MIDI 0"
- --mode <press|tap|hold>：选择模式
- --tap-ms <int>：Tap 模式按住时长（毫秒），建议 8–15；支持 0
- --velocity-threshold <int>：Note-On 触发的力度阈值；设为 0 表示忽略力度
- --channel <int>：限定通道（0–15）；MIDI-OX CHAN 1 → 0
- --list：列出输入与输出设备并退出
- --verbose：打印更多调试信息（开发调试用）
- --log-level <error|warning|info|debug>：日志级别（影响控制台与文件日志）
- --per-event：打印每个事件的详细日志（默认关闭，避免 I/O 开销）
- --stats-interval <seconds>：周期打印统计信息（事件数/速率/平均延迟），默认 5 秒；设为 0 可关闭
- --async-log：启用异步日志（降低事件处理的阻塞风险）
- --no-file-log：仅输出到控制台，关闭文件日志（避免磁盘 I/O）
- --inject-backend <auto|sendinput|keybd>：
  - auto：优先 SendInput（scancode/VK），失败回退 keybd_event；必要时 Unicode 兜底（用于单字符）
  - sendinput：强制使用 SendInput（推荐通用）
  - keybd：强制使用 keybd_event（某些应用更认可）

## 验证方法
- 打开一个前台文本输入框（浏览器地址栏、记事本、IDE 编辑器）
- 运行程序后，按下对应琴键应出现映射字符（如 C3→Y）
- 日志会输出状态与统计（如平均延迟）；若失败，日志会显示错误码与描述，便于定位

## 性能与稳定性建议
- 建议使用 --log-level warning，并关闭 --per-event，打开 --async-log
- 持续输入场景可使用 --no-file-log 减少磁盘 I/O
- press/tap 的 tap_ms 建议 8–15ms；过低可能被个别应用忽略（但程序支持 0）
- hold 模式不受 tap_ms 影响，按需选择注入后端（--inject-backend）

## 常见问题
- 为什么 CHAN 1 要填 0？
  - mido 使用 0–15 表示通道；MIDI-OX 显示 CHAN 1 对应 mido 的 0
- 映射没有生效？
  - 确认 note 数字是否为十进制；确认设备选择正确；如目标应用以管理员权限运行，请以同级权限运行本程序
- 输出字符大小写不合预期？
  - 字母大小写会受 Shift 与 CapsLock 影响；如需固定大小写，可扩展为组合键（后续可加）
- 单个标点不生效？
  - 程序已内置 ; , . / 的虚拟键码；如目标布局特殊，可以尝试 --inject-backend keybd

## 设备枚举与选择
- 列出设备：

```bash
python midi2keys.py --list
```

- 指定设备（名称子串匹配）：

```bash
python midi2keys.py --mode press --device "Minilab3 MIDI 0"
```

## 发布为可执行（可选）
- 使用 PyInstaller 打包为单文件 exe（示例）：

```bash
pip install pyinstaller
pyinstaller -F midi2keys.py
```

- 打包后，将 mapping.json 与可执行放在同一目录，终端运行 exe 即可。

## 免责声明
- 本工具仅用于个人和开发场景。请勿用于违反应用使用条款或平台规则的场景。
- 注入路径可能被部分安全软件阻止；如遇阻止，请根据实际环境调整权限或后端。

## 监控模式（monitor）
- 用途：在终端中实时查看 MIDI 输入事件，输出精简信息（不含日期），且使用十进制 note 编号，便于直接填入 mapping.json
- 使用示例：

```bash
python midi2keys.py --mode monitor --device "Minilab3 MIDI 0"
```

- 终端输出示例：
  - device:Minilab3 MIDI 0
  - monitoring... Ctrl+C to exit
  - note_on ch:1 note:59 vel:97
  - note_off ch:1 note:59 vel:0
  - note_on ch:1 note:48 vel:89

说明：
- ch 为 1 起计的通道号（与 MIDI-OX 显示一致）
- note 为 MIDI 音符号（0–127，十进制），表示具体的琴键音高；Note-On 与 Note-Off 共享同一个 note 值（例如 0x3B=59=B3）。在 mapping.json 中使用十进制的 note 作为键进行映射
- vel 为力度（velocity，0–127，十进制），表示按键的力度/速度；在 monitor 输出中直接显示十进制。程序中 press 模式默认忽略力度；tap/hold 模式可通过 velocity_threshold 参数过滤过小力度。部分设备会用 Note-On 且 vel=0 来表示 Note-Off

---

<a id="en"></a>
# MIDI to Keyboard Key Mapping (Windows) — English

Lightweight tool quickly built with AI: translates MIDI piano signals into keyboard keystrokes in real time, tailored for instrument performance scenes in the game “SKY: Children of the Light”. In principle, it works for similar games with any number of keys (just add the mappings in the config file).

Tested on the Minilab3 keyboard: press mode delivers precise response for short notes, and hold mode provides stable sustain for long notes.

This tool maps your MIDI keyboard notes to computer keyboard keys in real time. It works with any foreground app (browser, Notepad, IDE, etc.), so pressing a MIDI note is like typing.

- Modes: press (one-shot), tap (click), hold (press/down + release/up)
- Device listing and selection, configurable mapping (mapping.json), low-latency injection
- Logging supports rotation and async; performance stats are available

## Quick Start
- Install dependencies (Python 3.8+):

```bash
pip install mido python-rtmidi
```

- List devices:

```bash
python midi2keys.py --list
```

- Run press mode:

```bash
python midi2keys.py --mode press --device "Minilab3 MIDI 0" --log-level warning
```

- Run hold mode:

```bash
python midi2keys.py --mode hold --device "Minilab3 MIDI 0" --log-level info --stats-interval 5
```

## mapping.json
Example (15 white keys from C3 to C5):

```json
{
  "device": "",
  "mode": "press",
  "tap_ms": 15,
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

Note: mapping.json is strict JSON. Comments (e.g., //) are not allowed; adding them will cause the configuration to fail to load.

Fields:
- device: device name substring to select (empty means first input)
- mode: press/tap/hold
- tap_ms: click duration in milliseconds for tap mode; 8–15 recommended, 0 supported
- velocity_threshold: minimum velocity to trigger Note-On; set 0 to ignore velocity
- channel: 0–15; note that MIDI-OX “CHAN 1” corresponds to 0 here; null means all channels
- notes: decimal MIDI note number → keyboard key
  - Keys: letters/digits, punctuation ; , . /, specials SPACE/ENTER/TAB/ESC/LEFT/RIGHT/UP/DOWN/BACKSPACE

Getting the note number:
- In MIDI-OX logs, Data1 is the note number (hex). Convert to decimal for mapping.json
- Common conversions:
  - 0x30→48 (C3), 0x32→50 (D3), 0x34→52 (E3), 0x35→53 (F3)
  - 0x37→55 (G3), 0x39→57 (A3), 0x3B→59 (B3)
  - 0x3C→60 (C4), 0x3E→62 (D4), 0x40→64 (E4), 0x41→65 (F4)
  - 0x43→67 (G4), 0x45→69 (A4), 0x47→71 (B4), 0x48→72 (C5)

## Modes
- press: triggers a single tap on Note-On, ignores Note-Off and velocity
- tap: performs Down → wait tap_ms → Up on Note-On
- hold: Down on Note-On, Up on Note-Off

## CLI Options
- --config <path>: mapping file (default mapping.json)
- --device <name>: device name substring (e.g., "Minilab3 MIDI 0")
- --mode <press|tap|hold|monitor>: choose mode
- --tap-ms <int>: tap duration in ms (tap mode), supports 0
- --velocity-threshold <int>: min velocity to trigger Note-On; set 0 to ignore
- --channel <int>: limit to channel (0–15); MIDI-OX CHAN 1 → 0
- --list: show devices
- --verbose: more debug logs
- --log-level <error|warning|info|debug>: logging level
- --per-event: print per-event logs (off by default)
- --stats-interval <seconds>: periodic stats (events/rate/avg latency); set 0 to disable
- --async-log: async logging via queue
- --no-file-log: console only, no file
- --inject-backend <auto|sendinput|keybd>:
  - auto: try SendInput (scancode/VK), fallback keybd_event; Unicode fallback for single chars
  - sendinput: force SendInput
  - keybd: force keybd_event

## Monitor Mode
- Purpose: print note_on/note_off in a minimal format using decimal note numbers
- Usage:

```bash
python midi2keys.py --mode monitor --device "Minilab3 MIDI 0"
```

- Output:
  - device:Minilab3 MIDI 0
  - monitoring... Ctrl+C to exit
  - note_on ch:1 note:59 vel:97
  - note_off ch:1 note:59 vel:0
 
Notes:
- ch is the channel number starting at 1 (matches MIDI-OX’s display)
- note is the MIDI note number (0–127, decimal), representing the pitch; Note-On and Note-Off share the same note value (e.g., 0x3B=59=B3). Use the decimal note number in mapping.json as the key
- vel is velocity (0–127, decimal), representing how hard/fast the key was pressed; press mode ignores velocity; tap/hold can filter low values via velocity_threshold. Some devices signal Note-Off as Note-On with velocity=0

## Performance Tips
- Use --log-level warning, disable --per-event, enable --async-log
- For heavy typing, consider --no-file-log
- 8–15ms tap_ms feels natural; 0 is supported but may be ignored by some apps

## Packaging
- Build a single-file exe via PyInstaller:

```bash
pip install pyinstaller
pyinstaller -F midi2keys.py
```

- Keep mapping.json beside the executable.

## Disclaimer
- For personal and development use. Respect app/platform terms
- Some security software may block injection; adjust permissions or backend accordingly

## Directory Structure
- midi2keys.py: main CLI program
- mapping.json: note-to-key mapping configuration
- midi2keys.log: log file (rotated)
- README.md: user guide (Chinese + English)

## Device Listing & Selection
- List devices:

```bash
python midi2keys.py --list
```

- Select device by substring:

```bash
python midi2keys.py --mode press --device "Minilab3 MIDI 0"
```

Tip: the device parameter matches by substring (you can provide part of the name).

## Validation
- Open a foreground text input (browser address bar, Notepad, IDE editor)
- Run the program, press the mapped note (e.g., C3→Y)
- The character should appear and logs will show status/average latency (if enabled); on failure, logs print error code and description

## FAQ
- Why is CHAN 1 equal to channel 0 here?
  - mido uses 0–15; MIDI-OX displays CHAN 1 which corresponds to 0 in mido
- Mapping doesn’t work?
  - Ensure note numbers are decimal; check device selection; if the target app runs as Administrator, run this program with the same elevation
- Unexpected letter case?
  - Case is affected by Shift/CapsLock/IME; if you need fixed case, consider mapping to a combo (e.g., add Shift)
- Punctuation doesn’t work?
  - The program includes ; , . / VK codes; for unusual layouts, try --inject-backend keybd

