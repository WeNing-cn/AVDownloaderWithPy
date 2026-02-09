"""
文件名：main.py
功能：AVDownloader Android移动端主程序（Kivy版）
创建时间：2026-02-09
"""

import os
import sys
import threading
from datetime import datetime

# Kivy配置
os.environ['KIVY_NO_ARGS'] = '1'
os.environ['KIVY_WINDOW'] = 'sdl2'

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.progressbar import ProgressBar
from kivy.uix.popup import Popup
from kivy.uix.filechooser import FileChooserListView
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.properties import StringProperty, ObjectProperty
from kivy.graphics import Color, Rectangle

# 导入核心模块
from video_downloader_mobile import VideoDownloader
from ts_merger_mobile import TSMerger

# Android路径配置
if hasattr(sys, '_MEIPASS'):
    ROOT_DIR = sys._MEIPASS
else:
    ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

# Android存储路径
if os.path.exists('/sdcard'):
    DEFAULT_DOWNLOAD_PATH = '/sdcard/Download/AVDownloader'
else:
    DEFAULT_DOWNLOAD_PATH = os.path.join(os.path.expanduser('~'), 'Downloads', 'AVDownloader')

os.makedirs(DEFAULT_DOWNLOAD_PATH, exist_ok=True)


class LogLabel(ScrollView):
    """日志显示组件"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.label = Label(
            size_hint_y=None,
            text='',
            markup=True,
            halign='left',
            valign='top',
            color=(0.9, 0.9, 0.9, 1)
        )
        self.label.bind(texture_size=self.label.setter('size'))
        self.add_widget(self.label)
        self.logs = []
        
    def add_log(self, message, level='INFO'):
        """添加日志"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        color_map = {
            'INFO': '[color=#AAAAAA]',
            'SUCCESS': '[color=#00FF00]',
            'ERROR': '[color=#FF0000]',
            'WARNING': '[color=#FFA500]'
        }
        color = color_map.get(level, '[color=#AAAAAA]')
        log_entry = f"{color}[{timestamp}] [{level}] {message}[/color]"
        self.logs.append(log_entry)
        # 只保留最近100条日志
        if len(self.logs) > 100:
            self.logs = self.logs[-100:]
        self.label.text = '\n'.join(self.logs)
        # 自动滚动到底部
        Clock.schedule_once(self.scroll_to_bottom, 0.1)
        
    def scroll_to_bottom(self, dt):
        """滚动到底部"""
        self.scroll_y = 0


