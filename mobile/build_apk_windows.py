"""
文件名：build_apk_windows.py
功能：Windows环境下的APK打包脚本（使用Buildozer）
创建时间：2026-02-09

注意：Buildozer在Windows上需要WSL2或Docker支持
本脚本提供多种打包方案
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path


class APKBuilder:
    def __init__(self):
        self.project_dir = Path(__file__).parent.absolute()
        self.sdk_dir = None
        self.ndk_dir = None
        
    def check_wsl(self):
        """检查是否安装了WSL"""
        try:
            result = subprocess.run(['wsl', '--version'], capture_output=True, text=True)
            return result.returncode == 0
        except FileNotFoundError:
            return False
    
    def check_docker(self):
        """检查是否安装了Docker"""
        try:
            result = subprocess.run(['docker', '--version'], capture_output=True, text=True)
            return result.returncode == 0
        except FileNotFoundError:
            return False
    
    def setup_android_sdk(self):
        """设置Android SDK"""
        print("="*60)
        print("Android SDK 设置")
        print("="*60)
        
        # 检查常见路径
        possible_paths = [
            Path.home() / "AppData" / "Local" / "Android" / "Sdk",
            Path("C:/Android/Sdk"),
            Path("D:/Android/Sdk"),
        ]
        
        for path in possible_paths:
            if path.exists():
                self.sdk_dir = path
                print(f"✓ 找到Android SDK: {path}")
                break
        
        if not self.sdk_dir:
            print("✗ 未找到Android SDK")
            print("\n请安装Android SDK:")
            print("1. 下载Android Studio: https://developer.android.com/studio")
            print("2. 安装SDK Platform 31和Build-Tools 31")
            print("3. 安装NDK (Side by side) 25.2.9519653")
            return False
        
        # 设置环境变量
        os.environ['ANDROID_HOME'] = str(self.sdk_dir)
        os.environ['ANDROID_SDK'] = str(self.sdk_dir)
        
        # 检查NDK
        ndk_paths = list(self.sdk_dir.glob("ndk/*"))
        if ndk_paths:
            self.ndk_dir = ndk_paths[0]
            print(f"✓ 找到Android NDK: {self.ndk_dir}")
        else:
            print("✗ 未找到Android NDK")
            print("请在Android Studio中安装NDK")
            return False
        
        return True
    
    def build_with_wsl(self):
        """使用WSL打包"""
        print("\n" + "="*60)
        print("使用WSL打包APK")
        print("="*60)
        
        if not self.check_wsl():
            print("✗ 未安装WSL")
            print("请安装WSL2: https://docs.microsoft.com/zh-cn/windows/wsl/install")
            return False
        
        # 创建WSL构建脚本
        wsl_script = """#!/bin/bash
set -e

echo "================================"
echo "在WSL中构建APK"
echo "================================"

# 更新系统
sudo apt-get update

# 安装依赖
sudo apt-get install -y python3-pip python3-venv git zip unzip openjdk-17-jdk

# 安装buildozer
pip3 install buildozer cython

# 进入项目目录
cd /mnt/{project_path}

# 构建APK
echo "开始构建APK..."
buildozer -v android debug

echo "构建完成！"
echo "APK文件位于: bin/"
""".format(project_path=str(self.project_dir).replace('C:', 'c').replace('\\', '/'))
        
        script_path = self.project_dir / "build_in_wsl.sh"
        with open(script_path, 'w') as f:
            f.write(wsl_script)
        
        print("✓ 已创建WSL构建脚本: build_in_wsl.sh")
        print("\n请在WSL终端中运行以下命令:")
        print(f"  cd /mnt/{str(self.project_dir).replace('C:', 'c').replace('\\', '/')}")
        print("  bash build_in_wsl.sh")
        
        return True
    
    def build_with_docker(self):
        """使用Docker打包"""
        print("\n" + "="*60)
        print("使用Docker打包APK")
        print("="*60)
        
        if not self.check_docker():
            print("✗ 未安装Docker")
            print("请安装Docker Desktop: https://www.docker.com/products/docker-desktop")
            return False
        
        # 创建Dockerfile
        dockerfile_content = """FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# 安装依赖
