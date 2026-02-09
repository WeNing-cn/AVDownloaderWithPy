"""
文件名：build_apk.py
功能：Android APK打包脚本
创建时间：2026-02-09

使用说明：
1. 确保已安装buildozer: pip install buildozer
2. 确保已安装Android SDK和NDK
3. 运行此脚本进行打包
"""

import os
import sys
import subprocess
import shutil


def check_buildozer():
    """检查buildozer是否已安装"""
    try:
        subprocess.run(['buildozer', '--version'], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def install_buildozer():
    """安装buildozer"""
    print("正在安装buildozer...")
    try:
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'buildozer'], check=True)
        print("buildozer安装成功")
        return True
    except subprocess.CalledProcessError as e:
        print(f"buildozer安装失败: {e}")
        return False


def setup_android_sdk():
    """设置Android SDK环境"""
    print("检查Android SDK环境...")
    
    # 检查环境变量
    android_home = os.environ.get('ANDROID_HOME') or os.environ.get('ANDROID_SDK')
    
    if not android_home:
        print("警告: 未设置ANDROID_HOME环境变量")
        print("请设置Android SDK路径，例如:")
        print("  set ANDROID_HOME=C:\\Users\\<用户名>\\AppData\\Local\\Android\\Sdk")
        return False
    
    if not os.path.exists(android_home):
        print(f"Android SDK路径不存在: {android_home}")
        return False
    
    print(f"Android SDK路径: {android_home}")
    return True


def clean_build():
    """清理之前的构建文件"""
    print("清理构建文件...")
    dirs_to_remove = ['.buildozer', 'bin']
    for dir_name in dirs_to_remove:
        if os.path.exists(dir_name):
            try:
                shutil.rmtree(dir_name)
                print(f"已删除: {dir_name}")
            except Exception as e:
                print(f"删除 {dir_name} 失败: {e}")


def build_apk():
    """构建APK"""
    print("开始构建APK...")
    print("注意：首次构建可能需要下载依赖，耗时较长（30分钟-1小时）")
    
    try:
        # 使用buildozer构建debug版本
        result = subprocess.run(
            ['buildozer', '-v', 'android', 'debug'],
            capture_output=False,
            text=True
        )
        
        if result.returncode == 0:
            print("\n" + "="*50)
            print("APK构建成功！")
            print("="*50)
            
            # 查找生成的APK文件
            bin_dir = 'bin'
            if os.path.exists(bin_dir):
                apk_files = [f for f in os.listdir(bin_dir) if f.endswith('.apk')]
                if apk_files:
                    print(f"\n生成的APK文件:")
                    for apk in apk_files:
                        apk_path = os.path.join(bin_dir, apk)
                        size_mb = os.path.getsize(apk_path) / (1024 * 1024)
                        print(f"  - {apk} ({size_mb:.2f} MB)")
                        print(f"    路径: {os.path.abspath(apk_path)}")
            
            return True
        else:
            print(f"\nAPK构建失败，返回码: {result.returncode}")
            return False
            
    except Exception as e:
        print(f"构建过程出错: {e}")
        return False


def build_release():
    """构建发布版APK（需要签名）"""
    print("开始构建发布版APK...")
    print("注意：发布版需要签名密钥")
    
    try:
        result = subprocess.run(
            ['buildozer', '-v', 'android', 'release'],
            capture_output=False,
            text=True
        )
        return result.returncode == 0
    except Exception as e:
        print(f"构建发布版失败: {e}")
        return False


def main():
    """主函数"""
    print("="*50)
    print("AVDownloader Android APK 打包工具")
    print("="*50)
    
    # 检查buildozer
    if not check_buildozer():
        print("buildozer未安装，尝试安装...")
        if not install_buildozer():
            print("请手动安装buildozer: pip install buildozer")
            return
    
    # 检查Android SDK
    setup_android_sdk()
    
    # 显示菜单
    print("\n请选择操作:")
    print("1. 构建Debug版APK（推荐用于测试）")
    print("2. 构建Release版APK（需要签名）")
    print("3. 清理构建文件")
    print("4. 退出")
    
    choice = input("\n输入选项 (1-4): ").strip()
    
    if choice == '1':
        build_apk()
    elif choice == '2':
        build_release()
    elif choice == '3':
        clean_build()
    elif choice == '4':
        print("退出")
    else:
        print("无效选项")


if __name__ == '__main__':
    main()
