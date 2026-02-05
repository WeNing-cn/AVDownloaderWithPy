import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from typing import List, Dict, Optional, Set

class VideoDetector:
    def __init__(self):
        # 视频文件扩展名
        self.video_extensions = {
            'mp4', 'avi', 'mov', 'wmv', 'flv', 'mkv', 'webm', 
            'm3u8', 'ts', 'm4v', 'f4v'
        }
        
        # 视频内容类型
        self.video_content_types = {
            'video/mp4', 'video/avi', 'video/mov', 'video/wmv', 
            'video/flv', 'video/mkv', 'video/webm', 'application/x-mpegURL',
            'application/vnd.apple.mpegurl', 'video/MP2T'
        }
        
        # 视频链接正则表达式（更精确，避免匹配脚本文件）
        self.video_url_pattern = re.compile(r'https?://[^\s"\']+\.(mp4|avi|mov|wmv|flv|mkv|webm|m3u8|ts|m4v|f4v)(?!\.js)(?!\.css)(?!\.html)(?!\.php)', re.IGNORECASE)
        
        # M3U8播放列表正则表达式（更精确，避免匹配脚本文件）
        self.m3u8_pattern = re.compile(r'https?://[^\s"\']+\.m3u8(?!\.js)(?!\.css)(?!\.html)(?!\.php)', re.IGNORECASE)
    
    def detect_from_html(self, html: str, base_url: str) -> List[Dict[str, str]]:
        """
        从HTML内容中提取视频资源（只提取m3u8和key关键词）
        """
        videos = []
        seen_urls = set()
        
        try:
            soup = BeautifulSoup(html, 'lxml')
            
            # 提取video标签（只保留包含m3u8或key的链接）
            for video_tag in soup.find_all('video'):
                # 提取src属性
                if video_tag.get('src'):
                    video_url = self._normalize_url(video_tag['src'], base_url)
                    # 只保留包含m3u8或key的链接
                    if video_url and video_url not in seen_urls and ('m3u8' in video_url.lower() or 'key' in video_url.lower()):
                        seen_urls.add(video_url)
                        videos.append({
                            'url': video_url,
                            'type': 'video_tag',
                            'source': 'html'
                        })
                
                # 提取source标签（只保留包含m3u8或key的链接）
                for source_tag in video_tag.find_all('source'):
                    if source_tag.get('src'):
                        video_url = self._normalize_url(source_tag['src'], base_url)
                        # 只保留包含m3u8或key的链接
                        if video_url and video_url not in seen_urls and ('m3u8' in video_url.lower() or 'key' in video_url.lower()):
                            seen_urls.add(video_url)
                            videos.append({
                                'url': video_url,
                                'type': 'source_tag',
                                'source': 'html'
                            })
            
            # 提取iframe标签（只保留包含m3u8或key的链接）
            for iframe_tag in soup.find_all('iframe'):
                if iframe_tag.get('src'):
                    iframe_url = self._normalize_url(iframe_tag['src'], base_url)
                    # 只保留包含m3u8或key的链接
                    if iframe_url and iframe_url not in seen_urls and ('m3u8' in iframe_url.lower() or 'key' in iframe_url.lower()):
                        seen_urls.add(iframe_url)
                        videos.append({
                            'url': iframe_url,
                            'type': 'iframe',
                            'source': 'html'
                        })
            
            # 使用正则表达式提取包含m3u8或key的链接
            m3u8_pattern = re.compile(r'https?://[^\s"\']+[\w\-./?%&=]*m3u8[\w\-./?%&=]*', re.IGNORECASE)
            for match in m3u8_pattern.finditer(html):
                video_url = match.group(0)
                if video_url and video_url not in seen_urls:
                    seen_urls.add(video_url)
                    videos.append({
                        'url': video_url,
                        'type': 'regex',
                        'source': 'html'
                    })
            
            # 使用正则表达式提取包含key的链接
            key_pattern = re.compile(r'https?://[^\s"\']+[\w\-./?%&=]*key[\w\-./?%&=]*', re.IGNORECASE)
            for match in key_pattern.finditer(html):
                video_url = match.group(0)
                if video_url and video_url not in seen_urls:
                    seen_urls.add(video_url)
                    videos.append({
                        'url': video_url,
                        'type': 'regex',
                        'source': 'html'
                    })
            
        except Exception as e:
            print(f"从HTML提取视频失败: {e}")
        
        return videos
    
    def detect_from_network(self, network_requests: List[Dict], base_url: str) -> List[Dict[str, str]]:
        """
        从网络请求中提取视频资源（只提取m3u8和key关键词）
        """
        videos = []
        seen_urls = set()
        
        try:
            for request in network_requests:
                url = request.get('url', '')
                headers = request.get('headers', {})
                
                # 只提取包含m3u8或key的URL
                if url and url not in seen_urls and ('m3u8' in url.lower() or 'key' in url.lower()):
                    seen_urls.add(url)
                    videos.append({
                        'url': url,
                        'type': 'network',
                        'source': 'network'
                    })
        except Exception as e:
            print(f"从网络请求提取视频失败: {e}")
        
        return videos
    
    def detect_m3u8_playlists(self, videos: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        从视频资源中识别M3U8播放列表（只提取m3u8和key关键词）
        """
        m3u8_playlists = []
        
        for video in videos:
            url = video.get('url', '')
            # 只保留包含m3u8的URL
            if 'm3u8' in url.lower():
                m3u8_playlists.append({
                    **video,
                    'is_playlist': True
                })
        
        return m3u8_playlists
    
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
    
    def get_unique_videos(self, videos: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        去重视频资源
        """
        seen_urls = set()
        unique_videos = []
        
        for video in videos:
            url = video.get('url', '')
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_videos.append(video)
        
        return unique_videos
    
    def rank_videos(self, videos: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        对视频资源进行排序（只提取m3u8和key关键词）
        优先级：
        1. M3U8播放列表
        2. key文件
        """
        def video_priority(video):
            url = video.get('url', '')
            # M3U8播放列表优先级最高
            if 'm3u8' in url.lower():
                return 0
            # key文件次之
            elif 'key' in url.lower():
                return 1
            # 其他类型最后
            else:
                return 2
        
        return sorted(videos, key=video_priority)
    
    def detect_all_videos(self, html: str, network_requests: List[Dict], base_url: str) -> List[Dict[str, str]]:
        """
        综合检测所有视频资源
        """
        # 从HTML中提取
        html_videos = self.detect_from_html(html, base_url)
        
        # 从网络请求中提取
        network_videos = self.detect_from_network(network_requests, base_url)
        
        # 合并所有视频资源
        all_videos = html_videos + network_videos
        
        # 去重
        unique_videos = self.get_unique_videos(all_videos)
        
        # 排序
        ranked_videos = self.rank_videos(unique_videos)
        
        return ranked_videos
    
    def validate_video_url(self, url: str) -> bool:
        """
        验证视频URL是否有效
        """
        try:
            parsed = urlparse(url)
            return parsed.scheme in ['http', 'https'] and parsed.netloc
        except Exception:
            return False
