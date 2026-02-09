#!/bin/bash
# AVDownloader APK构建脚本（Linux/Mac）

set -e

echo "================================"
echo "AVDownloader APK构建脚本"
echo "================================"

# 检查依赖
if ! command -v python3 &> /dev/null; then
    echo "安装Python3..."
    sudo apt-get update
    sudo apt-get install -y python3 python3-pip
fi

# 安装buildozer
echo "安装buildozer..."
pip3 install --user buildozer cython

# 安装Android依赖
echo "安装Android构建依赖..."
sudo apt-get install -y \
    git \
    zip \
    unzip \
    openjdk-17-jdk \
    autoconf \
    libtool \
    pkg-config \
    zlib1g-dev \
    libncurses5-dev \
    libncursesw5-dev \
    libtinfo5 \
    cmake \
    libffi-dev \
    libssl-dev

# 构建APK
echo "开始构建APK..."
buildozer -v android debug

echo ""
echo "================================"
echo "构建完成！"
echo "APK文件位于: bin/"
echo "================================"