class MainLayout(BoxLayout):
    """主界面布局"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.padding = 10
        self.spacing = 10
        
        # 初始化下载器
        self.downloader = VideoDownloader()
        self.ts_merger = TSMerger(
            log_callback=self.add_log,
            download_path=DEFAULT_DOWNLOAD_PATH
        )
        self.download_thread = None
        self.is_downloading = False
        
        self._setup_ui()
        
    def _setup_ui(self):
        """设置UI界面"""
        # 标题
        title = Label(
            text='[b]AVDownloader 视频下载器[/b]',
            markup=True,
            size_hint_y=None,
            height=50,
            font_size='20sp',
            color=(0.2, 0.6, 1, 1)
        )
        self.add_widget(title)
        
        # URL输入区域
        url_box = BoxLayout(orientation='vertical', size_hint_y=None, height=120)
        url_label = Label(
            text='视频URL（支持M3U8链接）:',
            size_hint_y=None,
            height=30,
            halign='left',
            color=(0.8, 0.8, 0.8, 1)
        )
        url_label.bind(size=url_label.setter('text_size'))
        url_box.add_widget(url_label)
        
        self.url_input = TextInput(
            multiline=True,
            hint_text='请输入视频URL，多个URL用换行分隔\n支持M3U8播放列表链接',
            size_hint_y=None,
            height=80
        )
        url_box.add_widget(self.url_input)
        self.add_widget(url_box)
        
        # 下载路径显示
        path_box = BoxLayout(orientation='horizontal', size_hint_y=None, height=40)
        path_label = Label(
            text=f'下载路径: {DEFAULT_DOWNLOAD_PATH}',
            size_hint_x=0.8,
            halign='left',
            color=(0.7, 0.7, 0.7, 1)
        )
        path_label.bind(size=path_label.setter('text_size'))
        path_box.add_widget(path_label)
        self.add_widget(path_box)
        
        # 进度条
        progress_box = BoxLayout(orientation='vertical', size_hint_y=None, height=60)
        self.progress_label = Label(
            text='准备就绪',
            size_hint_y=None,
            height=25,
            color=(0.8, 0.8, 0.8, 1)
        )
        progress_box.add_widget(self.progress_label)
        
        self.progress_bar = ProgressBar(
            max=100,
            value=0,
            size_hint_y=None,
            height=20
        )
        progress_box.add_widget(self.progress_bar)
        self.add_widget(progress_box)
        
        # 按钮区域
        button_box = BoxLayout(orientation='horizontal', size_hint_y=None, height=50, spacing=10)
        
        self.download_btn = Button(
            text='开始下载',
            background_color=(0.2, 0.7, 0.3, 1),
            background_normal=''
        )
        self.download_btn.bind(on_press=self.start_download)
        button_box.add_widget(self.download_btn)
        
        self.stop_btn = Button(
            text='停止下载',
            background_color=(0.8, 0.2, 0.2, 1),
            background_normal='',
            disabled=True
        )
        self.stop_btn.bind(on_press=self.stop_download)
        button_box.add_widget(self.stop_btn)
        
        clear_btn = Button(
            text='清空日志',
            background_color=(0.5, 0.5, 0.5, 1),
            background_normal=''
        )
        clear_btn.bind(on_press=self.clear_logs)
        button_box.add_widget(clear_btn)
        
        self.add_widget(button_box)
        
        # 日志显示区域
        log_label = Label(
            text='下载日志:',
            size_hint_y=None,
            height=25,
            halign='left',
            color=(0.8, 0.8, 0.8, 1)
        )
        log_label.bind(size=log_label.setter('text_size'))
        self.add_widget(log_label)
        
        self.log_view = LogLabel()
        self.add_widget(self.log_view)
        
        # 添加初始日志
        self.add_log('AVDownloader 移动端已启动', 'INFO')
        self.add_log(f'下载路径: {DEFAULT_DOWNLOAD_PATH}', 'INFO')
        
    def add_log(self, message, level='INFO'):
        """添加日志"""
        Clock.schedule_once(lambda dt: self.log_view.add_log(message, level), 0)
        
    def update_progress(self, percentage, downloaded, total):
        """更新进度"""
        def update(dt):
            self.progress_bar.value = percentage
            self.progress_label.text = f'下载进度: {percentage:.1f}% ({downloaded}/{total} MB)'
        Clock.schedule_once(update, 0)
        
    def start_download(self, instance):
        """开始下载"""
        urls_text = self.url_input.text.strip()
        if not urls_text:
            self.show_popup('错误', '请输入视频URL')
            return
            
        urls = [url.strip() for url in urls_text.split('\n') if url.strip()]
        if not urls:
            self.show_popup('错误', '没有有效的URL')
            return
            
        self.is_downloading = True
        self.download_btn.disabled = True
        self.stop_btn.disabled = False
        self.progress_bar.value = 0
        
        # 在后台线程中执行下载
        self.download_thread = threading.Thread(
            target=self._download_worker,
            args=(urls,),
            daemon=True
        )
        self.download_thread.start()
        
    def _download_worker(self, urls):
        """下载工作线程"""
        try:
            total = len(urls)
            for index, url in enumerate(urls, 1):
                if not self.is_downloading:
                    self.add_log('下载已取消', 'WARNING')
                    break
                    
                self.add_log(f'[{index}/{total}] 开始下载: {url[:50]}...', 'INFO')
                
                # 判断是否为M3U8链接
                if '.m3u8' in url.lower():
                    result = self._download_m3u8(url, index, total)
                else:
                    result = self._download_direct(url, index, total)
                    
                if result.get('success'):
                    self.add_log(f'下载完成: {result.get("filename", "未知文件")}', 'SUCCESS')
                else:
                    self.add_log(f'下载失败: {result.get("error", "未知错误")}', 'ERROR')
                    
            self.add_log('所有任务处理完成', 'INFO')
        except Exception as e:
            self.add_log(f'下载过程出错: {str(e)}', 'ERROR')
        finally:
            Clock.schedule_once(self._reset_ui, 0)
            
    def _download_m3u8(self, url, index, total):
        """下载M3U8视频"""
        try:
            self.add_log('检测到M3U8播放列表，开始解析...', 'INFO')
            
            # 生成输出文件名
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = os.path.join(DEFAULT_DOWNLOAD_PATH, f'video_{timestamp}_{index}.mp4')
            
            # 使用TSMerger下载并合并
            result = self.ts_merger.download_and_merge(
                m3u8_url=url,
                output_file=output_file,
                progress_callback=lambda p, d, t: self.update_progress(p, d, t)
            )
            
            return result
        except Exception as e:
            return {'success': False, 'error': str(e)}
            
    def _download_direct(self, url, index, total):
        """直接下载视频文件"""
        try:
            result = self.downloader.download_video(
                video_url=url,
                download_path=DEFAULT_DOWNLOAD_PATH,
                progress_callback=lambda p, d, t: self.update_progress(p, d, t)
            )
            return result
        except Exception as e:
            return {'success': False, 'error': str(e)}
            
    def stop_download(self, instance):
        """停止下载"""
        self.is_downloading = False
        self.downloader.stop()
        self.ts_merger.stop()
        self.add_log('正在停止下载...', 'WARNING')
        self.stop_btn.disabled = True
        
    def _reset_ui(self, dt):
        """重置UI状态"""
        self.is_downloading = False
        self.download_btn.disabled = False
        self.stop_btn.disabled = True
        self.progress_label.text = '准备就绪'
        self.progress_bar.value = 0
        
    def clear_logs(self, instance):
        """清空日志"""
        self.log_view.logs = []
        self.log_view.label.text = ''
        self.add_log('日志已清空', 'INFO')
        
    def show_popup(self, title, message):
        """显示弹窗"""
        popup = Popup(
            title=title,
            content=Label(text=message),
            size_hint=(None, None),
            size=(300, 150)
        )
        popup.open()


class AVDownloaderApp(App):
    """Kivy应用主类"""
    def build(self):
        """构建应用"""
        # 设置窗口背景色
        Window.clearcolor = (0.15, 0.15, 0.15, 1)
        return MainLayout()


if __name__ == '__main__':
    AVDownloaderApp().run()
