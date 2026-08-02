# HistoryCopy · 历史剪贴板

一款运行在 Windows 上的**历史剪贴板软件**。后台静默记录你复制过的文字和图片,
需要时打开窗口即可找回、再次粘贴。淡蓝色简洁界面,开箱即用。

![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB)
![PySide6](https://img.shields.io/badge/PySide6-6.x-41CD52)
![License](https://img.shields.io/badge/License-MIT-blue)
![Platform](https://img.shields.io/badge/Platform-Windows-0078D6)

## ✨ 功能特性

- **自动记录** —— 后台常驻(系统托盘),复制即记录文字与图片
- **时间倒序** —— 打开窗口按时间从新到旧排列
- **再次使用** —— 点击卡片内容自动复制回剪贴板,回到目标窗口 Ctrl+V 即可
- **置顶 / 删除** —— 常用卡片固定在最上方,单条记录随时删除
- **搜索** —— 关键词实时过滤,命中文字高亮显示
- **图片预览** —— 图片卡片可点开大图预览
- **保留期限** —— 可设 1 / 3 / 5 天,超期自动清理(置顶的不受影响)
- **开机自启** —— 可选开机自动在后台运行
- **本地存储** —— 数据保存在 exe 旁 `data/` 目录,方便备份

## 📸 界面预览

> (截图待补充)

## 🚀 快速开始

### 方式一:直接使用(推荐)

从 [Releases](https://github.com/) 页面下载 `HistoryCopy.exe`,放到任意文件夹双击即可运行。
数据会自动保存在 exe 同级的 `data/` 目录。

### 方式二:从源码运行

需要 Python 3.11+。

```bash
pip install -r requirements.txt
python src/main.py
# 或直接双击 run.bat
```

## 🔨 打包成 exe

```bash
build.bat
```

产物位于 `dist\HistoryCopy.exe`(首次启动需等待数秒解压,属正常现象)。

## 📁 目录结构

```
HistoryCopy/
├── src/               # 源码
│   ├── main.py        # 入口
│   ├── app.py         # 应用主控(托盘/窗口/自启/清理)
│   ├── clipboard_monitor.py  # 剪贴板监听(Windows API)
│   ├── storage.py     # 数据存取(SQLite + 图片文件)
│   ├── cleanup.py     # 到期清理
│   ├── autostart.py   # 开机自启
│   └── ui/            # 界面(PySide6)
├── docs/              # 需求/技术/设计/计划/使用文档
├── devlog/            # 开发日志
└── requirements.txt   # 依赖清单
```

## 📄 文档

- [使用说明](docs/usage.md)
- [需求文档](docs/requirements.md)
- [技术方案](docs/tech-spec.md)
- [界面设计规范](docs/design-spec.md)

## ⚠️ 已知说明

- 本地"图片文件"的复制(如资源管理器里选中图片 Ctrl+C)进剪贴板的是文件引用,
  软件目前记录的是"图片内容"(网页复制图片、截图等),本地图片文件记录可作为后续功能。
- PyInstaller 打包的 exe 可能被部分杀毒软件误报,选择信任即可。

## 📝 许可证

本项目基于 [MIT License](LICENSE) 开源。