RUN apt-get update && apt-get install -y \\
    python3-pip \\
    python3-venv \\
    git \\
    zip \\
    unzip \\
    openjdk-17-jdk \\
    autoconf \\
    libtool \\
    pkg-config \\
    zlib1g-dev \\
    libncurses5-dev \\
    libncursesw5-dev \\
    libtinfo5 \\
    cmake \\
    libffi-dev \\
    libssl-dev \\
    automake \\
    && rm -rf /var/lib/apt/lists/*

# 安装buildozer
RUN pip3 install buildozer cython

# 设置工作目录
WORKDIR /app

# 复制项目文件
COPY . /app/

# 构建APK
CMD ["buildozer", "-v", "android", "debug"]
"""
        
        dockerfile_path = self.project_dir / "Dockerfile"
        with open(dockerfile_path, 'w') as f:
            f.write(dockerfile_content)
        
        # 创建docker-compose.yml
        compose_content = """version: '3.8'

services:
  buildozer:
    build: .
    volumes:
      - .:/app
      - ./.buildozer:/root/.buildozer
    command: buildozer -v android debug
"""
        
        compose_path = self.project_dir / "docker-compose.yml"
        with open(compose_path, 'w') as f:
            f.write(compose_content)
        
        print("✓ 已创建Docker配置文件")
        print("\n请运行以下命令构建APK:")
        print("  docker-compose up --build")
        
        return True
    
    def build_local(self):
        """本地构建（如果环境支持）"""
        print("\n" + "="*60)
        print("本地构建APK")
        print("="*60)
        
        # 检查buildozer
        try:
            subprocess.run(['buildozer', '--version'], capture_output=True, check=True)
            print("✓ Buildozer已安装")
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("✗ Buildozer未安装")
            print("正在安装buildozer...")
            subprocess.run([sys.executable, '-m', 'pip', 'install', 'buildozer'])
        
        # 设置Android SDK
        if not self.setup_android_sdk():
            return False
        
        # 尝试构建
        print("\n开始构建APK...")
        print("注意：首次构建需要下载大量依赖，耗时约30-60分钟")
        
        try:
            os.chdir(self.project_dir)
            result = subprocess.run(
                ['buildozer', '-v', 'android', 'debug'],
                capture_output=False
            )
            
            if result.returncode == 0:
                print("\n✓ APK构建成功！")
                self.show_apk_info()
                return True
            else:
                print(f"\n✗ 构建失败，返回码: {result.returncode}")
                return False
                
        except Exception as e:
            print(f"\n✗ 构建过程出错: {e}")
            return False
    
    def show_apk_info(self):
        """显示APK信息"""
        bin_dir = self.project_dir / "bin"
        if bin_dir.exists():
            apk_files = list(bin_dir.glob("*.apk"))
            if apk_files:
                print("\n" + "="*60)
                print("生成的APK文件:")
                print("="*60)
                for apk in apk_files:
                    size_mb = apk.stat().st_size / (1024 * 1024)
                    print(f"  📱 {apk.name}")
                    print(f"     大小: {size_mb:.2f} MB")
                    print(f"     路径: {apk}")
                    print()
    
    def run(self):
        """运行构建流程"""
        print("="*60)
        print("AVDownloader Android APK 打包工具")
        print("="*60)
        print(f"项目路径: {self.project_dir}")
        print()
        
        # 检查环境
        has_wsl = self.check_wsl()
        has_docker = self.check_docker()
        
        print("环境检测:")
        print(f"  WSL: {'✓ 已安装' if has_wsl else '✗ 未安装'}")
        print(f"  Docker: {'✓ 已安装' if has_docker else '✗ 未安装'}")
        print()
        
        # 选择构建方式
        print("请选择构建方式:")
        print("1. 使用WSL构建（推荐，需要WSL2）")
        print("2. 使用Docker构建（需要Docker Desktop）")
        print("3. 本地构建（Windows原生，可能有限制）")
        print("4. 生成构建脚本并手动执行")
        print("5. 退出")
        
        choice = input("\n输入选项 (1-5): ").strip()
        
        if choice == '1':
            if has_wsl:
                self.build_with_wsl()
            else:
                print("✗ 未安装WSL，请先安装WSL2")
        elif choice == '2':
            if has_docker:
                self.build_with_docker()
            else:
                print("✗ 未安装Docker，请先安装Docker Desktop")
        elif choice == '3':
            self.build_local()
        elif choice == '4':
            self.generate_build_scripts()
        elif choice == '5':
            print("退出")
        else:
            print("无效选项")
    
    def generate_build_scripts(self):
        """生成构建脚本"""
        print("\n" + "="*60)
        print("生成构建脚本")
        print("="*60)
        
        # 生成Linux/Mac构建脚本
        linux_script = """#!/bin/bash
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
sudo apt-get install -y \\
    git \\
    zip \\
    unzip \\
    openjdk-17-jdk \\
    autoconf \\
    libtool \\
    pkg-config \\
    zlib1g-dev \\
    libncurses5-dev \\
    libncursesw5-dev \\
    libtinfo5 \\
    cmake \\
    libffi-dev \\
    libssl-dev

# 构建APK
echo "开始构建APK..."
buildozer -v android debug

echo ""
echo "================================"
echo "构建完成！"
echo "APK文件位于: bin/"
echo "================================"
"""
        
        script_path = self.project_dir / "build_linux.sh"
        with open(script_path, 'w') as f:
            f.write(linux_script)
        
        # 在Unix系统上设置可执行权限
        if sys.platform != 'win32':
            os.chmod(script_path, 0o755)
        
        print(f"✓ 已生成Linux/Mac构建脚本: {script_path}")
        print("\n在Linux/Mac终端中运行:")
        print(f"  cd {self.project_dir}")
        print("  bash build_linux.sh")


def main():
    builder = APKBuilder()
    builder.run()


if __name__ == '__main__':
    main()
