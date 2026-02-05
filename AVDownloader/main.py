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
    
    script_content = "@echo off\nchcp 65001 >nul\n\necho ========================================\necho    安装Chrome浏览器\necho ========================================\necho.\necho 正在启动Chrome安装程序...\necho.\n\n\"{}\"\n\necho.\necho Chrome安装完成！\necho 请重新运行视频下载器\n\necho.\necho 按任意键退出...\npause >nul".format(chrome_setup)
    
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
                return {'success': False, 'error': '操作已取消'}
            
            # 添加进度回调（仅当函数接受该参数时）
            import inspect
            sig = inspect.signature(self.func)
            if 'progress_callback' in sig.parameters:
                def progress_callback(percentage, downloaded, total):
                    # 检查是否应该停止
                    if self.should_stop:
                        return
                    self.progress_updated.emit(percentage, downloaded, total)
                self.kwargs['progress_callback'] = progress_callback
            
            # 执行函数
            result = self.func(*self.args, **self.kwargs)
            self.finished.emit(result)
        except Exception as e:
            self.finished.emit({'success': False, 'error': str(e)})

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
        self.ts_merger = TSMerger()
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
        检测临时目录中是否有剩余文件
        """
        try:
            self.log("正在获取临时子目录...", "DEBUG")
            subdirs = self.ts_merger.get_temp_subdirs()
            
            if subdirs:
                self.log(f"检测到 {len(subdirs)} 个临时下载目录", "INFO")
                self.log(f"临时目录列表: {subdirs}", "DEBUG")
                
                # 显示对话框
                self.log("显示临时文件处理对话框", "INFO")
                dialog = TempFilesDialog(subdirs, self)
                result = dialog.exec_()
                
                if result == QDialog.Accepted:
                    action = dialog.get_action()
                    selected_subdir = dialog.get_selected_subdir()
                    
                    if action == 'delete' and selected_subdir:
                        # 删除选中的子目录
                        self.log(f"删除临时目录: {selected_subdir}", "INFO")
                        self.log(f"删除目录: {selected_subdir}", "DEBUG")
                        success = self.ts_merger.delete_temp_subdir(selected_subdir)
                        if success:
                            QMessageBox.information(self, "成功", f"临时目录已删除: {selected_subdir}")
                            self.log(f"临时目录删除成功: {selected_subdir}", "INFO")
                        else:
                            QMessageBox.warning(self, "失败", f"删除临时目录失败: {selected_subdir}")
                            self.log(f"临时目录删除失败: {selected_subdir}", "ERROR")
                    
                    elif action == 'clear_all':
                        # 清空所有临时目录
                        self.log("清空所有临时目录", "INFO")
                        self.log(f"将清空 {len(subdirs)} 个临时目录", "DEBUG")
                        success = self.ts_merger.clear_temp_dir()
                        if success:
                            QMessageBox.information(self, "成功", "所有临时目录已清空")
                            self.log("所有临时目录清空成功", "INFO")
                        else:
                            QMessageBox.warning(self, "失败", "清空临时目录失败")
                            self.log("清空临时目录失败", "ERROR")
                    
                    elif selected_subdir:
                        # 合并选中的子目录
                        self.log(f"合并临时目录: {selected_subdir}", "INFO")
                        self.log(f"合并目录: {selected_subdir}", "DEBUG")
                        
                        # 检查是否需要解密
                        self.log("询问是否需要解密", "INFO")
                        reply = QMessageBox.question(
                            self, 
                            "是否需要解密", 
                            "这些TS文件可能是加密的。\n\n如果需要解密，请提供原始的M3U8 URL。\n\n是否需要解密？",
                            QMessageBox.Yes | QMessageBox.No
                        )
                        
                        if reply == QMessageBox.Yes:
                            # 需要解密，询问M3U8 URL
                            self.log("用户选择需要解密，询问M3U8 URL", "INFO")
                            m3u8_url, ok = QInputDialog.getText(
                                self,
                                "输入M3U8 URL",
                                "请输入原始的M3U8 URL（用于获取解密密钥）:",
                                QLineEdit.Normal
                            )
                            
                            if ok and m3u8_url:
                                self.log(f"用户提供了M3U8 URL: {m3u8_url}", "DEBUG")
                                # 询问输出文件名
                                output_filename, ok = QFileDialog.getSaveFileName(
                                    self,
                                    "保存合并后的视频",
                                    os.path.join(self.download_path, "decrypted_video.mp4"),
                                    "视频文件 (*.mp4)"
                                )
                                
                                if ok:
                                    self.log(f"用户选择了输出文件: {output_filename}", "DEBUG")
                                    # 启动工作线程进行解密和合并
                                    self.log("启动工作线程进行解密和合并", "INFO")
                                    def decrypt_and_merge():
                                        from decrypt_existing import decrypt_existing_ts_files
                                        result = decrypt_existing_ts_files(
                                            m3u8_url,
                                            selected_subdir,
                                            output_filename
                                        )
                                        return result
                                    
                                    self.worker_thread = WorkerThread(decrypt_and_merge)
                                    self.worker_thread.finished.connect(self.on_merge_finished)
                                    self.worker_thread.start()
                        else:
                            # 不需要解密，直接合并
                            self.log("用户选择不需要解密，直接合并", "INFO")
                            # 询问输出文件名
                            output_filename, ok = QFileDialog.getSaveFileName(
                                self,
                                "保存合并后的视频",
                                os.path.join(self.download_path, "merged_video.mp4"),
                                "视频文件 (*.mp4)"
                            )
                            
                            if ok:
                                self.log(f"用户选择了输出文件: {output_filename}", "DEBUG")
                                # 启动工作线程进行合并
                                self.log("启动工作线程进行合并", "INFO")
                                def merge_existing():
                                    result = self.ts_merger.merge_existing_ts_files(
                                        selected_subdir,
                                        output_filename
                                    )
                                    return result
                                
                                self.worker_thread = WorkerThread(merge_existing)
                                self.worker_thread.finished.connect(self.on_merge_finished)
                                self.worker_thread.start()
            
            else:
                self.log("没有检测到临时文件", "INFO")
        
        except Exception as e:
            self.log(f"检测临时文件失败: {e}", "ERROR")
            import traceback
            self.log(f"错误详情: {traceback.format_exc()}", "ERROR")
    
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
        control_layout = QHBoxLayout()
        
        # URL输入
        url_label = QLabel("目标网址:")
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("请输入视频网站URL")
        self.url_input.setMinimumWidth(400)
        # 绑定Enter键到开始探测
        self.url_input.returnPressed.connect(self.start_detection)
        
        # 开始按钮
        self.start_button = QPushButton("开始探测")
        self.start_button.clicked.connect(self.start_detection)
        
        # 保存路径选择
        path_label = QLabel("保存路径:")
        self.path_input = QLineEdit(self.download_path)
        self.path_input.setMinimumWidth(300)
        
        # 浏览按钮
        browse_button = QPushButton("浏览")
        browse_button.clicked.connect(self.browse_path)
        
        # 清空按钮
        self.clear_button = QPushButton("清空")
        self.clear_button.clicked.connect(self.clear_all)
        
        # 添加到控制布局
        control_layout.addWidget(url_label)
        control_layout.addWidget(self.url_input)
        control_layout.addWidget(self.start_button)
        control_layout.addWidget(self.clear_button)
        control_layout.addWidget(path_label)
        control_layout.addWidget(self.path_input)
        control_layout.addWidget(browse_button)
        
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
        # 获取URL
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "警告", "请输入目标网址")
            return
        
        # 验证URL
        if not utils.is_valid_url(url):
            QMessageBox.warning(self, "警告", "请输入有效的URL")
            return
        
        # 保存当前URL
        self.current_url = url
        
        # 清空视频列表
        self.video_list.clear()
        self.video_items = []
        
        # 禁用按钮
        self.start_button.setEnabled(False)
        self.download_button.setEnabled(False)
        
        # 显示状态
        self.log("====================================", "INFO")
        self.log(f"开始探测视频资源: {url}", "INFO")
        self.log(f"目标URL: {url}", "DEBUG")
        self.log(f"保存路径: {self.download_path}", "DEBUG")
        self.log("====================================", "INFO")
        self.log("[步骤1/4] 正在初始化浏览器...", "INFO")
        self.progress_label.setText("正在初始化浏览器...")
        self.progress_bar.setValue(0)
        
        # 启动工作线程
        def detect_videos():
            try:
                # 初始化浏览器
                self.log("[步骤1/4] 正在初始化浏览器...", "INFO")
                self.log("正在创建浏览器实例...", "DEBUG")
                self.browser.init_browser()
                self.log("[步骤1/4] 浏览器初始化完成", "INFO")
                self.log("浏览器实例创建成功", "DEBUG")
                
                # 加载页面
                self.log(f"[步骤2/4] 正在加载页面: {url}", "INFO")
                self.log(f"请求URL: {url}", "DEBUG")
                success = self.browser.load_page(url)
                if not success:
                    self.log("[步骤2/4] 页面加载失败", "ERROR")
                    self.log("页面可能无法访问或网络连接失败", "ERROR")
                    return {'success': False, 'error': '页面加载失败，请检查网络连接或URL是否正确'}
                self.log("[步骤2/4] 页面加载完成", "INFO")
                self.log("页面加载成功", "DEBUG")
                
                # 获取页面内容
                self.log("[步骤3/4] 正在获取页面内容...", "INFO")
                html = self.browser.get_page_content()
                if not html:
                    self.log("[步骤3/4] 无法获取页面内容", "ERROR")
                    self.log("页面内容为空或获取失败", "ERROR")
                    return {'success': False, 'error': '无法获取页面内容，请检查网络连接'}
                self.log(f"[步骤3/4] 页面内容获取完成，大小: {len(html)} 字符", "INFO")
                self.log(f"页面内容长度: {len(html)} 字符", "DEBUG")
                
                # 探测视频资源（使用browser中的video_resources，已经过滤为只包含m3u8和key关键词）
                self.log("[步骤4/4] 正在探测视频资源...", "INFO")
                self.log("正在分析页面内容，提取视频链接...", "DEBUG")
                videos = self.browser.get_video_resources()
                self.log(f"[步骤4/4] 视频资源探测完成，找到 {len(videos)} 个资源", "INFO")
                self.log(f"找到 {len(videos)} 个视频资源", "DEBUG")
                
                # 关闭浏览器
                self.log("正在关闭浏览器...", "INFO")
                self.browser.close()
                self.log("浏览器已关闭", "INFO")
                
                return {'success': True, 'videos': videos}
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
                return {'success': False, 'error': f'探测过程中发生错误: {str(e)}'}
        
        # 启动线程
        self.worker_thread = WorkerThread(detect_videos)
        self.worker_thread.finished.connect(self.on_detection_finished)
        self.worker_thread.start()
    
    def on_detection_finished(self, result):
        """
        探测完成回调
        """
        # 启用按钮
        self.start_button.setEnabled(True)
        
        if result['success']:
            videos = result.get('videos', [])
            self.log(f"探测完成，找到 {len(videos)} 个视频资源", "INFO")
            self.log(f"视频资源数量: {len(videos)}", "DEBUG")
            
            # 添加到视频列表
            for i, video in enumerate(videos):
                item = VideoItem(video)
                self.video_list.addItem(item)
                self.video_items.append(item)
                self.log(f"添加视频资源 {i+1}: {video.get('url', '')}", "DEBUG")
            
            # 启用下载按钮
            if videos:
                self.download_button.setEnabled(True)
                self.progress_label.setText(f"找到 {len(videos)} 个视频资源")
                self.log("下载按钮已启用", "INFO")
            else:
                self.progress_label.setText("未找到视频资源")
                self.log("未找到视频资源", "WARNING")
        else:
            error = result.get('error', '未知错误')
            self.log(f"探测失败: {error}", "ERROR")
            self.progress_label.setText("探测失败")
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
        self.log("====================================", "INFO")
        self.log(f"开始下载视频: {video_url}", "INFO")
        self.log(f"视频URL: {video_url}", "DEBUG")
        self.log(f"保存路径: {self.download_path}", "DEBUG")
        self.log("====================================", "INFO")
        self.progress_label.setText("正在准备下载...")
        self.progress_bar.setValue(0)
        
        # 启动工作线程
        def download_video():
            try:
                # 检查是否为M3U8播放列表
                if self.ts_merger.is_m3u8_url(video_url):
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
        # 清空网址输入框
        self.url_input.clear()
        self.log("已清空URL输入框", "INFO")
        
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
                print("[关闭] 正在关闭程序...")
                
                # 停止TS合并器（优先级最高，因为它可能有ffmpeg进程）
                print("[关闭] 正在停止TS合并器...")
                try:
                    if hasattr(self, 'ts_merger') and self.ts_merger:
                        # 直接设置停止标志
                        self.ts_merger.should_stop = True
                        # 尝试终止可能的ffmpeg进程
                        if hasattr(self.ts_merger, 'ffmpeg_process'):
                            try:
                                self.ts_merger.ffmpeg_process.terminate()
                                print("[关闭] ffmpeg进程已终止")
                            except:
                                pass
                        print("[关闭] TS合并器已停止")
                except Exception as e:
                    print(f"[关闭] 停止TS合并器时出错: {e}")
                
                # 停止下载器
                print("[关闭] 正在停止下载器...")
                try:
                    if hasattr(self, 'downloader') and self.downloader:
                        self.downloader.stop()
                        print("[关闭] 下载器已停止")
                except Exception as e:
                    print(f"[关闭] 停止下载器时出错: {e}")
                
                # 停止工作线程
                if hasattr(self, 'worker_thread') and self.worker_thread and self.worker_thread.isRunning():
                    print("[关闭] 正在停止工作线程...")
                    try:
                        self.worker_thread.stop()
                        self.worker_thread.quit()
                        # 使用较短的超时时间，避免阻塞
                        self.worker_thread.wait(timeout=1000)  # 等待最多1秒
                        print("[关闭] 工作线程已停止")
                    except Exception as e:
                        print(f"[关闭] 停止工作线程时出错: {e}")
                
                # 确保浏览器关闭
                print("[关闭] 正在关闭浏览器...")
                try:
                    if hasattr(self, 'browser') and self.browser:
                        self.browser.close()
                        print("[关闭] 浏览器已关闭")
                except Exception as e:
                    print(f"[关闭] 关闭浏览器时出错: {e}")
                
                print("[关闭] 程序已关闭")
            except Exception as e:
                print(f"[关闭] 关闭操作时出错: {e}")
        
        # 启动关闭操作线程
        close_thread = threading.Thread(target=close_operation)
        close_thread.daemon = True
        close_thread.start()

if __name__ == "__main__":
    # 检查依赖
    if not check_dependencies():
        # 依赖检查失败，退出程序
        input("按任意键退出...")
        sys.exit(1)
    
    # 确保默认下载目录存在
    default_path = "C:\index"
    if not os.path.exists(default_path):
        try:
            os.makedirs(default_path)
        except:
            pass
    
    # 启动应用
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
