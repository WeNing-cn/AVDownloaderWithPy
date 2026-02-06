import sys
import os
import subprocess
import threading
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QLineEdit, QPushButton, QListWidget, QListWidgetItem, 
    QTextEdit, QProgressBar, QFileDialog, QMessageBox, QSplitter,
    QGroupBox, QFormLayout, QComboBox, QDialog, QInputDialog
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QUrl
from PyQt5.QtGui import QIcon, QFont

# 导入自定义模块
from browser_simulator import SyncBrowserSimulator
from video_detector import VideoDetector
from video_downloader import VideoDownloader
from ts_merger import TSMerger
from utils import utils

# 全局变量
ROOT_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))
UTILS_DIR = os.path.join(ROOT_DIR, "Utils")
RESOURCES_DIR = os.path.join(ROOT_DIR, "Resources")
BATS_DIR = os.path.join(ROOT_DIR, "Bats")


def check_chrome():
    """
    检查Chrome浏览器是否安装
    检查路径：
    1. Program Files (x86)\Google\Chrome\Application\chrome.exe
    2. Program Files\Google\Chrome\Application\chrome.exe
    3. LocalAppData\Google\Chrome\Application\chrome.exe
    """
    print("正在检查Chrome浏览器...")
    
    # 检查常见安装路径
    chrome_paths = [
        os.path.join(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"), "Google", "Chrome", "Application", "chrome.exe"),
        os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"), "Google", "Chrome", "Application", "chrome.exe"),
        os.path.join(os.environ.get("LocalAppData", r"C:\Users\Default\AppData\Local"), "Google", "Chrome", "Application", "chrome.exe")
    ]
    
    for chrome_path in chrome_paths:
        if os.path.exists(chrome_path):
            print(f"找到Chrome浏览器: {chrome_path}")
            return True
    
    print("未找到Chrome浏览器")
    return False


def install_chrome():
    """
    运行Chrome安装脚本
    """
    print("正在准备安装Chrome浏览器...")
    
    # 检查Chrome安装程序是否存在
    chrome_setup = os.path.join(RESOURCES_DIR, "ChromeSetup.exe")
    
    if not os.path.exists(chrome_setup):
        print(f"未找到Chrome安装程序: {chrome_setup}")
        return False
    
    # 检查Bats目录是否存在
    if not os.path.exists(BATS_DIR):
        os.makedirs(BATS_DIR)
    
    # 创建Chrome安装脚本
    install_script = os.path.join(BATS_DIR, "InstallChrome.cmd")
    
    script_content = "@echo off\nchcp 65001 >nul\n\necho ========================================\necho    安装Chrome浏览器\necho ========================================\necho.\necho 正在启动Chrome安装程序...\necho.\n\"{}\"\n\necho.\necho Chrome安装完成！\necho 请重新运行视频下载器\n\necho.\necho 按任意键退出...\npause >nul".format(chrome_setup)
    
    try:
        with open(install_script, 'w', encoding='utf-8') as f:
            f.write(script_content)
        
        print(f"创建Chrome安装脚本: {install_script}")
        
        # 运行安装脚本
        print("正在运行Chrome安装脚本...")
        subprocess.run([install_script], shell=True)
        
        return True
    except Exception as e:
        print(f"创建或运行Chrome安装脚本失败: {e}")
        return False


def check_ffmpeg():
    """
    检查FFmpeg是否存在
    检查路径：Utils\ffmpeg.exe
    """
    print("正在检查FFmpeg工具...")
    
    ffmpeg_path = os.path.join(UTILS_DIR, "ffmpeg.exe")
    
    if os.path.exists(ffmpeg_path):
        print(f"找到FFmpeg: {ffmpeg_path}")
        return True
    else:
        print(f"未找到FFmpeg: {ffmpeg_path}")
        return False


def check_dependencies():
    """
    检查所有依赖
    """
    print("开始检查程序依赖...")
    
    # 检查Chrome
    chrome_installed = check_chrome()
    
    if not chrome_installed:
        print("Chrome浏览器未安装，准备安装...")
        
        # 运行Chrome安装
        install_success = install_chrome()
        
        if not install_success:
            print("Chrome安装失败，程序无法运行")
            return False
        else:
            print("Chrome安装完成，请重新运行程序")
            return False
    
    # 检查FFmpeg
    ffmpeg_installed = check_ffmpeg()
    
    if not ffmpeg_installed:
        print("FFmpeg工具未找到，程序无法运行")
        return False
    
    print("所有依赖检查通过")
    return True

class WorkerThread(QThread):
    """
    工作线程，用于执行耗时操作
    """
    progress_updated = pyqtSignal(float, int, int)
    status_updated = pyqtSignal(str)
    finished = pyqtSignal(dict)
    
    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.should_stop = False  # 添加停止标志
    
    def stop(self):
        """
        设置停止标志
        """
        self.should_stop = True
    
    def run(self):
        try:
            # 检查是否应该停止
            if self.should_stop:
                self.finished.emit({'success': False, 'error': '操作已取消'})
                return
            
            # 添加进度回调（仅当函数接受该参数时）
            import inspect
            try:
                sig = inspect.signature(self.func)
                if 'progress_callback' in sig.parameters:
                    def progress_callback(percentage, downloaded, total):
                        # 检查是否应该停止
                        if self.should_stop:
                            return
                        self.progress_updated.emit(percentage, downloaded, total)
                    self.kwargs['progress_callback'] = progress_callback
            except Exception as e:
                # 忽略签名检查错误，继续执行
                pass
            
            # 执行函数
            try:
                result = self.func(*self.args, **self.kwargs)
                self.finished.emit(result)
            except Exception as e:
                import traceback
                error_detail = traceback.format_exc()
                print(f"WorkerThread执行错误: {error_detail}")
                self.finished.emit({'success': False, 'error': f'{str(e)}\n{error_detail}'})
        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            print(f"WorkerThread线程错误: {error_detail}")
            self.finished.emit({'success': False, 'error': f'{str(e)}\n{error_detail}'})

class URLItem(QListWidgetItem):
    """
    URL项，用于在列表中显示URL及其下载状态
    """
    STATUS_PENDING = "待处理"
    STATUS_DOWNLOADING = "下载中"
    STATUS_SUCCESS = "下载成功"
    STATUS_FAILED = "下载失败"
    
    def __init__(self, url):
        super().__init__()
        self.url = url
        self.status = self.STATUS_PENDING
        self.update_display()
    
    def update_status(self, status):
        """
        更新下载状态
        """
        self.status = status
        self.update_display()
    
    def update_display(self):
        """
        更新显示文本
        """
        status_color = {
            self.STATUS_PENDING: "#000000",    # 黑色
            self.STATUS_DOWNLOADING: "#006400",  # 绿色
            self.STATUS_SUCCESS: "#008000",    # 深绿色
            self.STATUS_FAILED: "#FF0000"      # 红色
        }.get(self.status, "#000000")
        
        self.setText(f"{self.url} [{self.status}]")

class VideoItem(QListWidgetItem):
    """
    视频项，用于在列表中显示视频信息
    """
    def __init__(self, video_info):
        super().__init__()
        self.video_info = video_info
        self.setText(self._get_display_text())
    
    def _get_display_text(self):
        """
        获取显示文本
        """
        url = self.video_info.get('url', '')
        video_type = self.video_info.get('type', '')
        source = self.video_info.get('source', '')
        
        # 截取URL末尾作为显示文本
        display_url = url.split('/')[-1] if url else '未知视频'
        if len(display_url) > 50:
            display_url = display_url[:50] + '...'
        
        return f"{display_url} ({video_type}, {source})"

class TempFilesDialog(QDialog):
    """
    临时文件处理对话框
    """
    def __init__(self, subdirs, parent=None):
        super().__init__(parent)
        self.subdirs = subdirs
        self.selected_subdir = None
        self.init_ui()
    
    def init_ui(self):
        """
        初始化用户界面
        """
        self.setWindowTitle("检测到临时文件")
        self.setMinimumWidth(600)
        self.setMinimumHeight(400)
        
        layout = QVBoxLayout(self)
        
        # 说明标签
        info_label = QLabel("检测到以下临时下载目录，请选择处理方式：")
        layout.addWidget(info_label)
        
        # 子目录列表
        self.subdir_list = QListWidget()
        for subdir in self.subdirs:
            item = QListWidgetItem(subdir)
            self.subdir_list.addItem(item)
        
        layout.addWidget(self.subdir_list)
        
        # 按钮布局
        button_layout = QHBoxLayout()
        
        # 合并按钮
        self.merge_button = QPushButton("合并选中")
        self.merge_button.clicked.connect(self.merge_selected)
        button_layout.addWidget(self.merge_button)
        
        # 删除按钮
        self.delete_button = QPushButton("删除选中")
        self.delete_button.clicked.connect(self.delete_selected)
        button_layout.addWidget(self.delete_button)
        
        # 清空全部按钮
        self.clear_all_button = QPushButton("清空全部")
        self.clear_all_button.clicked.connect(self.clear_all)
        button_layout.addWidget(self.clear_all_button)
        
        # 忽略按钮
        self.ignore_button = QPushButton("忽略")
        self.ignore_button.clicked.connect(self.reject)
        button_layout.addWidget(self.ignore_button)
        
        layout.addLayout(button_layout)
    
    def merge_selected(self):
        """
        合并选中的子目录
        """
        selected_items = self.subdir_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "警告", "请选择要合并的目录")
            return
        
        self.selected_subdir = selected_items[0].text()
        self.action = 'merge'
        self.accept()
    
    def delete_selected(self):
        """
        删除选中的子目录
        """
        selected_items = self.subdir_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "警告", "请选择要删除的目录")
            return
        
        reply = QMessageBox.question(
            self, 
            "确认删除", 
            f"确定要删除目录 '{selected_items[0].text()}' 吗？",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.selected_subdir = selected_items[0].text()
            self.action = 'delete'
            self.accept()
    
    def clear_all(self):
        """
        清空所有临时文件
        """
        reply = QMessageBox.question(
            self, 
            "确认清空", 
            f"确定要清空所有 {len(self.subdirs)} 个临时目录吗？",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.action = 'clear_all'
            self.accept()
    
    def get_action(self):
        """
        获取用户选择的操作
        """
        return getattr(self, 'action', None)
    
    def get_selected_subdir(self):
        """
        获取选中的子目录
        """
        return self.selected_subdir

class MainWindow(QMainWindow):
    """
    主窗口
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("视频爬取下载工具")
        self.setGeometry(100, 100, 1200, 800)
        # 设置窗口图标（如果有）
        # self.setWindowIcon(QIcon('icon.ico'))
        # 设置字体
        font = QFont()
        font.setPointSize(10)
        self.setFont(font)
        
        # 状态变量
        self.current_url = ""
        self.download_path = r"C:\index"
        self.video_items = []
        self.worker_thread = None
        # 下载历史记录
        self.download_history = set()
        self.history_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "download_history.txt")
        # 加载下载历史记录
        self.load_download_history()
        
        # 初始化UI（必须先初始化UI，因为log方法依赖于self.console）
        print("正在初始化用户界面...")
        self.init_ui()
        print("用户界面初始化完成")
        
        # 初始化模块
        self.log("正在初始化浏览器模拟器...", "INFO")
        self.browser = SyncBrowserSimulator()
        self.log("浏览器模拟器初始化完成", "INFO")
        
        self.log("正在初始化视频检测器...", "INFO")
        self.detector = VideoDetector()
        self.log("视频检测器初始化完成", "INFO")
        
        self.log("正在初始化视频下载器...", "INFO")
        self.downloader = VideoDownloader()
        self.log("视频下载器初始化完成", "INFO")
        
        self.log("正在初始化TS合并器...", "INFO")
        self.ts_merger = TSMerger(log_callback=self.log)
        self.log("TS合并器初始化完成", "INFO")
        
        self.log(f"默认下载路径: {self.download_path}", "DEBUG")
        
        # 检测临时文件
        self.log("正在检测临时文件...", "INFO")
        self.check_temp_files()
        
        # 日志
        self.log("程序初始化完成", "INFO")
        self.log("所有模块初始化成功，程序已准备就绪", "INFO")
    
    def check_temp_files(self):
        """
        检测临时目录中是否有剩余文件（当前版本不处理temp中的文件）
        """
        # 根据用户要求，不再处理temp中的文件
        self.log("跳过临时文件检测，不处理temp中的文件", "INFO")
        return
    
    def on_merge_finished(self, result):
        """
        合并完成回调
        """
        if result:
            if isinstance(result, dict) and result.get('success'):
                output_path = result.get('output_path', '')
                filename = os.path.basename(output_path) if output_path else "未知文件"
                self.log(f"临时文件合并成功: {filename}", "INFO")
                if output_path:
                    self.log(f"合并后的文件路径: {output_path}", "DEBUG")
                QMessageBox.information(self, "成功", "临时文件合并成功")
            else:
                self.log("临时文件合并成功", "INFO")
                QMessageBox.information(self, "成功", "临时文件合并成功")
        else:
            self.log("临时文件合并失败", "ERROR")
            QMessageBox.warning(self, "失败", "临时文件合并失败")
    
    def init_ui(self):
        """
        初始化用户界面
        """
        # 主布局
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        self.setCentralWidget(central_widget)
        
        # 顶部控制区
        control_group = QGroupBox("控制中心")
        control_layout = QVBoxLayout()
        
        # URL输入部分
        url_section = QHBoxLayout()
        url_label = QLabel("目标网址:")
        url_section.addWidget(url_label)
        
        # URL列表
        self.url_list = QListWidget()
        self.url_list.setMinimumWidth(400)
        self.url_list.setMinimumHeight(100)
        url_section.addWidget(self.url_list)
        
        # URL操作按钮
        url_buttons = QVBoxLayout()
        self.add_url_button = QPushButton("添加")
        self.add_url_button.clicked.connect(self.add_url)
        url_buttons.addWidget(self.add_url_button)
        
        self.delete_url_button = QPushButton("删除")
        self.delete_url_button.clicked.connect(self.delete_url)
        url_buttons.addWidget(self.delete_url_button)
        
        self.clear_urls_button = QPushButton("清空")
        self.clear_urls_button.clicked.connect(self.clear_urls)
        url_buttons.addWidget(self.clear_urls_button)
        
        # 删除所有下载成功的网址按钮
        self.delete_success_button = QPushButton("删除已成功")
        self.delete_success_button.clicked.connect(self.delete_success_urls)
        url_buttons.addWidget(self.delete_success_button)
        
        url_section.addLayout(url_buttons)
        
        control_layout.addLayout(url_section)
        
        # 其他控制按钮
        other_controls = QHBoxLayout()
        
        # 自动下载按钮
        self.start_button = QPushButton("自动下载")
        self.start_button.clicked.connect(self.start_detection)
        other_controls.addWidget(self.start_button)
        
        # 手动下载按钮
        self.manual_download_button = QPushButton("手动下载")
        self.manual_download_button.clicked.connect(self.manual_download)
        other_controls.addWidget(self.manual_download_button)
        
        # 清空按钮
        self.clear_button = QPushButton("清空")
        self.clear_button.clicked.connect(self.clear_all)
        other_controls.addWidget(self.clear_button)
        
        # 保存路径选择
        path_label = QLabel("保存路径:")
        other_controls.addWidget(path_label)
        
        self.path_input = QLineEdit(self.download_path)
        self.path_input.setMinimumWidth(300)
        other_controls.addWidget(self.path_input)
        
        # 浏览按钮
        browse_button = QPushButton("浏览")
        browse_button.clicked.connect(self.browse_path)
        other_controls.addWidget(browse_button)
        
        control_layout.addLayout(other_controls)
        
        control_group.setLayout(control_layout)
        main_layout.addWidget(control_group)
        
        # 中间内容区
        splitter = QSplitter(Qt.Horizontal)
        
        # 左侧视频列表
        video_group = QGroupBox("视频资源列表")
        video_layout = QVBoxLayout()
        
        self.video_list = QListWidget()
        
        # 下载按钮
        self.download_button = QPushButton("下载选中视频")
        self.download_button.clicked.connect(self.download_selected_video)
        self.download_button.setEnabled(False)
        
        video_layout.addWidget(self.video_list)
        video_layout.addWidget(self.download_button)
        video_group.setLayout(video_layout)
        
        # 右侧控制台
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        # 控制台输出
        console_group = QGroupBox("控制台输出")
        console_layout = QVBoxLayout()
        
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setFont(QFont("Consolas", 10))
        
        console_layout.addWidget(self.console)
        console_group.setLayout(console_layout)
        
        right_layout.addWidget(console_group)
        
        # 添加到分隔器
        splitter.addWidget(video_group)
        splitter.addWidget(right_widget)
        splitter.setSizes([400, 800])
        
        main_layout.addWidget(splitter)
        
        # 底部进度区
        progress_group = QGroupBox("进度信息")
        progress_layout = QHBoxLayout()
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        
        self.progress_label = QLabel("就绪")
        
        progress_layout.addWidget(self.progress_bar)
        progress_layout.addWidget(self.progress_label)
        
        progress_group.setLayout(progress_layout)
        main_layout.addWidget(progress_group)
    
    def add_url(self):
        """
        添加URL
        """
        url, ok = QInputDialog.getText(
            self,
            "添加URL",
            "请输入视频网站URL:",
            QLineEdit.Normal
        )
        
        if ok and url:
            url = url.strip()
            # 同步检测URL是否合法
            if utils.is_valid_url(url):
                item = URLItem(url)
                self.url_list.addItem(item)
                self.log(f"添加URL: {url}", "INFO")
            else:
                QMessageBox.warning(self, "警告", "请输入有效的URL")
                self.log(f"URL验证失败: {url}", "ERROR")
    
    def delete_url(self):
        """
        删除选中的URL
        """
        selected_items = self.url_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "警告", "请选择要删除的URL")
            return
        
        for item in selected_items:
            self.log(f"删除URL: {item.text()}", "INFO")
            self.url_list.takeItem(self.url_list.row(item))
    
    def clear_urls(self):
        """
        清空所有URL
        """
        if self.url_list.count() > 0:
            reply = QMessageBox.question(
                self, 
                "确认清空", 
                "确定要清空所有URL吗？",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.url_list.clear()
                self.log("清空所有URL", "INFO")

    def delete_success_urls(self):
        """
        删除所有下载成功的网址
        """
        success_count = 0
        for i in range(self.url_list.count() - 1, -1, -1):
            item = self.url_list.item(i)
            if isinstance(item, URLItem) and item.status == URLItem.STATUS_SUCCESS:
                self.url_list.takeItem(i)
                success_count += 1
        
        if success_count > 0:
            self.log(f"已删除 {success_count} 个下载成功的URL", "INFO")
        else:
            self.log("没有下载成功的URL可删除", "INFO")
    
    def load_download_history(self):
        """
        加载下载历史记录
        """
        try:
            import os
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        url = line.strip()
                        if url:
                            self.download_history.add(url)
                self.log(f"已加载 {len(self.download_history)} 条下载历史记录", "DEBUG")
        except Exception as e:
            self.log(f"加载下载历史记录失败: {str(e)}", "ERROR")
    
    def save_download_history(self):
        """
        保存下载历史记录
        """
        try:
            import os
            # 确保目录存在
            os.makedirs(os.path.dirname(self.history_file), exist_ok=True)
            with open(self.history_file, 'w', encoding='utf-8') as f:
                for url in self.download_history:
                    f.write(url + '\n')
            self.log(f"已保存 {len(self.download_history)} 条下载历史记录", "DEBUG")
        except Exception as e:
            self.log(f"保存下载历史记录失败: {str(e)}", "ERROR")
    
    def add_to_history(self, url):
        """
        添加URL到下载历史记录
        """
        if url not in self.download_history:
            self.download_history.add(url)
            self.save_download_history()
            self.log(f"已添加到下载历史: {url}", "DEBUG")
    
    def is_in_history(self, url):
        """
        检查URL是否在下载历史记录中
        """
        return url in self.download_history
    
    def manual_download(self):
        """
        手动下载功能
        """
        # 获取选中的URL项
        selected_items = self.url_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "警告", "请选择要手动下载的URL")
            return
        
        # 处理每个选中的URL
        for item in selected_items:
            if isinstance(item, URLItem):
                url = item.url
                self.log(f"开始手动下载: {url}", "INFO")
                item.update_status(URLItem.STATUS_DOWNLOADING)
                
                # 启动手动下载线程
                def download_task():
                    try:
                        # 初始化浏览器
                        self.browser.init_browser()
                        
                        # 加载页面
                        success = self.browser.load_page(url)
                        if not success:
                            self.log(f"页面加载失败: {url}", "ERROR")
                            item.update_status(URLItem.STATUS_FAILED)
                            return
                        
                        # 获取页面内容
                        html = self.browser.get_page_content()
                        if not html:
                            self.log(f"无法获取页面内容: {url}", "ERROR")
                            item.update_status(URLItem.STATUS_FAILED)
                            return
                        
                        # 探测视频资源
                        videos = self.browser.get_video_resources()
                        if not videos:
                            self.log(f"未找到视频资源: {url}", "ERROR")
                            item.update_status(URLItem.STATUS_FAILED)
                            return
                        
                        # 添加到视频列表供用户选择
                        self.video_list.clear()
                        self.video_items = []
                        for i, video in enumerate(videos):
                            video_item = VideoItem(video)
                            self.video_list.addItem(video_item)
                            self.video_items.append(video_item)
                        
                        # 启用下载按钮
                        self.download_button.setEnabled(True)
                        self.log(f"找到 {len(videos)} 个视频资源，请选择要下载的视频", "INFO")
                        item.update_status(URLItem.STATUS_PENDING)
                    except Exception as e:
                        self.log(f"手动下载失败: {str(e)}", "ERROR")
                        item.update_status(URLItem.STATUS_FAILED)
                    finally:
                        try:
                            self.browser.close()
                        except:
                            pass
                
                # 启动线程
                import threading
                thread = threading.Thread(target=download_task)
                thread.daemon = True
                thread.start()

    def log(self, message, level="INFO"):
        """
        输出日志到控制台
        
        Args:
            message: 日志消息
            level: 日志级别，可选值：INFO, WARNING, ERROR, DEBUG
        """
        timestamp = utils.get_datetime()
        # 根据日志级别设置不同的颜色
        level_colors = {
            "INFO": "#000000",  # 黑色
            "WARNING": "#FF8C00",  # 橙色
            "ERROR": "#FF0000",  # 红色
            "DEBUG": "#006400"   # 深绿色
        }
        color = level_colors.get(level, "#000000")
        log_message = f"<font color='{color}'>[{timestamp}] [{level}] {message}</font>\n"
        self.console.append(log_message)
        self.console.verticalScrollBar().setValue(self.console.verticalScrollBar().maximum())
        # 同时输出到控制台
        print(f"[{timestamp}] [{level}] {message}")
    
    def browse_path(self):
        """
        浏览保存路径
        """
        path = QFileDialog.getExistingDirectory(self, "选择保存路径", self.download_path)
        if path:
            self.download_path = path
            self.path_input.setText(path)
            self.log(f"保存路径已设置为: {path}", "INFO")
            self.log(f"新的保存路径: {path}", "DEBUG")
    
    def start_detection(self):
        """
        开始探测视频资源
        """
        # 获取所有URL项
        url_items = []
        for i in range(self.url_list.count()):
            item = self.url_list.item(i)
            if isinstance(item, URLItem):
                url_items.append(item)
        
        if not url_items:
            QMessageBox.warning(self, "警告", "请添加有效的URL")
            return
        
        # 清空视频列表
        self.video_list.clear()
        self.video_items = []
        
        # 禁用按钮
        self.start_button.setEnabled(False)
        self.download_button.setEnabled(False)
        
        # 显示状态
        self.log("======================================", "INFO")
        self.log(f"开始探测视频资源，共 {len(url_items)} 个URL", "INFO")
        for item in url_items:
            self.log(f"目标URL: {item.url}", "DEBUG")
        self.log(f"保存路径: {self.download_path}", "DEBUG")
        self.log("======================================", "INFO")
        self.log("[步骤1/4] 正在初始化浏览器...", "INFO")
        self.progress_label.setText("正在初始化浏览器...")
        self.progress_bar.setValue(0)
        
        # 启动工作线程
        def process_urls():
            failed_urls = []
            success_count = 0
            
            try:
                # 处理每个URL
                for url_index, url_item in enumerate(url_items):
                    url = url_item.url
                    self.log(f"======================================", "INFO")
                    self.log(f"处理URL {url_index + 1}/{len(url_items)}: {url}", "INFO")
                    
                    # 为每个URL创建一个新的浏览器实例
                    self.log("[步骤1/4] 正在初始化浏览器...", "INFO")
                    self.log("正在创建浏览器实例...", "DEBUG")
                    from browser_simulator import BrowserSimulator
                    current_browser = BrowserSimulator()
                    current_browser.init_browser()
                    self.log("[步骤1/4] 浏览器初始化完成", "INFO")
                    self.log("浏览器实例创建成功", "DEBUG")
                    
                    # 更新状态为下载中
                    url_item.update_status(URLItem.STATUS_DOWNLOADING)
                    
                    try:
                        # 加载页面
                        self.log(f"[步骤2/4] 正在加载页面: {url}", "INFO")
                        self.log(f"请求URL: {url}", "DEBUG")
                        success = current_browser.load_page(url)
                        if not success:
                            self.log("[步骤2/4] 页面加载失败", "ERROR")
                            self.log("页面可能无法访问或网络连接失败", "ERROR")
                            url_item.update_status(URLItem.STATUS_FAILED)
                            failed_urls.append(url)
                            continue
                        self.log("[步骤2/4] 页面加载完成", "INFO")
                        self.log("页面加载成功", "DEBUG")
                        
                        # 获取页面内容
                        self.log("[步骤3/4] 正在获取页面内容...", "INFO")
                        html = current_browser.get_page_content()
                        if not html:
                            self.log("[步骤3/4] 无法获取页面内容", "ERROR")
                            self.log("页面内容为空或获取失败", "ERROR")
                            url_item.update_status(URLItem.STATUS_FAILED)
                            failed_urls.append(url)
                            continue
                        self.log(f"[步骤3/4] 页面内容获取完成，大小: {len(html)} 字符", "INFO")
                        self.log(f"页面内容长度: {len(html)} 字符", "DEBUG")
                        
                        # 探测视频资源（使用browser中的video_resources，已经过滤为只包含m3u8和key关键词）
                        self.log("[步骤4/4] 正在探测视频资源...", "INFO")
                        self.log("正在分析页面内容，提取视频链接...", "DEBUG")
                        videos = current_browser.get_video_resources()
                        self.log(f"[步骤4/4] 视频资源探测完成，找到 {len(videos)} 个资源", "INFO")
                        self.log(f"找到 {len(videos)} 个视频资源", "DEBUG")
                        
                        # 检查是否有getmovie链接
                        getmovie_found = False
                        for video in videos:
                            video_url = video.get('url', '')
                            if 'getmovie' in video_url.lower():
                                # 找到getmovie链接，自动下载
                                self.log("[模式] 检测到getmovie链接，自动开始下载", "INFO")
                                download_success = self.download_video_automatically(video_url)
                                if download_success:
                                    url_item.update_status(URLItem.STATUS_SUCCESS)
                                    success_count += 1
                                    getmovie_found = True
                                    # 添加到下载历史记录
                                    self.add_to_history(url)
                                else:
                                    url_item.update_status(URLItem.STATUS_FAILED)
                                    failed_urls.append(url)
                                break
                        
                        # 如果没有getmovie链接，检查是否有唯一的m3u8文件
                        if not getmovie_found:
                            m3u8_videos = [v for v in videos if v.get('url', '').lower().endswith('.m3u8')]
                            if len(m3u8_videos) == 1:
                                # 找到唯一的m3u8文件，自动下载
                                self.log("[模式] 未检测到getmovie链接，但找到唯一的m3u8文件，自动开始下载", "INFO")
                                m3u8_url = m3u8_videos[0].get('url', '')
                                # 使用TS合并器下载
                                def progress_callback(percentage, downloaded, total):
                                    from PyQt5.QtWidgets import QApplication
                                    QApplication.processEvents()
                                    self.progress_bar.setValue(int(percentage))
                                    self.progress_label.setText(f"下载进度: {downloaded}/{total} ({percentage:.1f}%)")
                                
                                # 确保TS合并器的stop标志已重置
                                self.ts_merger.should_stop = False
                                
                                try:
                                    result = self.ts_merger.download_and_merge(
                                        m3u8_url,
                                        self.download_path,
                                        progress_callback=progress_callback
                                    )
                                    
                                    # 清理临时目录（如果有）
                                    if not result.get('success') and 'temp_subdir' in result and result['temp_subdir']:
                                        try:
                                            self.ts_merger.delete_temp_subdir(result['temp_subdir'])
                                            self.log(f"[清理] 已删除临时目录: {result['temp_subdir']}", "INFO")
                                        except Exception as e:
                                            self.log(f"[清理] 删除临时目录失败: {e}", "ERROR")
                                    
                                    if result.get('success'):
                                        url_item.update_status(URLItem.STATUS_SUCCESS)
                                        success_count += 1
                                        # 添加到下载历史记录
                                        self.add_to_history(url)
                                    else:
                                        url_item.update_status(URLItem.STATUS_FAILED)
                                        failed_urls.append(url)
                                        self.log(f"[错误] 下载失败: {result.get('error', '未知错误')}", "ERROR")
                                except Exception as e:
                                    # 捕获所有异常，确保程序不会崩溃
                                    self.log(f"[错误] 下载过程中发生异常: {str(e)}", "ERROR")
                                    import traceback
                                    error_detail = traceback.format_exc()
                                    self.log(f"[错误详情] {error_detail}", "ERROR")
                                    url_item.update_status(URLItem.STATUS_FAILED)
                                    failed_urls.append(url)
                                finally:
                                    # 确保ffmpeg进程被终止
                                    if hasattr(self.ts_merger, 'ffmpeg_process') and self.ts_merger.ffmpeg_process:
                                        try:
                                            self.ts_merger.ffmpeg_process.terminate()
                                            self.ts_merger.ffmpeg_process.wait(timeout=5)
                                            self.ts_merger.ffmpeg_process = None
                                        except Exception as terminate_error:
                                            self.log(f"[错误] 终止ffmpeg进程失败: {str(terminate_error)}", "ERROR")
                                    # 重置停止标志
                                    self.ts_merger.should_stop = False
                            else:
                                # 没有唯一的m3u8文件，标记为需要手动下载
                                self.log("[模式] 未检测到getmovie链接，且没有唯一的m3u8文件，标记为需要手动下载", "WARNING")
                                url_item.update_status(URLItem.STATUS_PENDING)
                                # 添加到视频列表供用户选择
                                self.video_list.clear()
                                self.video_items = []
                                for i, video in enumerate(videos):
                                    video_item = VideoItem(video)
                                    self.video_list.addItem(video_item)
                                    self.video_items.append(video_item)
                                
                                # 启用下载按钮
                                self.download_button.setEnabled(True)
                                self.log(f"找到 {len(videos)} 个视频资源，请选择要下载的视频", "INFO")
                                # 不要使用continue，否则会跳过后续URL
                                # continue
                            
                    except Exception as e:
                        # 出现错误，标记为失败并继续
                        self.log(f"[错误] 处理URL时发生错误: {str(e)}", "ERROR")
                        import traceback
                        error_detail = traceback.format_exc()
                        self.log(f"[错误详情] {error_detail}", "ERROR")
                        url_item.update_status(URLItem.STATUS_FAILED)
                        failed_urls.append(url)
                    finally:
                        # 关闭当前浏览器实例
                        try:
                            self.log("正在关闭浏览器...", "INFO")
                            current_browser.close()
                            self.log("浏览器已关闭", "INFO")
                        except Exception as close_error:
                            self.log(f"[错误] 关闭浏览器时发生错误: {str(close_error)}", "ERROR")
                
                # 准备结果
                result = {
                    'success': True,
                    'failed_urls': failed_urls,
                    'success_count': success_count,
                    'total_count': len(url_items)
                }
                
                return result
            except Exception as e:
                # 确保浏览器关闭
                try:
                    self.browser.close()
                except:
                    pass
                self.log(f"[错误] 探测过程中发生错误: {str(e)}", "ERROR")
                import traceback
                error_detail = traceback.format_exc()
                self.log(f"[错误详情] {error_detail}", "ERROR")
                
                # 标记所有未处理的URL为失败
                for item in url_items:
                    if item.status == URLItem.STATUS_DOWNLOADING:
                        item.update_status(URLItem.STATUS_FAILED)
                        failed_urls.append(item.url)
                
                result = {
                    'success': False,
                    'error': f'探测过程中发生错误: {str(e)}',
                    'failed_urls': failed_urls,
                    'success_count': success_count,
                    'total_count': len(url_items)
                }
                
                return result
        
        # 启动线程
        self.worker_thread = WorkerThread(process_urls)
        self.worker_thread.finished.connect(self.on_detection_finished)
        self.worker_thread.start()
    
    def download_video_automatically(self, video_url):
        """
        自动下载视频（用于getmovie链接）
        """
        try:
            # 检查是否为getmovie链接
            if 'getmovie' in video_url.lower():
                # 处理getmovie链接
                self.log("[模式] 检测到getmovie链接，使用特殊处理模式", "INFO")
                self.log("将获取JSON数据并提取M3U8链接", "DEBUG")
                
                # 获取getmovie JSON数据
                import requests
                import json
                response = requests.get(video_url, timeout=30)
                response.raise_for_status()
                json_data = response.json()
                
                if 'm3u8' in json_data:
                    m3u8_path = json_data['m3u8']
                    # 构造完整的M3U8 URL
                    from urllib.parse import urljoin
                    m3u8_url = urljoin(video_url, m3u8_path)
                    
                    self.log(f"[解析] 从getmovie JSON中提取到M3U8路径: {m3u8_path}", "INFO")
                    self.log(f"[构造] 完整的M3U8 URL: {m3u8_url}", "INFO")
                    
                    # 使用TS合并器下载
                    self.log("[模式] 检测到M3U8播放列表，使用TS分片合并模式", "INFO")
                    self.log("将使用并行下载和自动合并功能", "DEBUG")
                    
                    # 定义进度回调函数，更新UI进度条
                    def progress_callback(percentage, downloaded, total):
                        # 使用QApplication.processEvents()确保UI更新
                        from PyQt5.QtWidgets import QApplication
                        QApplication.processEvents()
                        # 更新进度条
                        self.progress_bar.setValue(int(percentage))
                        self.progress_label.setText(f"下载进度: {downloaded}/{total} ({percentage:.1f}%)")
                    
                    self.log(f"[准备] 目标URL: {m3u8_url}", "INFO")
                    self.log(f"[准备] 保存路径: {self.download_path}", "INFO")
                    self.log(f"M3U8 URL: {m3u8_url}", "DEBUG")
                    
                    result = self.ts_merger.download_and_merge(
                        m3u8_url,
                        self.download_path,
                        progress_callback=progress_callback
                    )
                    
                    # 清理临时目录（如果有）
                    if not result.get('success') and 'temp_subdir' in result and result['temp_subdir']:
                        try:
                            self.ts_merger.delete_temp_subdir(result['temp_subdir'])
                            self.log(f"[清理] 已删除临时目录: {result['temp_subdir']}", "INFO")
                        except Exception as e:
                            self.log(f"[清理] 删除临时目录失败: {e}", "ERROR")
                    
                    if result.get('success'):
                        self.log("[成功] 视频下载完成", "INFO")
                        return True
                    else:
                        self.log(f"[失败] 视频下载失败: {result.get('error', '未知错误')}", "ERROR")
                        return False
                else:
                    self.log("[错误] getmovie JSON中没有找到m3u8字段", "ERROR")
                    return False
            else:
                self.log("[错误] 不是getmovie链接", "ERROR")
                return False
        except Exception as e:
            self.log(f"[错误] 自动下载失败: {str(e)}", "ERROR")
            import traceback
            error_detail = traceback.format_exc()
            self.log(f"[错误详情] {error_detail}", "ERROR")
            return False
    
    def on_detection_finished(self, result):
        """
        探测完成回调
        """
        # 启用按钮
        self.start_button.setEnabled(True)
        
        if result.get('success'):
            failed_urls = result.get('failed_urls', [])
            success_count = result.get('success_count', 0)
            total_count = result.get('total_count', 0)
            
            self.log(f"探测完成，共处理 {total_count} 个URL", "INFO")
            self.log(f"成功: {success_count} 个，失败: {len(failed_urls)} 个", "INFO")
            
            # 显示状态提示
            if failed_urls:
                # 有下载失败的网址
                failed_list = "\n".join(failed_urls)
                self.log(f"失败的URL: {failed_list}", "ERROR")
                self.progress_label.setText(f"处理完成，{success_count} 个成功，{len(failed_urls)} 个失败")
                QMessageBox.warning(
                    self, 
                    "部分失败", 
                    f"处理完成，但有 {len(failed_urls)} 个URL下载失败:\n\n{failed_list}"
                )
            else:
                # 所有网址都下载成功
                self.log("所有URL下载成功", "INFO")
                self.progress_label.setText(f"所有 {total_count} 个URL下载成功")
                QMessageBox.information(
                    self, 
                    "全部成功", 
                    f"所有 {total_count} 个URL下载成功！"
                )
        else:
            error = result.get('error', '未知错误')
            failed_urls = result.get('failed_urls', [])
            self.log(f"探测失败: {error}", "ERROR")
            self.progress_label.setText("探测失败")
            
            if failed_urls:
                failed_list = "\n".join(failed_urls)
                QMessageBox.critical(
                    self, 
                    "错误", 
                    f"探测失败: {error}\n\n失败的URL:\n{failed_list}"
                )
            else:
                QMessageBox.critical(self, "错误", f"探测失败: {error}")
        
        self.progress_bar.setValue(100)
        self.log("探测任务完成", "INFO")
    
    def download_selected_video(self):
        """
        下载选中的视频
        """
        # 获取选中项
        selected_items = self.video_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "警告", "请选择要下载的视频")
            return
        
        selected_item = selected_items[0]
        if not isinstance(selected_item, VideoItem):
            return
        
        video_info = selected_item.video_info
        video_url = video_info.get('url', '')
        
        # 禁用按钮
        self.download_button.setEnabled(False)
        self.start_button.setEnabled(False)
        
        # 显示状态
        self.log("======================================", "INFO")
        self.log(f"开始下载视频: {video_url}", "INFO")
        self.log(f"视频URL: {video_url}", "DEBUG")
        self.log(f"保存路径: {self.download_path}", "DEBUG")
        self.log("======================================", "INFO")
        self.progress_label.setText("正在准备下载...")
        self.progress_bar.setValue(0)
        
        # 启动工作线程
        def download_video():
            try:
                # 检查是否为getmovie链接
                if 'getmovie' in video_url.lower():
                    # 处理getmovie链接
                    self.log("[模式] 检测到getmovie链接，使用特殊处理模式", "INFO")
                    self.log("将获取JSON数据并提取M3U8链接", "DEBUG")
                    
                    # 获取getmovie JSON数据
                    import requests
                    import json
                    response = requests.get(video_url, timeout=30)
                    response.raise_for_status()
                    json_data = response.json()
                    
                    if 'm3u8' in json_data:
                        m3u8_path = json_data['m3u8']
                        # 构造完整的M3U8 URL
                        from urllib.parse import urljoin
                        m3u8_url = urljoin(video_url, m3u8_path)
                        
                        self.log(f"[解析] 从getmovie JSON中提取到M3U8路径: {m3u8_path}", "INFO")
                        self.log(f"[构造] 完整的M3U8 URL: {m3u8_url}", "INFO")
                        
                        # 使用TS合并器下载
                        self.log("[模式] 检测到M3U8播放列表，使用TS分片合并模式", "INFO")
                        self.log("将使用并行下载和自动合并功能", "DEBUG")
                        
                        # 定义进度回调函数
                        def progress_callback(percentage, downloaded, total):
                            # 发射进度更新信号
                            self.worker_thread.progress_updated.emit(percentage, downloaded, total)
                        
                        self.log(f"[准备] 目标URL: {m3u8_url}", "INFO")
                        self.log(f"[准备] 保存路径: {self.download_path}", "INFO")
                        self.log(f"M3U8 URL: {m3u8_url}", "DEBUG")
                        
                        result = self.ts_merger.download_and_merge(
                            m3u8_url,
                            self.download_path,
                            progress_callback=progress_callback
                        )
                    else:
                        self.log("[错误] getmovie JSON中没有找到m3u8字段", "ERROR")
                        return {'success': False, 'error': 'getmovie JSON中没有找到m3u8字段'}
                # 检查是否为M3U8播放列表
                elif self.ts_merger.is_m3u8_url(video_url):
                    # 使用TS合并器下载
                    self.log("[模式] 检测到M3U8播放列表，使用TS分片合并模式", "INFO")
                    self.log("将使用并行下载和自动合并功能", "DEBUG")
                    
                    # 定义进度回调函数
                    def progress_callback(percentage, downloaded, total):
                        # 发射进度更新信号
                        self.worker_thread.progress_updated.emit(percentage, downloaded, total)
                    
                    self.log(f"[准备] 目标URL: {video_url}", "INFO")
                    self.log(f"[准备] 保存路径: {self.download_path}", "INFO")
                    self.log(f"M3U8 URL: {video_url}", "DEBUG")
                    
                    result = self.ts_merger.download_and_merge(
                        video_url,
                        self.download_path,
                        progress_callback=progress_callback
                    )
                else:
                    # 使用普通下载器
                    self.log("[模式] 使用普通视频下载模式", "INFO")
                    self.log("将直接下载完整视频文件", "DEBUG")
                    
                    # 定义进度回调函数
                    def progress_callback(percentage, downloaded, total):
                        # 发射进度更新信号
                        self.worker_thread.progress_updated.emit(percentage, downloaded, total)
                    
                    self.log(f"[准备] 目标URL: {video_url}", "INFO")
                    self.log(f"[准备] 保存路径: {self.download_path}", "INFO")
                    self.log(f"视频URL: {video_url}", "DEBUG")
                    
                    result = self.downloader.download_video(
                        video_url,
                        self.download_path,
                        progress_callback=progress_callback
                    )
                
                return result
            except Exception as e:
                self.log(f"[错误] 下载过程中发生错误: {str(e)}", "ERROR")
                import traceback
                error_detail = traceback.format_exc()
                self.log(f"[错误详情] {error_detail}", "ERROR")
                return {'success': False, 'error': str(e)}
        
        # 启动线程
        self.worker_thread = WorkerThread(download_video)
        self.worker_thread.progress_updated.connect(self.on_progress_updated)
        self.worker_thread.finished.connect(self.on_download_finished)
        self.worker_thread.start()
    
    def on_progress_updated(self, percentage, downloaded, total):
        """
        进度更新回调
        """
        self.progress_bar.setValue(int(percentage))
        # 显示分片个数，而不是字节数
        self.progress_label.setText(f"下载进度: {percentage:.1f}% ({int(downloaded)} / {int(total)} 个分片)")
    
    def on_download_finished(self, result):
        """
        下载完成回调
        """
        # 启用按钮
        self.download_button.setEnabled(True)
        self.start_button.setEnabled(True)
        self.log("按钮已重新启用", "INFO")
        
        if result['success']:
            file_path = result.get('file_path', '')
            filename = result.get('filename', '')
            file_size = result.get('size', 0)
            
            self.log(f"下载完成: {filename}", "INFO")
            self.log(f"保存路径: {file_path}", "INFO")
            self.log(f"文件大小: {utils.format_file_size(file_size)}", "INFO")
            self.log(f"文件名: {filename}", "DEBUG")
            self.log(f"文件路径: {file_path}", "DEBUG")
            self.log(f"文件大小: {file_size} 字节", "DEBUG")
            
            self.progress_label.setText("下载完成")
            QMessageBox.information(self, "成功", f"视频下载完成！\n保存路径: {file_path}")
        else:
            error = result.get('error', '未知错误')
            self.log(f"下载失败: {error}", "ERROR")
            self.progress_label.setText("下载失败")
            QMessageBox.critical(self, "错误", f"下载失败: {error}")
        
        self.progress_bar.setValue(100)
        self.log("下载任务完成", "INFO")
    
    def clear_all(self):
        """
        清空所有输入和输出
        """
        # 清空URL列表
        self.url_list.clear()
        self.log("已清空URL列表", "INFO")
        
        # 清空控制台输出
        self.console.clear()
        self.log("已清空控制台输出", "INFO")
        
        # 清空视频列表
        self.video_list.clear()
        self.video_items = []
        self.log("已清空视频列表", "INFO")
        
        # 重置进度条和状态
        self.progress_bar.setValue(0)
        self.progress_label.setText("就绪")
        self.log("已重置进度条和状态", "INFO")
        
        # 禁用下载按钮
        self.download_button.setEnabled(False)
        self.log("已禁用下载按钮", "INFO")
        
        # 确保开始按钮是可用的
        self.start_button.setEnabled(True)
        self.log("已确保开始按钮可用", "INFO")
        
        # 记录操作
        self.log("已清空所有输入和输出", "INFO")
    
    def closeEvent(self, event):
        """
        关闭窗口事件
        """
        # 立即接受事件，避免UI阻塞
        event.accept()
        
        # 在新线程中执行关闭操作，避免阻塞主线程
        import threading
        def close_operation():
            try:
                # 停止工作线程
                if hasattr(self, 'worker_thread') and self.worker_thread:
                    try:
                        self.worker_thread.stop()
                        self.worker_thread.wait()
                    except:
                        pass
                
                # 停止TS合并器（优先级最高，因为它可能有ffmpeg进程）
                if hasattr(self, 'ts_merger') and self.ts_merger:
                    try:
                        self.ts_merger.stop()
                    except:
                        pass
                    
                    # 尝试终止可能的ffmpeg进程
                    if hasattr(self.ts_merger, 'ffmpeg_process'):
                        try:
                            if self.ts_merger.ffmpeg_process:
                                self.ts_merger.ffmpeg_process.terminate()
                                print("[关闭] ffmpeg进程已终止")
                        except:
                            pass
                
                # 停止浏览器模拟器
                if hasattr(self, 'browser') and self.browser:
                    try:
                        self.browser.close()
                        print("[关闭] 浏览器已关闭")
                    except:
                        pass
                
                # 停止其他模块
                if hasattr(self, 'downloader') and self.downloader:
                    try:
                        if hasattr(self.downloader, 'stop'):
                            self.downloader.stop()
                    except:
                        pass
                
                if hasattr(self, 'detector') and self.detector:
                    try:
                        if hasattr(self.detector, 'stop'):
                            self.detector.stop()
                    except:
                        pass
                
            except Exception as e:
                print(f"[关闭] 发生错误: {e}")
        
        # 创建并启动关闭线程
        close_thread = threading.Thread(target=close_operation)
        close_thread.daemon = True
        close_thread.start()


def main():
    """
    主函数
    """
    # 检查依赖
    if not check_dependencies():
        return
    
    # 创建应用程序
    app = QApplication(sys.argv)
    
    # 创建主窗口
    window = MainWindow()
    window.show()
    
    # 运行应用程序
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()