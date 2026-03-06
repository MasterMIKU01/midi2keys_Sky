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
- 注入后端：1.auto 2.sendinput 3.keybd 4.interception（需安装 Interception 驱动）
- 日志模式：1.DEBUG 2.INFO 3.NOLOG
  - 提示：推荐选择 auto；少数应用不兼容可选 keybd；需要严格键盘行为可选 sendinput
  - 提示：推荐 INFO；演出/录制选 NOLOG；排障选 DEBUG
  - 若选择 interception：输入键盘设备索引（1–10，默认 1）
  - 若不确定索引：按回车执行“自动探测”，将记事本置前，程序会依次发送测试按键并显示探测到的索引

随后会显示“程序运行中，按 Ctrl+C 退出”，开始工作。

### 模式说明
- press（一次触发）：每次 Note-On 执行一次按键点击（Down→短暂停→Up）
- tap（点击）：Note-On 执行一次点击，时长为 tap_ms（毫秒）
- hold（长按）：Note-On 按下键，Note-Off 抬起键
- monitor（监控）：终端打印 note_on/note_off（十进制 note 与 vel），不注入键盘事件
- 限制：实测 hold 模式下同时输入超过约 8 个 MIDI 信号会出现未完全注入的情况；press 模式可支持更多并发输入
- 建议：tap_ms 设为约 15ms 以确保目标应用能稳定检测到点击

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

## 4.1 安装与风险说明（Interception 驱动）
- 适用场景：部分游戏客户端会拦截用户态注入（SendInput/keybd_event），interception 通过驱动层模拟“真实键盘”，提升兼容性
- 项目地址：https://github.com/oblitum/Interception
- 安装步骤（管理员 PowerShell）：
  - 可选：开启测试签名（部分系统需要），执行 bcdedit /set testsigning on 后重启；关闭用 bcdedit /set testsigning off
  - 运行 install-interception.exe /install 安装驱动，卸载 /uninstall
  - 下载 Release 并解压，获取 install-interception.exe 与 library\\x64\\interception.dll、library\\x86\\interception.dll
  - DLL 选择与放置：
    - 架构选择：64 位 Python/exe 用 x64 DLL；32 位 Python/exe 用 x86 DLL（架构查看：python -c "import platform; print(platform.architecture()[0])"）
    - 放置位置：推荐与 exe 同目录；或加入 PATH；或系统目录 C:\\Windows\\System32（x64）、C:\\Windows\\SysWOW64（x86）
- 使用：交互中选择注入后端 4.interception
- 未安装或驱动未就绪：自动探测不可用，程序将使用默认索引 1 或回退；请先安装驱动并重启
- 风险：
  - 可能与某些安全软件或反作弊策略冲突；请遵守游戏/平台条款
  - 需要管理员权限与重启；若驱动不可用会回退到用户态注入

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

## 文件结构说明
1. midi2keys.exe（主程序，必须置于根目录）
2. mapping.json（映射配置文件，必须置于根目录）
3. midi2keys.log（可选日志文件，缺失不影响运行但将关闭日志记录功能）
4. interception.dll（仅 interception 模式需要，建议与exe同目录）

### interception 模式使用须知
- interception 驱动及 interception.dll 仅在“注入模式失效”后作为备选方案启用；若默认模式已满足使用需求，**无需安装 interception 驱动**，也**无需放置 interception.dll 文件**。

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
- Injection backend: 1.auto 2.sendinput 3.keybd 4.interception (requires Interception driver)
- Log mode: 1.DEBUG 2.INFO 3.NOLOG
  - Tip: choose auto by default; try keybd if some apps misbehave; sendinput for strict keyboard behavior
  - Tip: INFO recommended; use NOLOG for performance/clean window; DEBUG for troubleshooting
  - If choose interception: input keyboard device index (1–10, default 1)
  - If unsure: press Enter to “auto-probe”, bring Notepad foreground; the program sends test keys and prints the detected index

Then it prints “Running... press Ctrl+C to exit” and starts working.

### Modes
- press: single tap on Note-On
- tap: tap with tap_ms duration on Note-On
- hold: Down on Note-On, Up on Note-Off
- monitor: prints note_on/note_off with decimal note/velocity; no injection
- Limitation: in hold mode, more than ~8 simultaneous MIDI inputs may not be injected reliably; press mode supports more concurrent inputs
- Recommendation: set tap_ms to ~15 ms to ensure the target app reliably detects the click

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

## 4.1 Installation & Risks (Interception driver)
- When some game clients block user-mode injection, Interception simulates “real keyboard” at driver level for better compatibility
- Project: https://github.com/oblitum/Interception
- Install steps (Administrator PowerShell):
  - Optional: enable Test Mode if required: bcdedit /set testsigning on (reboot); disable with bcdedit /set testsigning off
  - Run install-interception.exe /install to install; /uninstall to remove
  - Download the Release archive and extract install-interception.exe plus library\\x64\\interception.dll and library\\x86\\interception.dll
  - DLL selection & placement:
    - Choose architecture: 64-bit Python/exe → x64 DLL; 32-bit Python/exe → x86 DLL (check: python -c "import platform; print(platform.architecture()[0])")
    - Placement: recommended beside the exe; or add to PATH; or system dirs C:\\Windows\\System32 (x64) / C:\\Windows\\SysWOW64 (x86)
- Usage: choose injection backend 4.interception in the interactive flow
- If driver not installed or not ready: auto-probe is unavailable; the program uses default index 1 or falls back. Install the driver and reboot first
- Risks:
  - May conflict with security software or anti-cheat; respect app/platform terms
  - Requires admin privileges and reboot; if driver not available, it falls back to user-mode injection

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

## File Structure
1. midi2keys.exe (main program; must be in the root directory)
2. mapping.json (mapping config; must be in the root directory)
3. midi2keys.log (optional log file; missing does not affect running but will disable logging functionality)
4. interception.dll (only required for interception mode; recommended beside the exe)

### Interception Mode Notes
- Interception driver and interception.dll are enabled only as a fallback when default injection modes fail; if defaults meet your needs, **no Interception driver installation is needed** and **no interception.dll placement is needed**.

