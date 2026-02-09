"""
文件名：video_downloader_mobile.py
功能：移动端视频下载模块（适配Android）
创建时间：2026-02-09
"""

import os
import requests
import time
from datetime import datetime
from typing import Dict, Optional, Callable


class VideoDownloader:
    """视频下载器 - 移动端适配版"""
    
    def __init__(self):
        # Android下载路径
        if os.path.exists('/sdcard'):
            self.default_download_path = '/sdcard/Download/AVDownloader'
        else:
            self.default_download_path = os.path.join(
                os.path.expanduser('~'), 'Downloads', 'AVDownloader'
            )
        
        self.chunk_size = 1024 * 512  # 512KB，移动端使用更小的块
        self.max_retries = 3
        self.retry_delay = 2
        self.timeout = 30
        self.should_stop = False
        self.session = requests.Session()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 10; Mobile) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.120 Mobile Safari/537.36',
            'Accept': '*/*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
            'Connection': 'keep-alive'
        }
    
    def stop(self):
        """停止下载"""
        self.should_stop = True
        try:
            self.session.close()
        except:
            pass
    
    def ensure_download_directory(self, download_path: str) -> bool:
        """确保下载目录存在"""
        try:
            if not os.path.exists(download_path):
                os.makedirs(download_path, exist_ok=True)
            return True
        except Exception as e:
            print(f"创建下载目录失败: {e}")
            return False
    
    def generate_filename(self, video_url: str) -> str:
        """生成时间戳格式的文件名"""
        try:
            now = datetime.now()
            # 从URL中提取扩展名
            ext = '.mp4'
            if '.' in video_url:
                url_ext = video_url.split('.')[-1].split('?')[0].lower()
                if url_ext in ['mp4', 'avi', 'mov', 'mkv', 'flv', 'webm', 'ts']:
                    ext = f'.{url_ext}'
            
            filename = f"{now.year}{now.month:02d}{now.day:02d}_{now.hour:02d}{now.minute:02d}{now.second:02d}{ext}"
            return filename
        except Exception as e:
            print(f"生成文件名失败: {e}")
            return "video.mp4"
    
    def download_video(self, 
                      video_url: str, 
                      download_path: Optional[str] = None, 
                      filename: Optional[str] = None, 
                      progress_callback: Optional[Callable] = None) -> Dict:
        """
        下载视频文件
        
        Args:
            video_url: 视频URL
            download_path: 下载路径
            filename: 文件名
            progress_callback: 进度回调函数
            
        Returns:
            包含下载结果的字典
        """
        if not download_path:
            download_path = self.default_download_path
        
        if not self.ensure_download_directory(download_path):
            return {
                'success': False,
                'error': '下载目录创建失败'
            }
        
        if not filename:
            filename = self.generate_filename(video_url)
        
        file_path = os.path.join(download_path, filename)
        
        # 检查是否支持断点续传
        file_size = 0
        if os.path.exists(file_path):
            file_size = os.path.getsize(file_path)
        
        retries = 0
        while retries < self.max_retries:
            try:
                headers = self.headers.copy()
                if file_size > 0:
                    headers['Range'] = f'bytes={file_size}-'
                    mode = 'ab'
                else:
                    mode = 'wb'
                
                response = self.session.get(
                    video_url, 
                    headers=headers, 
                    stream=True, 
                    timeout=self.timeout,
                    allow_redirects=True
                )
                
                if response.status_code not in [200, 206]:
                    raise Exception(f"请求失败，状态码: {response.status_code}")
                
                total_size = int(response.headers.get('content-length', 0))
                if file_size > 0:
                    total_size += file_size
                
                # 如果没有content-length，尝试从header获取
                if total_size == 0:
                    total_size = int(response.headers.get('x-full-content-length', 0))
                
                downloaded = file_size
                last_update_time = time.time()
                
                with open(file_path, mode) as f:
                    for chunk in response.iter_content(chunk_size=self.chunk_size):
                        if self.should_stop:
                            return {
                                'success': False,
                                'error': '下载已取消',
                                'filename': filename,
                                'path': file_path
                            }
                        
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            
                            # 每0.5秒更新一次进度
                            current_time = time.time()
                            if current_time - last_update_time >= 0.5:
                                if total_size > 0 and progress_callback:
                                    percentage = (downloaded / total_size) * 100
                                    progress_callback(
                                        percentage,
                                        downloaded / (1024 * 1024),
                                        total_size / (1024 * 1024)
                                    )
                                last_update_time = current_time
                
                # 最终进度更新
                if progress_callback:
                    progress_callback(100, downloaded / (1024 * 1024), total_size / (1024 * 1024))
                
                return {
                    'success': True,
                    'filename': filename,
                    'path': file_path,
                    'size': downloaded
                }
                
            except Exception as e:
                retries += 1
                if retries >= self.max_retries:
                    return {
                        'success': False,
                        'error': f'下载失败（重试{self.max_retries}次）: {str(e)}',
                        'filename': filename
                    }
                time.sleep(self.retry_delay)
        
        return {
            'success': False,
            'error': '未知错误',
            'filename': filename
        }
