import os
import re
import requests
import subprocess
import tempfile
import concurrent.futures
import shutil
from urllib.parse import urljoin, urlparse
from typing import List, Dict, Optional, Callable, Tuple
from tqdm import tqdm
from video_downloader import VideoDownloader
try:
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import unpad
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    print("警告: 未安装pycryptodome库，无法处理加密的M3U8流")
    print("可以使用: pip install pycryptodome")

class TSMerger:
    def __init__(self, log_callback=None, state_manager=None):
        self.downloader = VideoDownloader()
        self.max_workers = 8  # 并行下载线程数
        self.chunk_size = 1024 * 1024  # 1MB
        self.timeout = 60  # 秒
        # 固定的 temp 目录
        self.temp_dir = r"C:\index\temp"
        # 确保temp目录存在
        os.makedirs(self.temp_dir, exist_ok=True)
        # ffmpeg路径配置
        self.ffmpeg_path = self._find_ffmpeg()
        # 添加停止标志
        self.should_stop = False
        # 添加ffmpeg进程跟踪
        self.ffmpeg_process = None
        # 日志回调函数
        self.log_callback = log_callback
        # 状态管理器
        self.state_manager = state_manager
        # 当前任务ID
        self.current_task_id = None
        # 线程池执行器引用（用于强制停止）
        self.executor = None
        # 全局请求会话（用于强制中断）
        self.session = requests.Session()
        # 调试信息
        self.log(f"当前工作目录: {os.getcwd()}")
        self.log(f"系统PATH环境变量: {os.environ.get('PATH', '')}")
        self.log(f"ffmpeg路径配置: {self.ffmpeg_path}")
        self.log(f"临时目录: {self.temp_dir}")
        # 尝试验证ffmpeg
        try:
            import subprocess
            result = subprocess.run([self.ffmpeg_path, '-version'], capture_output=True, text=True)
            self.log(f"ffmpeg版本检查: {'成功' if result.returncode == 0 else '失败'}")
        except Exception as e:
            self.log(f"验证ffmpeg失败: {e}")
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': '*/*',
            'Accept-Language': 'zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3',
            'Connection': 'keep-alive'
        }
    
    def log(self, message, level="INFO"):
        """
        输出日志
        
        Args:
            message: 日志消息
            level: 日志级别
        """
        if self.log_callback:
            self.log_callback(message, level)
        else:
            print(f"[{level}] {message}")
    
    def stop(self):
        """
        设置停止标志并强制停止所有下载任务
        """
        print("[停止] 设置停止标志")
        self.should_stop = True
        
        # 关闭请求会话，强制中断所有正在进行的requests请求
        if self.session:
            print("[停止] 关闭请求会话，中断所有下载请求...")
            try:
                self.session.close()
            except Exception as e:
                print(f"[停止] 关闭请求会话失败: {e}")
        
        # 强制停止线程池中的所有任务
        if self.executor:
            print("[停止] 正在取消所有下载任务...")
            try:
                # 取消所有未完成的任务
                for future in self.executor._futures:
                    if not future.done():
                        future.cancel()
                print(f"[停止] 已取消 {len(self.executor._futures)} 个任务")
            except Exception as e:
                print(f"[停止] 取消任务失败: {e}")
        
        # 同时停止下载器
        if hasattr(self.downloader, 'stop'):
            self.downloader.stop()
        
        print("[停止] 停止信号已发送")
    
    def get_temp_dir(self) -> str:
        """
        获取临时目录
        """
        return self.temp_dir
    
    def _find_ffmpeg(self) -> str:
        """
        自动查找ffmpeg.exe
        按以下顺序查找：
        1. Utils目录（用户指定的位置）
        2. 当前目录（AVDownloader.exe所在目录）
        3. 系统PATH
        """
        import os
        import sys
        
        # 1. Utils目录（用户指定的位置）
        current_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        utils_ffmpeg_path = os.path.join(current_dir, "Utils", "ffmpeg.exe")
        if os.path.exists(utils_ffmpeg_path):
            print(f"找到ffmpeg.exe: {utils_ffmpeg_path}")
            return utils_ffmpeg_path
        
        # 2. 当前目录
        ffmpeg_path = os.path.join(current_dir, "ffmpeg.exe")
        if os.path.exists(ffmpeg_path):
            print(f"找到ffmpeg.exe: {ffmpeg_path}")
            return ffmpeg_path
        
        # 3. 系统PATH
        try:
            import subprocess
            result = subprocess.run(
                ["where", "ffmpeg"],
                capture_output=True,
                text=True,
                shell=True
            )
            if result.returncode == 0 and result.stdout:
                # 获取第一个结果
                ffmpeg_path = result.stdout.strip().split('\n')[0]
                if os.path.exists(ffmpeg_path):
                    print(f"找到ffmpeg.exe: {ffmpeg_path}")
                    return ffmpeg_path
        except Exception as e:
            print(f"在系统PATH中查找ffmpeg失败: {e}")
        
        # 4. 默认返回ffmpeg（依赖系统PATH）
        print("警告: 未找到ffmpeg.exe，将使用系统PATH中的ffmpeg")
        return "ffmpeg"
    
    def check_temp_files(self) -> List[str]:
        """
        检查临时目录中是否有剩余的TS文件
        返回所有TS文件的列表
        """
        if not os.path.exists(self.temp_dir):
            return []
        
        ts_files = []
        for item in os.listdir(self.temp_dir):
            if item.endswith('.ts'):
                ts_files.append(os.path.join(self.temp_dir, item))
        
        return ts_files
    
    def clear_temp_dir(self) -> bool:
        """
        清空临时目录
        """
        try:
            if os.path.exists(self.temp_dir):
                for item in os.listdir(self.temp_dir):
                    item_path = os.path.join(self.temp_dir, item)
                    if os.path.isfile(item_path):
                        os.remove(item_path)
                    elif os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                print(f"临时目录已清空: {self.temp_dir}")
                return True
            return False
        except Exception as e:
            print(f"清空临时目录失败: {e}")
            return False
    
    def get_temp_subdirs(self) -> List[str]:
        """
        获取临时目录中的所有子目录
        返回子目录名称列表
        """
        if not os.path.exists(self.temp_dir):
            return []
        
        subdirs = []
        for item in os.listdir(self.temp_dir):
            item_path = os.path.join(self.temp_dir, item)
            if os.path.isdir(item_path):
                subdirs.append(item)
        
        return subdirs
    
    def get_ts_files_in_subdir(self, subdir: str) -> List[str]:
        """
        获取指定子目录中的所有TS文件
        """
        subdir_path = os.path.join(self.temp_dir, subdir)
        print(f"检查子目录路径: {subdir_path}")
        
        if not os.path.exists(subdir_path):
            print(f"错误: 子目录不存在: {subdir_path}")
            return []
        
        ts_files = []
        for item in os.listdir(subdir_path):
            if item.endswith('.ts'):
                file_path = os.path.join(subdir_path, item)
                # 检查文件大小，跳过空文件
                try:
                    file_size = os.path.getsize(file_path)
                    if file_size > 0:
                        ts_files.append(file_path)
                        print(f"找到有效的TS文件: {file_path} (大小: {file_size} 字节)")
                    else:
                        print(f"跳过空文件: {file_path}")
                except Exception as e:
                    print(f"无法访问文件 {file_path}: {e}")
        
        # 按文件名排序
        ts_files.sort()
        print(f"总共找到 {len(ts_files)} 个有效的TS文件")
        return ts_files
    
    def create_temp_subdir(self) -> str:
        """
        创建一个新的临时子目录
        返回子目录路径
        """
        import time
        timestamp = int(time.time())
        subdir_name = f"download_{timestamp}"
        subdir_path = os.path.join(self.temp_dir, subdir_name)
        os.makedirs(subdir_path, exist_ok=True)
        return subdir_path
    
    def delete_temp_subdir(self, subdir: str) -> bool:
        """
        删除指定的临时子目录
        """
        try:
            # 检查subdir是否是完整路径
            if os.path.isabs(subdir):
                subdir_path = subdir
            else:
                subdir_path = os.path.join(self.temp_dir, subdir)
            
            # 检查是否是我们自己创建的临时目录（在self.temp_dir下）
            if not subdir_path.startswith(self.temp_dir):
                print(f"警告: 尝试删除非程序创建的临时目录: {subdir_path}")
                print("只允许删除程序在 C:\\index\\temp 下创建的临时目录")
                return False
            
            # 检查是否存在
            if not os.path.exists(subdir_path):
                print(f"警告: 临时目录不存在: {subdir_path}")
                return False
            
            # 删除目录
            shutil.rmtree(subdir_path)
            print(f"临时子目录已删除: {subdir_path}")
            return True
        except Exception as e:
            print(f"删除临时子目录失败: {e}")
            return False
    
    def parse_m3u8(self, m3u8_url: str) -> tuple:
        """
        解析M3U8播放列表，提取TS分片URL和加密信息
        支持处理嵌套的M3U8播放列表和加密流
        返回: (ts_urls, encryption_info)
        encryption_info = {'method': 'NONE', 'key_url': None, 'key': None, 'iv': None}
        """
        try:
            # 构建更完整的请求头，模拟真实浏览器
            enhanced_headers = self.headers.copy()
            enhanced_headers.update({
                'Accept-Encoding': 'gzip, deflate, br',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache',
                'Sec-Ch-Ua': '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
                'Sec-Ch-Ua-Mobile': '?0',
                'Sec-Ch-Ua-Platform': '"Windows"',
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'same-origin',
                'Upgrade-Insecure-Requests': '1'
            })
            
            # 下载M3U8文件，允许重定向，添加更完整的请求头，增加超时时间
            response = requests.get(
                m3u8_url, 
                timeout=60,  # 增加超时时间到60秒
                allow_redirects=True,
                headers=enhanced_headers,
                verify=False  # 忽略SSL证书验证（在某些情况下可能有帮助）
            )
            response.raise_for_status()
            
            m3u8_content = response.text
            ts_urls = []
            
            # 检查是否为HTML内容
            if '<!DOCTYPE html>' in m3u8_content or '<html>' in m3u8_content:
                print("警告: 收到HTML内容而不是M3U8内容")
                
                # 尝试从URL参数中提取真正的M3U8 URL
                import urllib.parse
                parsed_url = urllib.parse.urlparse(m3u8_url)
                query_params = urllib.parse.parse_qs(parsed_url.query)
                
                if 'url' in query_params:
                    real_m3u8_url = query_params['url'][0]
                    print(f"从参数中提取到真正的M3U8 URL: {real_m3u8_url}")
                    
                    # 递归调用parse_m3u8处理真正的M3U8 URL
                    return self.parse_m3u8(real_m3u8_url)
            
            # 解析加密信息
            encryption_info = {'method': 'NONE', 'key_url': None, 'key': None, 'iv': None}
            
            # 提取URLs
            nested_m3u8_urls = []
            
            for line in m3u8_content.split('\n'):
                line = line.strip()
                
                # 处理加密信息
                if line.startswith('#EXT-X-KEY:'):
                    self.log(f"[M3U8解析] 发现加密信息: {line}")
                    # 解析加密信息
                    key_info = line[len('#EXT-X-KEY:'):].strip()
                    # 提取METHOD
                    if 'METHOD=' in key_info:
                        method_match = key_info.split('METHOD=')[1].split(',')[0].strip('"\'')
                        encryption_info['method'] = method_match
                        self.log(f"[M3U8解析] 加密方法: {method_match}")
                    # 提取KEY URL
                    if 'URI=' in key_info:
                        import re
                        uri_match = re.search(r'URI="([^"]+)"', key_info)
                        if uri_match:
                            key_url = uri_match.group(1)
                            # 处理相对路径
                            if not key_url.startswith('http'):
                                key_url = self._normalize_url(key_url, response.url)
                            encryption_info['key_url'] = key_url
                            self.log(f"[M3U8解析] 密钥URL: {key_url}")
                    # 提取IV
                    if 'IV=' in key_info:
                        import re
                        iv_match = re.search(r'IV=0x([0-9A-Fa-f]+)', key_info)
                        if iv_match:
                            encryption_info['iv'] = iv_match.group(1)
                            self.log(f"[M3U8解析] 初始化向量: {encryption_info['iv']}")
                
                # 跳过注释和空行
                if not line or line.startswith('#'):
                    continue
                
                # 构建完整的URL
                # 使用最终的URL（可能是重定向后的）作为基础URL
                full_url = self._normalize_url(line, response.url)
                if full_url:
                    # 检查是否为嵌套的M3U8播放列表
                    if full_url.lower().endswith('.m3u8'):
                        nested_m3u8_urls.append(full_url)
                    else:
                        # 假设是TS分片
                        ts_urls.append(full_url)
            
            # 如果找到加密密钥URL，下载密钥
            if encryption_info['key_url']:
                self.log("[密钥处理] 开始处理加密密钥...")
                try:
                    # 检查是否需要使用本地getmovie.key文件
                    if 'getmovie' in m3u8_url.lower() or 'custom_key' in encryption_info['key_url'].lower():
                        # 尝试使用resource目录中的getmovie.key文件
                        import os
                        current_dir = os.path.dirname(os.path.abspath(__file__))
                        resource_dir = os.path.join(current_dir, '..', 'Resources')
                        key_file_path = os.path.join(resource_dir, 'getmovie.key')
                        
                        if os.path.exists(key_file_path):
                            with open(key_file_path, 'r', encoding='utf-8') as f:
                                key_content = f.read().strip()
                                encryption_info['key'] = key_content.encode('ascii')
                                self.log(f"[密钥处理] 使用resource目录的getmovie.key文件")
                                self.log(f"[密钥处理] 密钥长度: {len(encryption_info['key'])} 字节")
                                self.log(f"[密钥处理] 解密方法: 使用本地密钥文件")
                        else:
                            # 尝试正常下载密钥
                            self.log(f"[密钥处理] resource目录中未找到getmovie.key文件，尝试从网络下载")
                            self.log(f"[密钥处理] 密钥URL: {encryption_info['key_url']}")
                            key_response = requests.get(
                                encryption_info['key_url'],
                                headers=enhanced_headers,
                                timeout=30,
                                verify=False
                            )
                            key_response.raise_for_status()
                            encryption_info['key'] = key_response.content
                            self.log(f"[密钥处理] 密钥下载成功")
                            self.log(f"[密钥处理] 密钥长度: {len(encryption_info['key'])} 字节")
                            self.log(f"[密钥处理] 解密方法: 使用网络下载的密钥")
                    else:
                        # 正常下载密钥
                        self.log(f"[密钥处理] 从网络下载密钥")
                        self.log(f"[密钥处理] 密钥URL: {encryption_info['key_url']}")
                        key_response = requests.get(
                            encryption_info['key_url'],
                            headers=enhanced_headers,
                            timeout=30,
                            verify=False
                        )
                        key_response.raise_for_status()
                        encryption_info['key'] = key_response.content
                        self.log(f"[密钥处理] 密钥下载成功")
                        self.log(f"[密钥处理] 密钥长度: {len(encryption_info['key'])} 字节")
                        self.log(f"[密钥处理] 解密方法: 使用网络下载的密钥")
                except Exception as e:
                    self.log(f"[密钥处理] 下载密钥失败: {e}", "ERROR")
                    encryption_info['key'] = None
            else:
                self.log("[密钥处理] 未发现加密密钥URL，视频未加密")
                self.log("[密钥处理] 解密方法: 无需解密")
            
            # 如果找到TS分片，直接返回
            if ts_urls:
                return ts_urls, encryption_info
            
            # 如果没有找到TS分片，但找到嵌套的M3U8播放列表，递归解析
            if nested_m3u8_urls:
                print(f"找到 {len(nested_m3u8_urls)} 个嵌套的M3U8播放列表，开始递归解析")
                # 只解析第一个嵌套的M3U8播放列表（通常包含最高质量的视频）
                return self.parse_m3u8(nested_m3u8_urls[0])
            
            return ts_urls, encryption_info
            
        except Exception as e:
            print(f"解析M3U8失败: {e}")
            import traceback
            traceback.print_exc()
            return [], {'method': 'NONE', 'key_url': None, 'key': None, 'iv': None}
    
    def _normalize_url(self, url: str, base_url: str) -> str:
        """
        规范化URL，处理相对路径
        """
        try:
            # 如果是完整URL，直接返回
            if urlparse(url).scheme in ['http', 'https']:
                return url
            # 否则，使用base_url构建完整URL
            return urljoin(base_url, url)
        except Exception:
            return ''
    
    def decrypt_ts_segment(self, encrypted_data: bytes, encryption_info: dict, segment_index: int) -> bytes:
        """
        解密TS分片
        """
        if encryption_info['method'] == 'NONE' or not encryption_info['key']:
            return encrypted_data
        
        if not CRYPTO_AVAILABLE:
            print("错误: 需要pycryptodome库来解密TS分片")
            return encrypted_data
        
        try:
            key = encryption_info['key']
            iv = encryption_info['iv']
            
            # 如果没有提供IV，使用segment_index作为IV
            if iv is None:
                # 使用segment_index作为IV，格式为16字节的big-endian
                iv = segment_index.to_bytes(16, byteorder='big')
            else:
                # 将十六进制字符串转换为字节
                iv = bytes.fromhex(iv)
            
            # 创建AES解密器
            cipher = AES.new(key, AES.MODE_CBC, iv)
            
            # 解密数据
            decrypted_data = cipher.decrypt(encrypted_data)
            
            # 移除PKCS7填充
            try:
                decrypted_data = unpad(decrypted_data, AES.block_size)
            except:
                # 如果解密失败，可能数据没有被填充，直接返回
                pass
            
            return decrypted_data
            
        except Exception as e:
            print(f"解密TS分片失败: {e}")
            import traceback
            traceback.print_exc()
            return encrypted_data
    
    def download_ts_segment(self, ts_url: str, output_path: str, encryption_info: dict = None, segment_index: int = 0) -> bool:
        """
        下载单个TS分片
        """
        # 检查文件是否已存在
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            msg = f"[分片下载] 分片 {segment_index} 已存在，跳过下载"
            print(msg)
            return True
        
        # 检查是否应该停止
        if self.should_stop:
            msg = f"[分片下载] 收到停止信号，跳过分片 {segment_index}"
            print(msg)
            return False
        
        retries = 0
        max_retries = 3
        
        while retries < max_retries:
            # 再次检查是否应该停止
            if self.should_stop:
                msg = f"[分片下载] 收到停止信号，取消分片 {segment_index} 的下载"
                print(msg)
                return False
            
            try:
                msg = f"[分片下载] 开始下载分片 {segment_index}: {ts_url}"
                print(msg)
                
                response = self.session.get(
                    ts_url, 
                    headers=self.headers, 
                    stream=True, 
                    timeout=self.timeout,
                    allow_redirects=True
                )
                response.raise_for_status()
                
                # 确保输出目录存在
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                
                # 读取数据
                data = b''
                for chunk in response.iter_content(chunk_size=self.chunk_size):
                    # 检查是否应该停止
                    if self.should_stop:
                        msg = f"[分片下载] 收到停止信号，取消分片 {segment_index} 的下载"
                        print(msg)
                        return False
                    
                    if chunk:
                        data += chunk
                
                # 如果需要解密
                if encryption_info and encryption_info['method'] != 'NONE' and encryption_info['key']:
                    msg = f"[分片下载] 解密分片: {segment_index}"
                    print(msg)
                    data = self.decrypt_ts_segment(data, encryption_info, segment_index)
                
                # 写入文件
                with open(output_path, 'wb') as f:
                    f.write(data)
                
                # 检查文件大小
                if os.path.getsize(output_path) == 0:
                    raise Exception("下载的文件为空")
                
                msg = f"[分片下载] 分片 {segment_index} 下载成功，大小: {len(data)} 字节"
                print(msg)
                
                # 记录已下载的分片
                if self.state_manager and self.current_task_id:
                    self.state_manager.add_downloaded_segment(self.current_task_id, segment_index)
                
                return True
                
            except Exception as e:
                retries += 1
                error_msg = f"[分片下载] 下载TS分片失败 {ts_url} (尝试 {retries}/{max_retries}): {e}"
                print(error_msg)
                
                # 清理失败的文件
                if os.path.exists(output_path):
                    try:
                        os.remove(output_path)
                    except:
                        pass
                
                if retries >= max_retries:
                    error_msg = f"[分片下载] 分片 {segment_index} 下载失败，已达到最大重试次数"
                    print(error_msg)
                    return False
                
                # 等待一段时间后重试
                import time
                time.sleep(1)
        
        return False
    
    def download_ts_segments(self, 
                           ts_urls: List[str], 
                           temp_dir: str, 
                           encryption_info: dict = None,
                           progress_callback: Optional[Callable] = None) -> List[str]:
        """
        并行下载所有TS分片，并按顺序返回
        """
        downloaded_segments = []
        total_segments = len(ts_urls)
        
        # 创建临时目录
        os.makedirs(temp_dir, exist_ok=True)
        
        # 获取已下载的分片列表
        downloaded_indices = []
        if self.state_manager and self.current_task_id:
            downloaded_indices = self.state_manager.get_downloaded_segments(self.current_task_id)
            print(f"[分片下载] 已下载 {len(downloaded_indices)} 个分片: {downloaded_indices}")
        
        # 使用线程池并行下载
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 保存executor引用，用于强制停止
            self.executor = executor
            
            # 提交所有下载任务
            future_to_segment = {}
            skipped_count = 0  # 跳过的分片计数
            try:
                for i, ts_url in enumerate(ts_urls):
                    # 检查是否应该停止
                    if self.should_stop:
                        print(f"[分片下载] 收到停止信号，停止提交下载任务")
                        break
                    
                    # 检查分片是否已下载
                    if i in downloaded_indices:
                        segment_path = os.path.join(temp_dir, f"segment_{i:06d}.ts")
                        if os.path.exists(segment_path) and os.path.getsize(segment_path) > 0:
                            print(f"[分片下载] 分片 {i} 已存在，跳过下载")
                            skipped_count += 1
                            continue
                    
                    segment_path = os.path.join(temp_dir, f"segment_{i:06d}.ts")
                    future = executor.submit(self.download_ts_segment, ts_url, segment_path, encryption_info, i)
                    future_to_segment[future] = (i, segment_path)
            except Exception as e:
                print(f"[分片下载] 提交下载任务失败: {e}")
            
            # 监控下载进度
            completed = skipped_count  # 从跳过的分片开始计数
            success_map = {}  # 使用字典记录每个索引的下载结果
            
            try:
                for future in concurrent.futures.as_completed(future_to_segment):
                    # 检查是否应该停止
                    if self.should_stop:
                        print(f"[分片下载] 收到停止信号，取消剩余下载任务")
                        # 取消所有未完成的任务
                        for f in future_to_segment:
                            if not f.done():
                                try:
                                    f.cancel()
                                except:
                                    pass
                        break
                    
                    i, segment_path = future_to_segment[future]
                    try:
                        success = future.result()
                        if success:
                            success_map[i] = segment_path
                            completed += 1
                            
                            # 更新进度
                            if progress_callback:
                                try:
                                    progress = (completed / total_segments) * 100
                                    progress_callback(progress, completed, total_segments)
                                    progress_msg = f"下载进度: {completed}/{total_segments} ({progress:.1f}%)"
                                    print(progress_msg)
                                    self.log(progress_msg, "INFO")
                                except Exception as callback_error:
                                    error_msg = f"[分片下载] 进度回调失败: {callback_error}"
                                    print(error_msg)
                                    self.log(error_msg, "ERROR")
                        else:
                            error_msg = f"分片 {i} 下载失败"
                            print(error_msg)
                            self.log(error_msg, "ERROR")
                    
                    except Exception as e:
                        error_msg = f"分片 {i} 下载异常: {e}"
                        print(error_msg)
                        self.log(error_msg, "ERROR")
            except Exception as e:
                error_msg = f"[分片下载] 监控下载进度失败: {e}"
                print(error_msg)
                self.log(error_msg, "ERROR")
        
        # 按顺序返回下载成功的分片
        final_downloaded_segments = []
        for i in range(total_segments):
            segment_path = os.path.join(temp_dir, f"segment_{i:06d}.ts")
            if os.path.exists(segment_path) and os.path.getsize(segment_path) > 0:
                final_downloaded_segments.append(segment_path)
            else:
                warning_msg = f"警告: 分片 {i} 不存在或为空，跳过"
                print(warning_msg)
                self.log(warning_msg, "WARNING")
        
        summary_msg = f"成功下载 {len(final_downloaded_segments)}/{total_segments} 个分片（跳过 {skipped_count} 个已下载分片）"
        print(summary_msg)
        self.log(summary_msg, "INFO")
        return final_downloaded_segments
    
    def merge_ts_segments(self, 
                         ts_files: List[str], 
                         output_file: str) -> bool:
        """
        合并TS分片为MP4文件
        """
        try:
            # 检查是否有TS分片
            if not ts_files:
                error_message = "错误: 没有可合并的TS分片"
                self.log(error_message, "ERROR")
                print(error_message)
                return False
            
            # 检查所有TS文件是否存在
            missing_files = []
            for ts_file in ts_files:
                if not os.path.exists(ts_file):
                    missing_files.append(ts_file)
            
            if missing_files:
                error_message = f"错误: 以下TS文件不存在: {missing_files}"
                self.log(error_message, "ERROR")
                print(error_message)
                return False
            
            # 确保输出目录存在
            output_dir = os.path.dirname(output_file)
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            
            # 创建TS文件列表文件
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
                for ts_file in ts_files:
                    # 使用正斜杠，避免ffmpeg中的转义字符问题
                    ts_file_normalized = ts_file.replace(os.sep, '/')
                    # 打印文件路径以便调试
                    debug_message = f"添加TS文件到列表: {ts_file_normalized}"
                    self.log(debug_message, "DEBUG")
                    print(debug_message)
                    f.write(f"file '{ts_file_normalized}'\n")
                ts_list_file = f.name
            
            # 打印临时文件列表内容以便调试
            debug_message = f"临时文件列表路径: {ts_list_file}"
            self.log(debug_message, "DEBUG")
            print(debug_message)
            with open(ts_list_file, 'r', encoding='utf-8') as f:
                list_content = f.read()
                debug_message = f"临时文件列表内容:\n{list_content}"
                self.log(debug_message, "DEBUG")
                print(debug_message)
            
            # 再次检查所有TS文件是否存在，确保文件没有被删除或移动
            missing_files = []
            for ts_file in ts_files:
                if not os.path.exists(ts_file):
                    missing_files.append(ts_file)
            
            if missing_files:
                error_message = f"错误: 以下TS文件不存在: {missing_files}"
                self.log(error_message, "ERROR")
                print(error_message)
                try:
                    os.remove(ts_list_file)
                except:
                    pass
                return False
            
            # 使用ffmpeg合并
            cmd = [
                self.ffmpeg_path,
                '-y',  # 覆盖现有文件
                '-f', 'concat',
                '-safe', '0',
                '-i', ts_list_file,
                '-c', 'copy',
                '-bsf:a', 'aac_adtstoasc',  # 修复音频流
                output_file
            ]
            
            # 打印命令以便于调试
            debug_message = f"执行ffmpeg命令: {' '.join(cmd)}"
            self.log(debug_message, "DEBUG")
            print(debug_message)
            
            # 再次检查ffmpeg路径
            if not os.path.exists(self.ffmpeg_path) and self.ffmpeg_path != "ffmpeg":
                error_message = f"错误: ffmpeg文件不存在: {self.ffmpeg_path}"
                self.log(error_message, "ERROR")
                print(error_message)
                try:
                    os.remove(ts_list_file)
                except:
                    pass
                return False
            
            # 执行ffmpeg命令，使用简化的方式确保不会卡住
            import subprocess
            
            # 执行ffmpeg命令，使用check_call直接执行并等待完成
            try:
                # 执行命令并等待完成，使用DEVNULL避免输出缓冲区阻塞
                subprocess.check_call(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                    shell=False  # 确保不使用shell
                )
                
                success_message = f"ffmpeg合并成功: {output_file}"
                self.log(success_message, "INFO")
                print(success_message)
                return True
                
            except subprocess.CalledProcessError as e:
                error_message = f"ffmpeg合并失败 (返回码: {e.returncode})"
                self.log(error_message, "ERROR")
                print(error_message)
                try:
                    os.remove(ts_list_file)
                except:
                    pass
                return False
            except FileNotFoundError:
                error_message = "错误: 找不到ffmpeg命令，请确保ffmpeg已安装并添加到系统PATH环境变量中"
                self.log(error_message, "ERROR")
                print(error_message)
                print("可以从 https://ffmpeg.org/download.html 下载ffmpeg")
                try:
                    os.remove(ts_list_file)
                except:
                    pass
                return False
            except Exception as e:
                error_message = f"执行ffmpeg命令时出错: {e}"
                self.log(error_message, "ERROR")
                print(error_message)
                import traceback
                traceback.print_exc()
                try:
                    os.remove(ts_list_file)
                except:
                    pass
                return False
        except Exception as e:
            error_message = f"合并TS分片失败: {e}"
            self.log(error_message, "ERROR")
            print(error_message)
            return False
        finally:
            # 清理临时文件
            if 'ts_list_file' in locals() and os.path.exists(ts_list_file):
                try:
                    os.remove(ts_list_file)
                except:
                    pass
    
    def download_and_merge(self, 
                          m3u8_url: str, 
                          output_path: Optional[str] = None, 
                          output_filename: Optional[str] = None, 
                          progress_callback: Optional[Callable] = None) -> Dict:
        """
        完整的下载和合并流程
        
        Args:
            m3u8_url: M3U8播放列表URL
            output_path: 输出路径，默认使用C:\\index
            output_filename: 输出文件名，默认使用时间戳格式
            progress_callback: 进度回调函数
            
        Returns:
            包含结果的字典，包含 temp_subdir 字段用于后续清理
        """
        # 使用默认输出路径
        if not output_path:
            output_path = self.downloader.default_download_path
        
        # 确保输出目录存在
        if not self.downloader.ensure_download_directory(output_path):
            return {
                'success': False,
                'error': '输出目录创建失败'
            }
        
        # 生成输出文件名
        if not output_filename:
            output_filename = self.downloader.generate_filename(m3u8_url)
        
        # 完整输出路径
        output_file = os.path.join(output_path, output_filename)
        
        # 检查是否是恢复任务（有保存的临时目录）
        temp_subdir = None
        is_resume = False  # 是否是断点续传
        if self.state_manager and self.current_task_id:
            # 获取任务信息
            task_info = self.state_manager.get_task(self.current_task_id)
            if task_info:
                saved_temp_dir = task_info.get('temp_dir')
                if saved_temp_dir and os.path.exists(saved_temp_dir):
                    # 使用保存的临时目录（断点续传）
                    temp_subdir = saved_temp_dir
                    is_resume = True
                    print(f"[断点续传] 使用已存在的临时目录: {temp_subdir}")
                else:
                    # 创建新的临时目录
                    temp_subdir = self.create_temp_subdir()
                    print(f"[新建任务] 创建新的临时目录: {temp_subdir}")
                    # 保存临时目录路径到状态管理器
                    self.state_manager.update_task_info(self.current_task_id, {'temp_dir': temp_subdir})
            else:
                # 任务信息不存在，创建新的临时目录
                temp_subdir = self.create_temp_subdir()
                print(f"[新建任务] 创建新的临时目录: {temp_subdir}")
        else:
            # 创建新的临时目录
            temp_subdir = self.create_temp_subdir()
            print(f"[新建任务] 创建新的临时目录: {temp_subdir}")
        
        try:
            # 1. 解析M3U8
            print(f"正在解析M3U8播放列表: {m3u8_url}")
            ts_urls, encryption_info = self.parse_m3u8(m3u8_url)
            
            if not ts_urls:
                return {
                    'success': False,
                    'error': '未找到TS分片',
                    'temp_subdir': temp_subdir
                }
            
            self.log(f"[M3U8解析] 找到 {len(ts_urls)} 个TS分片")
            if encryption_info['method'] != 'NONE':
                self.log(f"[加密检测] 视频已加密")
                self.log(f"[加密检测] 加密方法: {encryption_info['method']}")
                if encryption_info['key']:
                    self.log(f"[加密检测] 已获取解密密钥")
                    if 'getmovie' in m3u8_url.lower():
                        self.log(f"[加密检测] 解密方式: 使用Resource目录中的getmovie.key文件")
                    else:
                        self.log(f"[加密检测] 解密方式: 使用网络下载的密钥")
                else:
                    self.log(f"[加密检测] 未获取到解密密钥，解密可能失败", "WARNING")
            else:
                self.log(f"[加密检测] 视频未加密，无需解密")
                self.log(f"[加密检测] 解密方式: 无需解密")
            
            # 2. 下载TS分片到临时目录
            print(f"开始下载TS分片到临时目录: {temp_subdir}")
            downloaded_segments = self.download_ts_segments(
                ts_urls, 
                temp_subdir,
                encryption_info,
                progress_callback
            )
            
            if not downloaded_segments:
                return {
                    'success': False,
                    'error': 'TS分片下载失败',
                    'temp_subdir': temp_subdir
                }
            
            if len(downloaded_segments) != len(ts_urls):
                print(f"警告: 只下载了 {len(downloaded_segments)} 个分片，共 {len(ts_urls)} 个")
            
            # 3. 合并TS分片
            print(f"开始合并TS分片为MP4文件...")
            merge_success = self.merge_ts_segments(
                downloaded_segments, 
                output_file
            )
            
            if not merge_success:
                return {
                    'success': False,
                    'error': 'TS分片合并失败',
                    'temp_subdir': temp_subdir  # 保留临时目录供下次继续
                }
            
            print(f"合并成功: {output_file}")
            
            # 4. 清理临时子目录（只有合并成功才清理）
            print(f"清理临时目录: {temp_subdir}")
            self.delete_temp_subdir(temp_subdir)
            
            # 清理key文件（如果存在）
            current_dir = os.path.dirname(os.path.abspath(__file__))
            resource_dir = os.path.join(current_dir, '..', 'Resources')
            key_file_path = os.path.join(resource_dir, 'getmovie.key')
            
            if os.path.exists(key_file_path):
                try:
                    os.remove(key_file_path)
                    print(f"已删除resource目录中的key文件: {key_file_path}")
                except Exception as e:
                    print(f"删除key文件失败: {e}")
            
            # 5. 返回结果
            return {
                'success': True,
                'file_path': output_file,
                'filename': output_filename,
                'segments_count': len(downloaded_segments),
                'original_segments_count': len(ts_urls),
                'temp_subdir': None  # 已清理
            }
        except Exception as e:
            print(f"处理失败: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e),
                'temp_subdir': temp_subdir  # 保留临时目录供用户处理
            }
        finally:
            # 确保ffmpeg进程被终止
            if self.ffmpeg_process:
                try:
                    self.ffmpeg_process.terminate()
                    self.ffmpeg_process.wait(timeout=5)
                except:
                    pass
                self.ffmpeg_process = None
            # 重置停止标志
            self.should_stop = False
    
    def merge_existing_ts_files(self, 
                              subdir: str, 
                              output_file: str) -> bool:
        """
        合并已存在的TS文件
        用于处理之前下载但未合并的文件
        """
        try:
            print(f"开始合并已存在的TS文件")
            print(f"子目录名称: {subdir}")
            print(f"输出文件: {output_file}")
            
            # 获取子目录中的所有TS文件
            ts_files = self.get_ts_files_in_subdir(subdir)
            
            if not ts_files:
                print(f"错误: 子目录 {subdir} 中没有TS文件")
                return False
            
            print(f"找到 {len(ts_files)} 个TS文件，开始合并...")
            
            # 合并TS文件
            merge_success = self.merge_ts_segments(ts_files, output_file)
            
            if merge_success:
                # 合并成功，清理临时子目录
                print(f"合并成功，清理临时目录: {subdir}")
                self.delete_temp_subdir(subdir)
                return True
            else:
                return False
                
        except Exception as e:
            print(f"合并已存在的TS文件失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def is_m3u8_url(self, url: str) -> bool:
        """
        检查URL是否为M3U8播放列表
        """
        url_lower = url.lower()
        # 检查是否以 '.m3u8' 结尾
        if url_lower.endswith('.m3u8'):
            return True
        # 检查URL中是否包含 'm3u8' 关键词（处理带参数的M3U8 URL）
        if 'm3u8' in url_lower:
            return True
        return False
    
    def get_segment_count(self, m3u8_url: str) -> int:
        """
        获取M3U8中的分片数量
        """
        ts_urls = self.parse_m3u8(m3u8_url)
        return len(ts_urls)
