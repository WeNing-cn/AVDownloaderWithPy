# AVDownloader Android 移动端

## 📱 项目简介

这是 AVDownloader 视频下载工具的 Android 移动端版本，使用 Python + Kivy 框架开发。

### 功能特性

- ✅ **M3U8 视频流下载** - 支持 HLS 流媒体下载
- ✅ **TS 分片合并** - 自动下载并合并 TS 分片
- ✅ **加密视频支持** - 支持 AES-128 加密视频解密
- ✅ **批量下载** - 支持多个 URL 批量下载
- ✅ **断点续传** - 支持下载中断后恢复
- ✅ **实时进度** - 显示下载进度和速度
- ✅ **日志记录** - 详细的下载日志

## 📁 文件结构

```
mobile/
├── main.py                     # 主程序入口（Kivy UI）
├── video_downloader_mobile.py  # 视频下载模块
├── ts_merger_mobile.py         # TS合并模块
├── buildozer.spec              # Buildozer 打包配置
├── requirements.txt            # Python 依赖
├── build_apk_windows.py        # Windows 打包工具
├── build_linux.sh              # Linux/Mac 构建脚本
└── README.md                   # 本说明文件
```

## 🔧 打包方法

由于 Buildozer 在 Windows 上有一些限制，提供以下几种打包方案：

### 方案一：使用 WSL2（推荐）

1. **安装 WSL2**
   ```powershell
   wsl --install
   ```

2. **在 WSL 中构建**
   ```bash
   # 进入项目目录
   cd /mnt/c/CODE/QTS/Projects/AVDownloader/AVDownloaderWithQTCpp/mobile
   
   # 运行构建脚本
   bash build_linux.sh
   ```

### 方案二：使用 Docker

1. **安装 Docker Desktop**
   - 下载地址：https://www.docker.com/products/docker-desktop

2. **使用 Docker 构建**
   ```bash
   cd mobile
   docker-compose up --build
   ```

### 方案三：使用 Linux/Mac 系统

直接在 Linux 或 Mac 系统上运行：

```bash
cd mobile
bash build_linux.sh
```

### 方案四：使用 GitHub Actions（云构建）

创建 `.github/workflows/build-apk.yml` 文件，使用 GitHub Actions 自动构建 APK。

## 📦 手动打包步骤

如果你不想使用脚本，可以手动执行以下步骤：

### 1. 安装依赖

```bash
# 安装 Python 依赖
pip install buildozer cython

# 安装系统依赖（Ubuntu/Debian）
sudo apt-get update
sudo apt-get install -y \
    git zip unzip openjdk-17-jdk \
    autoconf libtool pkg-config \
    zlib1g-dev libncurses5-dev \
    cmake libffi-dev libssl-dev
```

### 2. 配置 Buildozer

编辑 `buildozer.spec` 文件，确保以下配置正确：

```ini
title = AVDownloader
package.name = avdownloader
package.domain = com.avdownloader
version = 1.0.0

requirements = python3,kivy,requests,urllib3,beautifulsoup4,pycryptodome

android.permissions = INTERNET,ACCESS_NETWORK_STATE,ACCESS_WIFI_STATE,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE
```

### 3. 构建 APK

```bash
# 构建 Debug 版本
buildozer -v android debug

# 构建 Release 版本
buildozer -v android release
```

### 4. 获取 APK

构建成功后，APK 文件位于 `bin/` 目录：

```
bin/
└── avdownloader-1.0.0-arm64-v8a_armeabi-v7a-debug.apk
```

## 🚀 安装到 Android 设备

### 方法一：通过 ADB

```bash
adb install -r bin/avdownloader-1.0.0-arm64-v8a_armeabi-v7a-debug.apk
```

### 方法二：直接安装

1. 将 APK 文件传输到手机
2. 在手机上打开 APK 文件
3. 允许安装未知来源应用
4. 完成安装

## 📝 使用说明

1. **输入视频 URL** - 在输入框中粘贴 M3U8 链接或直接视频链接
2. **点击开始下载** - 应用会自动下载并合并视频
3. **查看进度** - 实时显示下载进度和日志
4. **查找视频** - 下载完成的视频保存在 `/sdcard/Download/AVDownloader/`

## ⚠️ 注意事项

1. **存储权限** - 首次使用需要授予存储权限
2. **网络权限** - 需要网络连接才能下载视频
3. **后台下载** - 切换到后台时下载可能中断
4. **大文件下载** - 建议连接 WiFi 下载大文件

## 🔧 技术说明

### 与桌面版的区别

| 功能 | 桌面版 | 移动版 |
|------|--------|--------|
| UI 框架 | PyQt5 | Kivy |
| 浏览器自动化 | Selenium | 不支持 |
| TS 合并 | FFmpeg | 纯 Python |
| 并发数 | 8 线程 | 4 线程 |
| 存储路径 | C:\index | /sdcard/Download/AVDownloader |

### 依赖库

- **Kivy** - 跨平台 GUI 框架
- **Requests** - HTTP 请求库
- **BeautifulSoup4** - HTML 解析库
- **PyCryptodome** - 加密解密库

## 🐛 常见问题

### 1. 应用闪退

- 检查是否授予存储权限
- 检查网络连接是否正常

### 2. 下载失败

- 检查 URL 是否有效
- 检查网络连接
- 查看日志输出

### 3. 视频无法播放

- 确保视频格式受支持（MP4、TS）
- 尝试使用其他播放器

## 📄 许可证

本项目仅供学习研究使用，请遵守当地法律法规。

## 📞 技术支持

- Buildozer 文档：https://buildozer.readthedocs.io/
- Kivy 文档：https://kivy.org/doc/stable/
- Python-For-Android：https://python-for-android.readthedocs.io/

---

**注意**：首次打包需要下载大量依赖，耗时约 30-60 分钟，请耐心等待。
