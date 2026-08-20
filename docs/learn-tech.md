# HistoryCopy 技术学习指南

> 面向编程小白的入门读物。建议先通读第一部分建立整体认知,再按兴趣逐章深入。
> 每一章都从"它是什么、为什么这样做、怎么工作、代码示例"四个角度讲解。
> 阅读时可对照 `src/` 目录下的真实代码。

## 目录

1. [总体概览](#1-总体概览)
2. [从双击到运行:程序的启动过程](#2-从双击到运行程序的启动过程)
3. [了解你的代码:模块总览](#3-了解你的代码模块总览)
4. [细节一:剪贴板监听(最底层)](#4-细节一剪贴板监听windows)
5. [细节二:记录与去重](#5-细节二记录与去重)
6. [细节三:数据存储(SQLite + 图片文件)](#6-细节三数据存储sqlite--图片文件)
7. [细节四:设置持久化(JSON)](#7-细节四设置持久化json)
8. [细节五:图形界面(PySide6/Qt)](#8-细节五图形界面pyside6qt)
9. [细节六:托盘与后台常驻](#9-细节六托盘与后台常驻)
10. [细节七:图片文字识别(OCR)](#10-细节七图片文字识别ocr)
11. [细节八:自动清理与开机自启](#11-细节八自动清理与开机自启)
12. [细节九:多线程:界面为什么不会卡](#12-细节九多线程界面为什么不会卡)
13. [细节十:打包成 exe(PyInstaller)](#13-细节十打包成-exepyinstaller)
14. [自学建议与动手练习](#14-自学建议与动手练习)

## 1. 总体概览

### 1.1 这个程序是做什么的?

**HistoryCopy = 历史剪贴板**。它是一个 Windows 桌面小工具:

- 你平时复制(Ctrl+C)文字或图片 → 它在后台默默记下来;
- 之后想找回某次复制过的内容 → 打开它,点一下卡片就写回剪贴板,再 Ctrl+V 粘贴即可。

关键词:**后台常驻**、**自动记录**、**随时找回**。

### 1.2 最核心的三个动作

| 动作 | 谁来做 | 对应模块 |
|---|---|---|
| 记录 | 系统通知"剪贴板变了" | `clipboard_monitor.py` + `recorder.py` |
| 保存 | 文字写进数据库、图片存成文件 | `storage.py` |
| 找回 | 窗口里看到卡片,点击复制 | `ui/` 目录 |

### 1.3 一张总图(先记住这张图,再往下看)

```
                 ┌───────────────────────────────────────────────┐
 你在任何软件里   │                HistoryCopy                    │
 按 Ctrl+C        │                                               │
   │              │   剪贴板监听(后台线程)      保存             │
   ▼              │   ClipboardMonitor ──► Recorde r ──► Storage │
 ┌────────┐       │        │ 事件通知               (SQLite 文件) │
 │ Windows │       │        ▼                                       │
 │ 剪贴板  │       │    Qt 信号 ──► 主窗口 MainWindow             │
 └────────┘       │       (界面刷新 / 搜索 / 删除 / OCR)          │
                 │            │                                 │
                 │   需要时右键托盘 ──► 打开窗口 ──► 点卡片 ──► 写回剪贴板 │
                 └───────────────────────────────────────────────┘
```

简单说:**后台一直"看着"剪贴板,变了就存;你需要时打开窗口找你存的东西。**

### 1.4 技术栈速览(每项后面都会细讲)

| 技术 | 用在哪 | 一句话 |
|---|---|---|
| Python 3.11+ | 全部代码 | 编程语言 |
| PySide6 (Qt6) | 界面 | 做窗口 / 按钮 / 列表的图形库 |
| sqlite3(内置) | 存储 | 把文字记录放在一个轻量数据库文件里 |
| 图片文件+相对路径 | 存储 | 图片太大不进数据库,单独存文件、数据库记路径 |
| ctypes(内置) | 系统调用 | 直接调用 Windows 剪贴板 API |
| winreg(内置) | 系统调用 | 读写注册表(开机自启) |
| rapidocr + onnxruntime | OCR | 离线识别图片里的文字 |
| Pillow (PIL) | 图片 | 读取/转换/保存剪贴板图片 |
| PyInstaller | 打包 | 把 Python 程序变成双击就能跑的 exe |

> 听到"API""库""框架"不用怕,它们就是"别人写好的现成功能,你按说明调用"。

### 1.5 程序跑起来长什么样

- 启动后不在任务栏显示窗口,而是缩到系统托盘(右下角小图标);
- 你复制东西,它悄悄记录;要查看时右键托盘图标 → 打开窗口;
- 窗口是"悬浮卡"风格,可拖动、可搜索、可置顶、可删除、可批量删除、图片可识别文字。

## 2. 从双击到运行:程序的启动流程

### 2.1 入口文件:`src/main.py`

```python
from app import run

if __name__ == "__main__":
    run()
```

- `if __name__ == "__main__"` 是 Python 的"入口判断"套路:只有**直接运行这个文件**时才执行,被别人 `import` 时跳过;
- 真正的启动从头到尾都在 `app.py` 的 `run()` 里。

### 2.2 组装大师:`app.py` 的 `run()`

`run()` 按顺序做这几件事(先感受"顺序感"):

```python
app = QApplication(sys.argv)         # 1. 创建 Qt 应用本体(Qt 一切开始的地方)
app.setStyleSheet(stylesheet())      # 2. 套上淡蓝色主题样式
if _already_running():               # 3. 防止开两个实例(单实例)
    return
storage = Storage()                  # 4. 打开数据库,连上表
settings = Settings()                # 5. 读取设置(保留天数等)
notifier = _Notifier()               # 6. 跨线程"通知器"(后面细说)
recorder = ClipboardRecorder(storage, on_recorded=...)
monitor = ClipboardMonitor(on_change=recorder.handle_change)  # 7. 监听剪贴板
monitor.start()                      #    (新线程里开始监听)
window = MainWindow(storage)          # 8. 建主窗口(先不显示)
controller = _Controller(...)         # 9. 托盘图标 + 菜单 + 定时清理
window.hide()                          # 10. 默认不显示窗口
app.exec()                             # 11. 进入事件循环(程序真正"活着")
```

**事件循环(Qt 的命根子)**:`app.exec()` 之后,程序进入一个死循环,不断守候"事件"——鼠标点击、按键、剪贴板变化、定时器到期……**每来一个事件**,就执行挂在这个事件上的处理函数。所有界面交互都靠它。就像餐厅服务员:不主动做饭,但一直站着等人叫。

### 2.3 一句话记住启动流程

> 先造好所有"零件"(数据库、监听器、窗口、托盘),把它们接线接好,最后进入事件循环等待用户动手。平时它就在托盘里安静待着。

## 3. 了解你的代码:模块总览

一张表看清每个文件干什么:

| 文件 | 分类 | 说明 |
|---|---|---|
| `src/main.py` | 入口 | 调用 `app.run()` |
| `src/app.py` | 主控 | 组装一切 + 托盘 + 定时清理 + 单实例 |
| `src/clipboard_monitor.py` | 底层监听 | 调用 Windows API 监听剪贴板、读写剪贴板 |
| `src/recorder.py` | 逻辑 | 剪贴板变化 → 去重 → 交给 Storage |
| `src/storage.py` | 数据 | SQLite 增删改查 + 图片文件管理 |
| `src/settings.py` | 数据 | 读取 / 保存设置(JSON) |
| `src/cleanup.py` | 维护 | 定期删除过期记录 |
| `src/autostart.py` | 系统 | 注册表"开机自启" |
| `src/ocr.py` | 功能 | 封装 OCR 图片文字识别 |
| `src/utils.py` | 工具 | 路径 / 时间 / MD5 / 错误日志 |
| `src/ui/main_window.py` | 界面 | 主窗口(搜索框 / 卡片列表 / 底部工具条) |
| `src/ui/card.py` | 界面 | 单张历史卡片组件 |
| `src/ui/theme.py` | 界面 | 全局配色与样式(QSS) |
| `src/ui/icon.py` | 界面 | 程序内绘制图标 |
| `src/ui/preview.py` | 界面 | 图片大图预览窗口 |
| `src/ui/ocr_dialog.py` | 界面 | OCR 结果展示窗口 |
| `src/ui/settings_dialog.py` | 界面 | 设置窗口 |
| `src/self_test.py` | 开发 | 自动化自检脚本 |

读代码时的"由浅入深"顺序建议:main → app → settings → storage → recorder → cleanup/autostart → ui/main_window → ui/card → clipboard_monitor → ocr → self_test。

## 4. 细节一:剪贴板监听(Windows)

### 4.1 为什么需要"监听"?

剪贴板是系统级的,任何软件都能改。想让"每次复制都记录",就得让**系统告诉我"剪贴板变了"**。

做法 A(笨办法):**轮询**——每几百毫秒扫一眼剪贴板有没有变化。缺点是:无谓地消耗 CPU,而且时机总差一点点。

做法 B(聪明办法):**事件回调**——系统主动通知你。本项目用这个。

### 4.2 关键 API:`AddClipboardFormatListener`

Windows 提供 `AddClipboardFormatListener` 这个 API,给自己的隐藏窗口"订阅"剪贴板变化事件。之后用户在任意软件里 Ctrl+C 或 Cut,Windows 就给这个窗口发一条 `WM_CLIPBOARDUPDATE` 消息。

**难点**:Python 本身不会讲这些底层 Windows API,所以要借用 `ctypes` 手动声明并调用。

### 4.3 读剪贴板文字的全过程

`s_clipboard_monitor.py` 里大量这种"手写 API"。以读取剪贴板文字为例:

```python
user32.OpenClipboard(None)              # 打开剪贴板(申请独占访问)
handle = user32.GetClipboardData(13)    # 13 = CF_UNICODETEXT,拿文字数据的内存句柄
ptr = kernel32.GlobalLock(handle)        # 锁定内存,拿到可读指针
text = ctypes.wstring_at(ptr)            # 从指针读出 Unicode 字符串
kernel32.GlobalUnlock(handle)            # 解锁
user32.CloseClipboard()                  # 关闭剪贴板
```

要点:必须"开门 → 取数据 → 关",中途任何一步失败就返回 `None`。

### 4.4 后台监听是怎么"挂"起来的

`ClipboardMonitor` 在 `start()` 里创建一个隐藏窗口(消息窗口),注册监听,然后在**新线程**里跑 `GetMessageW` 循环。`GetMessageW` 跟事件循环一样:死等新消息。剪贴板一变 → 收到 `WM_CLIPBOARDUPDATE` → 调用处理函数 `on_change`。

为什么用独立线程?因为 GUI 的事件循环很忙,剪贴板又是全局的,把它隔离到自己的工作线程更干净、更稳(本线程循环专用,不与界面争抢)。

### 4.5 剪贴板读写分工

- **读**:`get_clipboard_text()`、`get_clipboard_image()`(CF_DIB 位图格式)
- **写**:`set_clipboard_text()`、`set_clipboard_image()`(点卡片"复制"时用)

### 4.6 你可能踩的坑

- **内存处理**:不按 `GlobalLock/GlobalUnlock` 配对会把内存搞崩;
- **图片格式**:从剪贴板拿到的 DIB 位图数据先交给 Pillow 解码:

```python
from PIL import Image
img = Image.open(io.BytesIO(raw))
img.load()   # 一定要 load,真正把像素读进来
```

## 5. 细节二:记录与去重

### 5.1 记录流程(`recorder.py`)

剪贴板一变,`ClipboardRecorder.handle_change()` 执行:

```python
text = get_clipboard_text()
image = get_clipboard_image()
if text is not None:
    self._storage.add_text(text)
elif image is not None:
    self._storage.add_image(image)
```

### 5.2 去重(MD5 指纹)——为什么重要

如果不做任何处理,你连着复制同一句话,历史里会冒出一堆重复。去重思路:

1. 给内容算个**指纹**(MD5 摘要):相同内容 → 完全相同指纹;
2. 记录器记住"上一次看到的内容指纹";
3. 指纹一样 → 认为"内容没变" → **不新增**,只顺手更新时间;变了 → 新增。

```python
fp = md5_of(text)
if fp != self._last_text_fp:
    self._last_text_fp = fp
    self._storage.add_text(text)
```

`add_text` / `add_image` 内部还会用 `fingerprint` 字段做第二道保险,在数据库层再查一次同指纹的记录(见第 6 节)。

### 5.3 去重不了的小情况

**同一张截图**:有些软件的截图每次字节都不一样(MD5 就不同),这是已知小坑,demo 从简即可,不展开。

### 5.4 通知界面刷新

每次新增/更新后调用 `self._on_data()` —— 它是 `app.py` 里传入的 `notifier.changed.emit`,最终让 `main_window.schedule_refresh()` 重新从数据库拉一次列表。这就是"复制后列表自动出现新内容"的原因。

## 6. 细节三:数据存储(SQLite + 图片文件)

### 6.1 为什么要分成"数据库 + 文件"两套

- **文字**量小、适合搜索 → 直接存进 SQLite;
- **图片**是二进制大对象(BLOB),塞进数据库会让数据库变得又大又慢(session并发),更标准做法是**单独存文件**,数据库里只存一个"相对路径"。

> SQLite 是"一个文件就当作一个数据库"的轻量数据库,Python 的 `sqlite3` 内置就能操作,不需要额外装服务。

### 6.2 表结构(核心表 `clip_items`)

| 字段 | 说明 |
|---|---|
| `id` | 主键,每条记录唯一编号 |
| `content_type` | `'text'` 或 `'image'` |
| `content` | 文字内容(图片记录为空) |
| `image_path` | 图片的**相对路径**(文字记录为空) |
| `ocr_text` | 图片识别出的文字(留空表示未识别) |
| `fingerprint` | 内容指纹(MD5),用来去重 |
| `created_at` / `updated_at` | 首次创建时间 / 最后一次复制时间 |
| `is_pinned` / `pinned_at` | 是否置顶 / 置顶时间 |

### 6.3 建表与"自动升级"(迁移)

```python
CREATE TABLE IF NOT EXISTS clip_items ...
# 然后检查某些在新版本才有的列:
cols = {r[1] for r in conn.execute("PRAGMA table_info(clip_items)")}
if "ocr_text" not in cols:
    conn.execute("ALTER TABLE clip_items ADD COLUMN ocr_text TEXT")
```

这样老用户升级到新版本时,程序会自动补上缺失的列,不会崩。`PRAGMA table_info` 能列出表里所有列名。

### 6.4 图片文件怎么存取

```python
fname = f"img_{时间戳}.png"
with open(os.path.join(images_dir(), fname), "wb") as f:
    f.write(图片字节)
# 数据库里只存 fname 这个相对路径
```

好处:**备份整个 `data/` 文件夹 = 备份全部**(数据 + 图片 + 设置);但代价是——**删除记录时一定要记得连带删图片文件**。`delete` / `delete_many` / `clear_all` 都做了这一步,否则磁盘里会留一堆孤儿文件。

### 6.5 线程安全:为什么要有锁

`Storage` 用一个数据库连接 + `self._lock = threading.Lock()`,所有写操作都 `with self._lock:` 包住。原因是**后台监听线程(记录)和界面线程(浏览)可能同时访问数据库**,SQLite 同时多线程写会报"database is locked"。锁的作用是"同一时刻只有一个人进数据库"。

### 6.6 常用方法一览

- `add_text` / `add_image`(去重写入)
- `list_sorted(limit)`(置顶优先 + 时间倒序)
- `get(item_id)`(取单条)
- `set_pinned` / `delete` / `delete_many` / `clear_all`
- `set_ocr_text` / `get_ocr_text`(OCR 结果缓存,识别过一次就不再识别)

## 7. 细节四:设置持久化(JSON)

`src/settings.py` 用 **JSON 文件**保存设置,启动时读、改动即写过:

```python
class Settings:
    def __init__(self, path=None):
        self._data = dict(DEFAULTS)
        self._load()

    def get(self, key, default=None):
        return self._data.get(key, default)

    def set(self, key, value):
        self._data[key] = value
        self._save()
```

默认值大概是:`{"retention_days": 3, "autostart_enabled": False}`(保留 3 天、不自启)。JSON 就是纯文本,人类能直接看懂,适合存少量零散配置。

## 8. 细节五:图形界面(PySide6 / Qt)

### 8.1 三个概念:控件、布局、信号槽

- **控件(Widget)**:界面上的一块"积木"——按钮(`QPushButton`)、文本标签(`QLabel`)、输入框(`QLineEdit`)……
- **布局(Layout)**:安排控件位置的容器,`QVBoxLayout` 竖排、`QHBoxLayout` 横排,窗口缩放时自动重排;
- **信号槽(Signal / Slot)**:Qt 通讯靠它的核心。按钮被点→发 `clicked` 信号;你用 `connect()` 把它接给一个函数:

```python
btn = QPushButton("复制")
btn.clicked.connect(self.copy_content)   # 点一下 → 自动调用 copy_content()
```

### 8.2 主题:`theme.py`(QSS 样式表)

Qt 支持类似网页 CSS 的 **QSS**,统一控件的外观:

```css
QFrame { background: #FFFFFF; border-radius: 8px; }
QPushButton#primary { background: #7BD3FF; color: #333; }
```

只要在程序启动时 `app.setStyleSheet(stylesheet())` 一次,全部控件自动换上这套皮肤。**所以,想改外观,主要改 `ui/theme.py` 就好。**

### 8.3 主窗口 `main_window.py`:无边框 + 可拖动

- 用 `Qt.FramelessWindowHint` 去掉系统标题栏,更轻量、更专注;
- 需要自制拖动:在标题区域抓鼠标按下(`mousePressEvent`)记录偏移,然后在 `mouseMoveEvent` 里 `self.move(全局坐标 - 偏移)` 实现;
- 默认隐藏,只有托盘图标被点击时才 `show()`(平常不打扰用户)。

### 8.4 卡片组件 `card.py`

每一条历史是一张 `HistoryCard`(继承 `QFrame`),大概长这样:

```
┌────────────────────────────────┐
│ 📌 置顶(可选)                  │
│ 文字预览 / 图片缩略图           │
│ 今天 20:31   复制  识别  置顶 │
│              预览  删除        │   ← 按钮行(QHBoxLayout)
└────────────────────────────────┘
```

- **信号**:卡片把"点了删除""点了复制"通过 Qt 信号发出,主窗口负责接;这样卡片只专心画自己,逻辑决策在主窗口,分工清晰;
- **多选模式**:开启后卡片显示勾选框、隐藏操作按钮;点卡片切换选中,通过 `selection_toggled` 信号上报给主窗口做批量操作;
- **渲染性能**:列表刷新是"清空旧卡片、重建新卡片"。为防用户在搜索框连续打字导致疯狂重建,用了 `QTimer` 的**防抖**(比如 200ms 内不重复刷新);还保存/恢复滚动位置。

> 曾两次出现"卡片被撑破":第一次是**超长网址**塞满一行,给长 Token 插**零宽断行符**并限制图片缩略最大宽度;第二次是**不换行空格**——网页/Office 复制的文字常含它,Qt 不会在它那里折行,结果整段变成一个超长"单词"把卡片撑到 1000px 以上。处理办法:不换行空格也按普通字符计长补断行符,**并给列表容器加了"宽度上限"约束(SetNoConstraint)**,从此任何内容都不可能再把卡片撑宽(极端长内容只会在卡片里截断,悬停可看全文)。教训:**改 UI 布局时永远要预留宽度预算,而且长内容必须同时有"断行方案 + 宽度兜底"两道保险**。

### 8.5 其他界面

- `preview.py`:大图预览对话框;
- `ocr_dialog.py`:OCR 识别结果展示与复制;
- `settings_dialog.py`:设置窗口(保留天数 / 自启开关 / 清空历史);
- `icon.py`:不需要版权图库,用 `QPainter` 现画一个图标。

## 9. 细节六:托盘与后台常驻

### 9.1 什么是托盘

系统右下角时钟附近那排小图标就是"系统托盘"。程序退到托盘 → 窗口隐藏但进程还活着,继续监听剪贴板。

### 9.2 `app.py` 里 `_Controller` 托盘菜单

- `QSystemTrayIcon` 显示图标 + 冒泡提示;
- 右键小菜单:`打开主窗口 / 立即清理 / 退出`;  (以代码为准)
- 窗口关闭按钮的行为定为"隐藏到托盘"而不是退出(用户更容易不打扰地退回后台)。

### 9.3 定时清理的来历

`_Controller` 里放一个 `QTimer`,每天大约在某个时刻调用一次 `cleanup.run(storage, settings)`(见第 11 节)。

### 9.4 单实例(只允许开一个)

Windows 提供全局"互斥体(Mutex)"对象。启动时用 `OpenMutexW` 查一下——如果名字相同的互斥体已存在,说明第二个实例已在运行,`ShowWindow` 把它的窗口调到前台,然后退出;没有则用 `CreateMutexW` 建一个(程序退出时释放)。这样保证不会出现两份程序互相刷屏。

## 10. 细节七:图片文字识别(OCR)

### 10.1 OCR 是什么

OCR(Optical Character Recognition,光学字符识别):给一张图片,把里面印刷/手写的文字提取成字符串。本项目用 `rapidocr`,由 onnxruntime 在 **本机 CPU** 离线跑——不联网也不上传图片,隐私友好。

### 10.2 用户触发,不自动扫全部

识别很耗 CPU(好几十毫秒 ~ 上百毫秒),所以**只有用户点了那张图卡片上的"识别"按钮才执行**。识别结果存进 `ocr_text` 列,下次直接读出来,不重复识别。

### 10.3 识别流程

```python
# ocr.py 里类似:
engine = RapidOCR()
result, _ = engine(img)
text = "\n".join(line[1] for line in result if line[1])
storage.set_ocr_text(item_id, text)
```

### 10.4 后台线程运行识别

因为识别较慢,`card.py` 的"识别"按钮启动一个 `QThread`(`_OcrWorker`),识别完成后通过 Qt 信号把结果传回主线程刷新界面,避免点击后界面卡住。

## 11. 细节八:自动清理与开机自启

### 11.1 自动清理(`cleanup.py`)

设置里"保留几天(1/3/5 天)"决定历史存活期。`cleanup.run()`:

1. 从设置读 `retention_days`;
2. 计算"截止时间 = now - retention_days";
3. 让 `storage` 查出所有 `updated_at < 截止时间`(且未置顶)的记录;
4. 一条条把记录 + 图片文件一起删掉。

### 11.2 开机自启(`autostart.py`)

Windows 开机自启最常做法:**写注册表** `HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run` 的 Run 键:

```python
key = winreg.OpenKey(HKEY_CURRENT_USER, Run路径, 0, KEY_SET_VALUE)
winreg.SetValueEx(key, "HistoryCopy", 0, REG_SZ, exe路径)
```

- 用 HKCU(当前用户)而非 HKLM,这样**无需管理员权限**,只影响自己;
- 关闭自启时删同名键。

> ⚠ 注册表是 Windows 脆弱区,本项目遵循"仅配置当前用户的 Run 键、可在设置里随时关闭且可恢复",并且你(用户)如果没自信做这类操作前要先告诉我。

## 12. 细节九:多线程与"界面为什么不会卡"

### 12.1 三条线程

1. **主线程**(Qt 事件循环):画界面、处理点击;
2. **剪贴板监听线程**:收 Windows 消息,随时上报;
3. **OCR 工作线程**(按需):识别图片文字。

### 12.2 线程怎么"对话"

- 跨线程**不能**直接改 UI(Qt 会警告/崩溃)。所以用 Qt 的**信号跨线程投递**：后台线程 `emit` 一个信号,Qt 把信号事件安全地送到主线程执行;
- 本项目主程序 `app.py` 里再包装一层 `_Notifier`,让"监听线程 → 信号 → 主线程刷界面"这一连接清晰可见。

> 一句话：**后台干活、前台展示,中间用信号排队**,这样不管录多少东西拖动界面都不会卡。

## 13. 细节十:打包成 exe(PyInstaller)

### 13.1 为什么需要 PyInstaller

用户没装 Python。打包就是把 Python 程序 + 它用到的库 + 资源整合成一个 `.exe`,双击就运行。工具:`PyInstaller`。

### 13.2 项目用 `.spec` 文件定制打包

`HistoryCopy.spec` 干三件比较关键的定制:

1. **收集 OCR 模型文件**:rapidocr 的模型 + `config.yaml` 默认在包的位置之外,写在 `datas` 里,让它们打进 exe 同目录的 `_internal` 文件夹下;
2. **隐藏导入**:PyInstaller 有时漏掉某些自动 `import`,用 `hiddenimports` 保险补;`pkg_resources` / `onnxruntime` 等常被这样处理;
3. **单文件 or 目录**:本项目用"目录模式"(one-dir)而非单文件,启动更快、模型加载更干净。

打包命令(项目根目录):

```
python -m PyInstaller HistoryCopy.spec
```

最后把 `dist/HistoryCopy/` 整个文件夹发给用户即可;程序运行时在 exe 旁边的 `data/` 里自创新建数据。

## 14. 学习建议与动手练习

### 14.1 学习路线

| 阶段 | 目标 | 建议做法 |
|---|---|---|
| 1.打地基 | 看懂 Python 基础(变量/函数/类/装饰器/回调) | 同类型的线上题做几十个 |
| 2. 看懂图 | 把第一部分(总体)和模块表讲给朋友听 | 讲不出来的章节回去再读 |
| 3. 读主流程 | 从 `app.py` 的 `run()` 一行行追出来 | 画 `run()` 的调用树 |
| 4. 单模块精读 | 按「storage → recorder → settings → cleanup → autostart → clipboard」读 | 给每个文件写 3 句话总结 |
| 5. UI 上手 | 试 `PySide6` 官方教程里的小例子(widgets + 信号槽) | 弄个能点的按钮加输入框 |
| 6. 改点真活 | 改项目真实小功能(换个主题色 / 加个菜单项 / 改保留天数默认值) | 每改一次跑一次 `self_test` 与手工测 |
| 7. 上难度 | 剪贴板监听、线程、ctypes、打包 | 遇到问题先查官方文档再在网上搜 |

### 14.2 推荐的动手小练习(由易到难)

1. 把 `src/ui/theme.py` 里的主题色改一种,看界面变化;
2. 给托盘菜单加一项"打开数据文件夹";
3. 给 `cliplboard_monitor` 加一个只读、不阻塞的调试 log——观察"一次 Ctrl+C 会触发几次事件"(你会发现在某些软件里有"潜伏触发");
4. 看 `storage.add_text` 里同一指纹刷新 `updated_at` 的分支,想想要是需求把去重分成"完全不去重"该改哪里;
5. 用 `src/self_test.py` 跑自动化自检,并在 `tests/` 里补充正则 `断言`;(以实际代码为准)

### 14.3 保持代码卫生

- 每次改完跑 `python -m compileall src` 保证语法;
- 复杂改动后运行 `python src/self_test.py`(如果存在)做自检;
- 记录到 `devlog/` 当天日记;改需求先改 `docs/requirements.md`。

### 14.4 当心这几点

- Qt 对象只能在主线程创建操作(不在线程里 new 控件);
- 改注册表/常驻/自启的功能会影响用户机器,出问题要能立刻关闭;
- 图片删除、表格迁移、跨线程信号这四处最容易出 bug,改完必须手动验证。

祝你学习愉快,造自己的工具!