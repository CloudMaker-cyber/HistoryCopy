# 技术方案 (Technical Specification)

> 文档版本:v1.0
> 更新日期:2026-08-02

## 1. 技术选型

| 层面 | 技术 | 理由 |
|---|---|---|
| 语言 | Python 3.11+ | 代码简单、易维护、打包方便,适合本项目 |
| 图形界面 | PySide6 (Qt 6) | 支持卡片列表、托盘图标、无边框窗口、自定义主题(淡蓝色) |
| 数据存储 | SQLite (内置 sqlite3) | 轻量、无需额外安装、单个文件易备份 |
| 剪贴板监听 | Windows API `AddClipboardFormatListener` (ctypes) | 系统级事件监听,实时、低占用、不干扰用户 |
| 剪贴板读写 | 文字用 Windows 剪贴板 API;图片用 Pillow | 稳定兼容 |
| 图片处理 | Pillow | 剪贴板图片读取与保存 |
| 图像文字识别 | rapidocr(ONNX 推理)+ onnxruntime,CPU 离线 | 本地识别中英文,数据不出电脑;打包体积增量约 +80MB |
| 打包 | PyInstaller | 打包成单目录 exe,双击即用 |

## 2. 项目结构

```
HistoryCopy/
├── CLAUDE.md                  # 开发工作指引
├── docs/                      # 开发文档
│   ├── requirements.md        # 需求文档
│   ├── tech-spec.md           # 技术方案
│   ├── design-spec.md         # 界面设计规范
│   └── dev-plan.md            # 开发计划/执行步骤
├── devlog/                    # 开发日志(每日)
├── run.bat                    # 双击启动脚本
├── src/                       # 源码
│   ├── main.py                # 程序入口
│   ├── app.py                 # 应用主控(托盘、窗口调度、单实例、清理调度)
│   ├── recorder.py            # 剪贴板记录器(快照去重 + 通知界面)
│   ├── clipboard_monitor.py   # 剪贴板监听模块(Windows API)
│   ├── storage.py             # 数据存取模块(SQLite + 图片文件)
│   ├── cleanup.py             # 保留期限清理模块
│   ├── autostart.py           # 开机自启模块(注册表)
│   ├── ocr.py                 # 图像文字识别模块(RapidOCR,懒加载)
│   ├── settings.py            # 设置存储模块(JSON)
│   └── ui/
│       ├── main_window.py     # 主窗口
│       ├── card.py            # 历史卡片组件
│       ├── theme.py           # 淡蓝色主题
│       ├── icon.py            # 程序内绘制图标
│       ├── preview.py         # 图片大图预览对话框
│       └── settings_dialog.py # 设置对话框
├── data/                      # 运行时数据(自动生成)
│   ├── history.db             # 文字记录 SQLite 数据库
│   ├── settings.json          # 用户设置
│   └── images/                # 图片文件
├── build/                     # 打包输出
└── requirements.txt           # 依赖清单
```

## 3. 数据设计

### 3.1 SQLite 表 `clip_items`

| 字段 | 类型 | 说明 |
|---|---|---|
| id | INTEGER PRIMARY KEY | 主键 |
| content_type | TEXT | 'text' / 'image' |
| content | TEXT | 文字内容(图片时为空) |
| image_path | TEXT | 图片文件相对路径 |
| ocr_text | TEXT | 图片识别出的文字(图片未识别时为空) |
| fingerprint | TEXT | 内容 MD5 指纹(去重依据) |
| created_at | TEXT | 首次创建时间(ISO 格式) |
| updated_at | TEXT | 最后复制时间(排序依据) |
| is_pinned | INTEGER | 0/1 是否置顶 |
| pinned_at | TEXT | 置顶时间(置顶区内排序) |

### 3.2 索引

- `updated_at` 索引:时间倒序查询
- `(content_type, fingerprint)` 索引:去重查找加速

### 3.3 图片存储

- 图片保存到 `data/images/` 目录,文件名 `img_<时间戳>.png`
- 数据库仅存相对路径

## 4. 关键机制设计

### 4.1 剪贴板监听

- 通过 Windows `AddClipboardFormatListener` 注册窗口消息监听
- 收到剪贴板变化消息后,读取文字(CF_UNICODETEXT)与图片(Bitmap)
- 去重:与最近一条记录比较,相同则更新 `updated_at` 不新增

### 4.2 保留期限清理

- 每日(或软件启动时)执行一次清理
- 删除条件:`is_pinned = 0` 且 `updated_at` 距今超过保留天数
- 置顶内容在取消置顶后按最后更新时间重新判定是否清理
- 清理同时删除对应图片文件

### 4.3 开机自启

- 写入注册表 `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`
- 值指向启动命令行;开发态为 `python src/main.py`,打包后为 exe 路径
- 默认关闭,由用户在设置界面勾选开启/关闭

### 4.4 托盘与窗口

- 托盘图标:程序内绘制(蓝色剪贴板);左键单击切换窗口显示/隐藏;右键菜单(打开历史/设置/退出)
- 主窗口:无边框悬浮窗,点击卡片复制后自动隐藏
- 单实例:命名互斥量防止重复启动
- 设置:`data/settings.json` 保存保留天数与开机自启开关

### 4.5 清理调度

- 启动时执行一次清理,并每 24 小时执行一次
- 条件:未置顶且最后更新时间早于保留期限;置顶记录取消置顶后按更新时间重新判定

### 4.6 图像文字识别(OCR)

- 采用 `rapidocr`(RapidOCR,基于 ONNX Runtime)+ `onnxruntime` CPU 推理,完全离线,数据不出电脑
- **懒加载**:RapidOCR 引擎首次需要识别时才初始化(首次加载模型需 1~2 秒),避免程序启动变慢
- **手动触发**:仅在用户点击图片卡片上"识别文字"按钮时才执行;一次同一时间只识别一张,用独立线程执行避免卡界面
- **结果缓存**:识别结果写入 `clip_items.ocr_text`,同一图片再次点击直接显示缓存,不重复识别
- **界面**:"识别文字"按钮位于图片卡片右下角操作区;识别中按钮显示"识别中…"不可重复点击;完成弹出结果对话框,可一键复制
- 识别能力:中英文印刷体为主;手写/模糊/严重倾斜图片可能不准(OCR 通用局限)

## 5. 依赖清单 (requirements.txt)

```
PySide6>=6.6
Pillow>=10.0
rapidocr>=2.0        # 图像文字识别(离线 ONNX)
onnxruntime>=1.17    # rapidocr 推理引擎(rapidocr>=2.0.6 起需单独安装)
pyinstaller>=6.0    # 仅打包时使用
```

## 6. 打包方案

- PyInstaller `--noconsole` 隐藏命令行窗口,打包成单文件夹
- exe 放置于 `build/` 下
- 数据目录与 exe 同级(首启自动创建)
- OCR 需在打包时包含 rapidocr 模型与配置文件(使用 `--collect-all rapidocr` 或手动添加 data)

## 7. 风险与对策

| 风险 | 对策 |
|---|---|
| 复制大图片频繁,监听占用高 | 监听事件驱动,图片读取有大小限制 |
| 杀毒软件误报 | 使用签名、说明文档引导用户信任 |
| 剪贴板被其他软件干扰 | 仅在收到系统通知时才读取 |
| 老版本 Windows 兼容 | 最低支持 Windows 10 |
