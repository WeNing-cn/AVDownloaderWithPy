import os
import requests
import time
from datetime import datetime
from typing import Dict, Optional, Callable
from tqdm import tqdm

class VideoDownloader:
    def __init__(self):
        self.default_download_path = "C:\\index"
        self.chunk_size = 1024 * 1024  # 1MB
        self.max_retries = 5
        self.retry_delay = 3  # 秒
        self.timeout = 60  # 秒
        self.should_stop = False  # 添加停止标志
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': '*/*',
            'Accept-Language': 'zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3',
            'Connection': 'keep-alive',
            'Range': 'bytes=0-'  # 支持断点续传
        }
    
    def stop(self):
        """
        设置停止标志
        """
        self.should_stop = True
    
    def ensure_download_directory(self, download_path: str) -> bool:
        """
        确保下载目录存在
        """
        try:
            if not os.path.exists(download_path):
                os.makedirs(download_path)
            return True
        except Exception as e:
            print(f"创建下载目录失败: {e}")
            return False
    
    def generate_filename(self, video_url: str) -> str:
        """
        生成时间戳格式的文件名
        格式: 年-月-日-时-分-秒.mp4
        """
        try:
            import time
            from datetime import datetime
            
            # 获取当前时间
            now = datetime.now()
            
            # 生成时间戳格式的文件名
            filename = f"{now.year}-{now.month}-{now.day}-{now.hour}-{now.minute}-{now.second}.mp4"
            
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
            download_path: 下载路径，默认使用C:\\index
            filename: 文件名，默认使用时间戳格式
            progress_callback: 进度回调函数，接收(percentage, downloaded, total)参数
            
        Returns:
            包含下载结果的字典
        """
        # 使用默认下载路径
        if not download_path:
            download_path = self.default_download_path
        
        # 确保下载目录存在
        if not self.ensure_download_directory(download_path):
            return {
                'success': False,
                'error': '下载目录创建失败'
            }
        
        # 生成文件名
        if not filename:
            filename = self.generate_filename(video_url)
        
        # 完整文件路径
        file_path = os.path.join(download_path, filename)
        
        # 开始下载
        retries = 0
        while retries < self.max_retries:
            try:
                # 检查是否支持断点续传
                headers = self.headers.copy()
                if os.path.exists(file_path):
                    file_size = os.path.getsize(file_path)
                    headers['Range'] = f'bytes={file_size}-'
                    mode = 'ab'  # 追加模式
                else:
                    file_size = 0
                    mode = 'wb'  # 写入模式
                
                response = requests.get(
                    video_url, 
                    headers=headers, 
                    stream=True, 
                    timeout=self.timeout,
                    allow_redirects=True
                )
                
                # 检查响应状态
                if response.status_code not in [200, 206]:
                    raise Exception(f"请求失败，状态码: {response.status_code}")
                
                # 获取文件总大小
                total_size = int(response.headers.get('content-length', 0))
                if file_size > 0:
                    total_size += file_size
                
                # 开始下载
                downloaded = file_size
                with open(file_path, mode) as f:
                    with tqdm(
                        total=total_size, 
                        initial=downloaded, 
                        unit='B', 
                        unit_scale=True, 
                        desc=filename
                    ) as pbar:
                        for chunk in response.iter_content(chunk_size=self.chunk_size):
                            # 检查是否应该停止
                            if self.should_stop:
                                print("[下载] 收到停止信号，正在取消下载...")
                                return {
                                    'success': False,
                                    'error': '下载已取消'
                                }
                            
                            if chunk:
                                f.write(chunk)
                                downloaded += len(chunk)
                                pbar.update(len(chunk))
                                
                                # 调用进度回调
                                if progress_callback:
                                    percentage = (downloaded / total_size * 100) if total_size > 0 else 0
                                    progress_callback(percentage, downloaded, total_size)
                
                # 下载完成
                return {
                    'success': True,
                    'file_path': file_path,
                    'filename': filename,
                    'size': downloaded
                }
                
            except Exception as e:
                retries += 1
                print(f"下载失败 (尝试 {retries}/{self.max_retries}): {e}")
                
                if retries < self.max_retries:
                    print(f"{self.retry_delay}秒后重试...")
                    time.sleep(self.retry_delay)
                else:
                    # 清理不完整的文件
                    if os.path.exists(file_path) and os.path.getsize(file_path) == 0:
                        try:
                            os.remove(file_path)
                        except:
                            pass
                    
                    return {
                        'success': False,
                        'error': str(e)
                    }
    
    def download_videos(self, 
                       video_urls: list, 
                       download_path: Optional[str] = None, 
                       progress_callback: Optional[Callable] = None) -> list:
        """
        批量下载视频文件
        
        Args:
            video_urls: 视频URL列表
            download_path: 下载路径
            progress_callback: 进度回调函数
            
        Returns:
            下载结果列表
        """
        results = []
        
        for i, video_url in enumerate(video_urls):
            # 计算全局进度
            def batch_progress_callback(percentage, downloaded, total):
                if progress_callback:
                    global_percentage = (i + percentage / 100) / len(video_urls) * 100
                    progress_callback(global_percentage, downloaded, total)
            
            # 下载单个视频
            result = self.download_video(
                video_url,
                download_path,
                progress_callback=batch_progress_callback
            )
            results.append(result)
        
        return results
    
    def get_video_info(self, video_url: str) -> Dict:
        """
        获取视频信息
        
        Args:
            video_url: 视频URL
            
        Returns:
            包含视频信息的字典
        """
        try:
            response = requests.head(video_url, timeout=10)
            
            if response.status_code != 200:
                return {
                    'success': False,
                    'error': f"请求失败，状态码: {response.status_code}"
                }
            
            # 获取文件大小
            content_length = response.headers.get('content-length')
            file_size = int(content_length) if content_length else 0
            
            # 获取内容类型
            content_type = response.headers.get('content-type', 'unknown')
            
            return {
                'success': True,
                'file_size': file_size,
                'content_type': content_type,
                'headers': dict(response.headers)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def validate_video_url(self, video_url: str) -> bool:
        """
        验证视频URL是否可访问
        """
        try:
            response = requests.head(video_url, timeout=10)
            return response.status_code in [200, 206]
        except:
            return False
