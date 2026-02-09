"""
文件名：ts_merger_mobile.py
功能：移动端TS分片合并模块（适配Android，纯Python实现）
创建时间：2026-02-09
"""

import os
import re
import requests
import tempfile
import shutil
from urllib.parse import urljoin, urlparse
from typing import List, Dict, Optional, Callable
from datetime import datetime

try:
    from Crypto.Cipher import AES
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    print("警告: 未安装pycryptodome库，无法处理加密的M3U8流")


class TSMerger:
    """TS分片合并器 - 移动端适配版（不使用ffmpeg）"""
    
    def __init__(self, log_callback=None, download_path=None):
        self.downloader = None  # 不使用VideoDownloader，直接使用requests
        self.max_workers = 4  # 移动端减少并发数
        self.chunk_size = 1024 * 256  # 256KB
        self.timeout = 30
        
        # Android下载路径
        if download_path:
            self.download_path = download_path
        elif os.path.exists('/sdcard'):
            self.download_path = '/sdcard/Download/AVDownloader'
        else:
            self.download_path = os.path.join(
                os.path.expanduser('~'), 'Downloads', 'AVDownloader'
            )
        
        # 临时目录
        self.temp_dir = os.path.join(self.download_path, 'temp')
        os.makedirs(self.temp_dir, exist_ok=True)
        
        self.should_stop = False
        self.log_callback = log_callback
        self.session = requests.Session()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 10; Mobile) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.120 Mobile Safari/537.36',
            'Accept': '*/*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
            'Connection': 'keep-alive'
        }
    
    def log(self, message, level="INFO"):
        """输出日志"""
        if self.log_callback:
            self.log_callback(message, level)
        else:
            print(f"[{level}] {message}")
    
    def stop(self):
        """停止下载"""
        self.should_stop = True
        try:
            self.session.close()
        except:
            pass
    
    def parse_m3u8(self, m3u8_url: str) -> Dict:
        """
        解析M3U8播放列表
        
        Returns:
            包含TS分片信息和密钥信息的字典
        """
        try:
            self.log(f"正在解析M3U8: {m3u8_url}")
            
            response = self.session.get(m3u8_url, headers=self.headers, timeout=self.timeout)
            response.raise_for_status()
            
            content = response.text
            base_url = m3u8_url.rsplit('/', 1)[0] + '/'
            
            # 检查是否是主播放列表（包含多个码率）
            if '#EXT-X-STREAM-INF' in content:
                self.log("检测到主播放列表，选择第一个流")
                # 提取第一个子播放列表
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if '#EXT-X-STREAM-INF' in line and i + 1 < len(lines):
                        sub_playlist = lines[i + 1].strip()
                        if sub_playlist and not sub_playlist.startswith('#'):
                            # 构建完整URL
                            if sub_playlist.startswith('http'):
                                return self.parse_m3u8(sub_playlist)
                            else:
                                return self.parse_m3u8(urljoin(base_url, sub_playlist))
            
            # 解析TS分片
            segments = []
            key_url = None
            key_iv = None
            lines = content.split('\n')
            
            i = 0
            while i < len(lines):
                line = lines[i].strip()
                
                # 提取密钥信息
                if line.startswith('#EXT-X-KEY'):
                    # 解析METHOD和URI
                    method_match = re.search(r'METHOD=([^,]+)', line)
                    uri_match = re.search(r'URI="([^"]+)"', line)
                    iv_match = re.search(r'IV=0x([0-9a-fA-F]+)', line)
                    
                    if method_match:
                        method = method_match.group(1)
                        if method != 'NONE' and uri_match:
                            key_url = uri_match.group(1)
                            if not key_url.startswith('http'):
                                key_url = urljoin(base_url, key_url)
                    
                    if iv_match:
                        key_iv = bytes.fromhex(iv_match.group(1))
                
                # 提取TS分片URL
                elif line and not line.startswith('#'):
                    segment_url = line
                    if not segment_url.startswith('http'):
                        segment_url = urljoin(base_url, segment_url)
                    segments.append({
                        'url': segment_url,
                        'key_url': key_url,
                        'key_iv': key_iv
                    })
                    # 重置密钥（每个分片可能有不同的密钥）
                    key_url = None
                    key_iv = None
                
                i += 1
            
            self.log(f"解析完成，共{len(segments)}个分片")
            
            return {
                'success': True,
                'segments': segments,
                'base_url': base_url
            }
            
        except Exception as e:
            self.log(f"解析M3U8失败: {str(e)}", "ERROR")
            return {
                'success': False,
                'error': str(e)
            }
    
    def download_segment(self, segment: Dict, index: int, total: int, temp_dir: str) -> Dict:
        """
        下载单个TS分片
        
        Args:
            segment: 分片信息
            index: 分片索引
            total: 总分片数
            temp_dir: 临时目录
            
        Returns:
            包含下载结果的字典
        """
        try:
            if self.should_stop:
                return {'success': False, 'error': '下载已取消'}
            
            segment_url = segment['url']
            segment_file = os.path.join(temp_dir, f"segment_{index:06d}.ts")
            
            # 下载分片
            response = self.session.get(segment_url, headers=self.headers, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.content
            
            # 解密（如果需要）
            if segment.get('key_url') and CRYPTO_AVAILABLE:
                key_url = segment['key_url']
                key_response = self.session.get(key_url, headers=self.headers, timeout=self.timeout)
                key = key_response.content
                
                iv = segment.get('key_iv')
                if iv is None:
                    # 使用序列号作为IV
                    iv = index.to_bytes(16, 'big')
                
                cipher = AES.new(key, AES.MODE_CBC, iv)
                data = cipher.decrypt(data)
                # 去除PKCS7填充
                padding_len = data[-1]
                data = data[:-padding_len]
            
            # 保存分片
            with open(segment_file, 'wb') as f:
                f.write(data)
            
            return {
                'success': True,
                'file': segment_file,
                'index': index
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'index': index
            }
    
    def merge_segments(self, segment_files: List[str], output_file: str) -> Dict:
        """
        合并TS分片为MP4文件（纯Python实现，不使用ffmpeg）
        
        Args:
            segment_files: TS分片文件列表
            output_file: 输出文件路径
            
        Returns:
            包含合并结果的字典
        """
        try:
            self.log(f"开始合并{len(segment_files)}个分片...")
            
            # 按索引排序
            segment_files.sort()
            
            # 直接合并TS文件
            # 注意：纯TS合并可能需要在播放器中才能正常播放
            # 如果需要真正的MP4转换，需要使用ffmpeg或其他工具
            with open(output_file, 'wb') as outfile:
                for i, segment_file in enumerate(segment_files):
                    if self.should_stop:
                        return {'success': False, 'error': '合并已取消'}
                    
                    with open(segment_file, 'rb') as infile:
                        shutil.copyfileobj(infile, outfile)
                    
                    # 每10个分片报告一次进度
                    if (i + 1) % 10 == 0 or i == len(segment_files) - 1:
                        progress = ((i + 1) / len(segment_files)) * 100
                        self.log(f"合并进度: {progress:.1f}%")
            
            self.log(f"合并完成: {output_file}")
            return {
                'success': True,
                'output_file': output_file
            }
            
        except Exception as e:
            self.log(f"合并失败: {str(e)}", "ERROR")
            return {
                'success': False,
                'error': str(e)
            }
    
    def download_and_merge(self, 
                          m3u8_url: str, 
                          output_file: str,
                          progress_callback: Optional[Callable] = None) -> Dict:
        """
        下载并合并M3U8视频
        
        Args:
            m3u8_url: M3U8播放列表URL
            output_file: 输出文件路径
            progress_callback: 进度回调函数
            
        Returns:
            包含下载结果的字典
        """
        try:
            self.should_stop = False
            
            # 解析M3U8
            parse_result = self.parse_m3u8(m3u8_url)
            if not parse_result['success']:
                return parse_result
            
            segments = parse_result['segments']
            total_segments = len(segments)
            
            if total_segments == 0:
                return {'success': False, 'error': '没有可下载的分片'}
            
            self.log(f"开始下载{total_segments}个分片...")
            
            # 创建临时目录
            temp_dir = os.path.join(self.temp_dir, datetime.now().strftime('%Y%m%d_%H%M%S'))
            os.makedirs(temp_dir, exist_ok=True)
            
            # 下载所有分片（串行下载，移动端更稳定）
            segment_files = []
            for i, segment in enumerate(segments):
                if self.should_stop:
                    return {'success': False, 'error': '下载已取消'}
                
                result = self.download_segment(segment, i, total_segments, temp_dir)
                
                if result['success']:
                    segment_files.append(result['file'])
                    progress = ((i + 1) / total_segments) * 100
                    self.log(f"下载进度: {progress:.1f}% ({i+1}/{total_segments})")
                    if progress_callback:
                        progress_callback(progress, i + 1, total_segments)
                else:
                    self.log(f"分片{i+1}下载失败: {result.get('error')}", "ERROR")
                    # 继续下载其他分片
            
            if len(segment_files) == 0:
                return {'success': False, 'error': '所有分片下载失败'}
            
            if len(segment_files) < total_segments:
                self.log(f"警告: 只有{len(segment_files)}/{total_segments}个分片下载成功", "WARNING")
            
            # 更新进度为合并阶段
            if progress_callback:
                progress_callback(100, total_segments, total_segments)
            
            # 合并分片
            merge_result = self.merge_segments(segment_files, output_file)
            
            # 清理临时文件
            try:
                shutil.rmtree(temp_dir)
                self.log("临时文件已清理")
            except Exception as e:
                self.log(f"清理临时文件失败: {e}", "WARNING")
            
            if merge_result['success']:
                return {
                    'success': True,
                    'filename': os.path.basename(output_file),
                    'path': output_file,
                    'segments_downloaded': len(segment_files),
                    'total_segments': total_segments
                }
            else:
                return merge_result
                
        except Exception as e:
            self.log(f"下载合并过程出错: {str(e)}", "ERROR")
            return {
                'success': False,
                'error': str(e)
            }
