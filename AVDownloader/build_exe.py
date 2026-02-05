"""
打包脚本 - 将Python程序打包成exe文件
使用PyInstaller进行打包
"""

import os
import subprocess
import sys

def install_pyinstaller():
    """
    安装PyInstaller
    """
    print("正在安装PyInstaller...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        print("PyInstaller安装成功")
        return True
    except subprocess.CalledProcessError as e:
        print(f"PyInstaller安装失败: {e}")
        return False

def build_exe():
    """
    打包成exe文件
    """
    # 获取当前目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 主程序文件
    main_file = os.path.join(current_dir, "main.py")
    
    # 输出目录
    dist_dir = os.path.join(current_dir, "dist")
    build_dir = os.path.join(current_dir, "build")
    
    # PyInstaller命令
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name=AVDownloader",
        "--windowed",  # 不显示控制台窗口
        "--onefile",  # 打包成单个exe文件
        "--clean",  # 清理临时文件
        "--noconfirm",  # 覆盖输出目录
        "--add-data=video_downloader.py;.",  # 添加依赖模块
        "--add-data=video_detector.py;.",
        "--add-data=video_downloader.py;.",
        "--add-data=ts_merger.py;.",
        "--add-data=browser_simulator.py;.",
        "--add-data=utils.py;.",
        "--add-data=decrypt_existing.py;.",
        "--hidden-import=PyQt5",
        "--hidden-import=PyQt5.QtCore",
        "--hidden-import=PyQt5.QtWidgets",
        "--hidden-import=PyQt5.QtGui",
        "--hidden-import=requests",
        "--hidden-import=beautifulsoup4",
        "--hidden-import=selenium",
        "--hidden-import=tqdm",
        "--hidden-import=pycryptodome",
        "--hidden-import=Crypto",
        "--hidden-import=Crypto.Cipher",
        "--hidden-import=Crypto.Cipher.AES",
        "--hidden-import=Crypto.Util.Padding",
        main_file
    ]
    
    print("开始打包程序...")
    print(f"命令: {' '.join(cmd)}")
    
    try:
        subprocess.check_call(cmd)
        print("\n打包成功！")
        print(f"exe文件位置: {os.path.join(dist_dir, 'AVDownloader.exe')}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"打包失败: {e}")
        return False

def main():
    """
    主函数
    """
    print("=" * 60)
    print("视频下载器 - 打包工具")
    print("=" * 60)
    print()
    
    # 检查是否安装了PyInstaller
    try:
        import PyInstaller
        print("PyInstaller已安装")
    except ImportError:
        print("PyInstaller未安装，正在安装...")
        if not install_pyinstaller():
            print("无法继续打包，请手动安装PyInstaller:")
            print("pip install pyinstaller")
            return
    
    print()
    
    # 开始打包
    if build_exe():
        print("\n打包完成！")
        print("您可以在dist目录中找到生成的exe文件")
        print("\n注意事项:")
        print("1. 确保ffmpeg已安装并添加到系统PATH")
        print("2. 确保Chrome浏览器已安装（用于Selenium）")
        print("3. 首次运行可能需要下载ChromeDriver")
    else:
        print("\n打包失败，请检查错误信息")

if __name__ == "__main__":
    main()