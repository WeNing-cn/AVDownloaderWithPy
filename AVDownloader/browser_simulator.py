import requests
import re
import time
from typing import List, Dict, Optional, Any
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, WebDriverException

class BrowserSimulator:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0'
        })
        self.video_resources = []
        self.network_requests = []
        self.page_content = ''
        self.driver = None
        # 视频文件扩展名
        self.video_extensions = {
            'mp4', 'avi', 'mov', 'wmv', 'flv', 'mkv', 'webm', 
            'm3u8', 'ts', 'm4v', 'f4v'
        }
        # 视频链接正则表达式（更精确，避免匹配脚本文件）
        self.video_url_pattern = re.compile(r'https?://[^\s"\']+\.(mp4|avi|mov|wmv|flv|mkv|webm|m3u8|ts|m4v|f4v)(?!\.js)(?!\.css)(?!\.html)(?!\.php)', re.IGNORECASE)
    
    def init_browser(self, headless: bool = True) -> None:
        """
        初始化浏览器模拟器
        """
        try:
            chrome_options = Options()
            if headless:
                chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
            
            # 启用性能日志以捕获网络请求
            chrome_options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
            
            self.driver = webdriver.Chrome(options=chrome_options)
            print("浏览器初始化成功")
        except Exception as e:
            print(f"浏览器初始化失败: {e}")
            raise
    
    def load_page(self, url: str, timeout: int = 60) -> bool:
        """
        加载网页
        """
        try:
            if not self.driver:
                self.init_browser()
            
            print(f"\n=== 开始加载页面 ===")
            print(f"URL: {url}")
            
            # 使用线程加载页面，避免长时间阻塞
            import threading
            page_loaded = False
            load_error = None
            
            def load_page_thread():
                nonlocal page_loaded, load_error
                try:
                    # 使用Selenium加载页面
                    self.driver.set_page_load_timeout(timeout)
                    self.driver.get(url)
                    
                    # 等待页面加载完成
                    try:
                        WebDriverWait(self.driver, timeout).until(
                            EC.presence_of_element_located((By.TAG_NAME, "body"))
                        )
                        print("页面主体加载完成")
                    except TimeoutException:
                        print("页面加载超时，继续处理")
                    
                    # 等待JavaScript执行完成（减少等待时间）
                    time.sleep(1)
                    
                    # 获取页面内容
                    self.page_content = self.driver.page_source
                    print(f"页面内容大小: {len(self.page_content)} 字节")
                    
                    # 记录主页面请求
                    self.network_requests.append({
                        'url': url,
                        'method': 'GET',
                        'headers': {'User-Agent': 'Selenium WebDriver'},
                        'timestamp': 0
                    })
                    
                    page_loaded = True
                except Exception as e:
                    load_error = e
                    print(f"页面加载线程异常: {e}")
            
            # 启动加载线程
            load_thread = threading.Thread(target=load_page_thread)
            load_thread.daemon = True
            load_thread.start()
            
            # 等待线程完成，最多等待timeout秒
            load_thread.join(timeout=timeout)
            
            if not page_loaded:
                if load_error:
                    print(f"页面加载失败: {load_error}")
                    return False
                else:
                    print("页面加载超时，强制继续")
                    # 即使超时，也尝试获取页面内容
                    try:
                        self.page_content = self.driver.page_source
                        print(f"超时后获取到页面内容大小: {len(self.page_content)} 字节")
                    except Exception as e:
                        print(f"超时后获取页面内容失败: {e}")
                        self.page_content = ""
            
            # 捕获网络请求（添加超时处理）
            try:
                import threading
                
                # 创建一个线程来执行网络请求捕获
                def capture_network_requests_thread():
                    try:
                        self._capture_network_requests()
                    except Exception as e:
                        print(f"捕获网络请求失败: {e}")
                
                # 启动线程
                capture_thread = threading.Thread(target=capture_network_requests_thread)
                capture_thread.daemon = True
                capture_thread.start()
                
                # 等待线程完成，最多等待10秒
                capture_thread.join(timeout=10)
                
            except Exception as e:
                print(f"启动网络请求捕获线程失败: {e}")
            
            # 提取视频资源（添加超时处理）
            try:
                import threading
                
                # 创建一个线程来执行视频资源提取
                def extract_video_resources_thread():
                    try:
                        self._extract_video_resources(url)
                    except Exception as e:
                        print(f"提取视频资源失败: {e}")
                
                # 启动线程
                extract_thread = threading.Thread(target=extract_video_resources_thread)
                extract_thread.daemon = True
                extract_thread.start()
                
                # 等待线程完成，最多等待10秒
                extract_thread.join(timeout=10)
                
            except Exception as e:
                print(f"启动视频资源提取线程失败: {e}")
            
            print(f"=== 页面加载完成 ===")
            return True
            
        except Exception as e:
            print(f"加载页面失败: {e}")
            # 确保浏览器不会因为异常而卡死
            try:
                if self.driver:
                    self.driver.quit()
                    self.driver = None
            except:
                pass
            return False
    
    def _capture_network_requests(self) -> None:
        """
        捕获网络请求
        """
        try:
            print(f"\n=== 开始捕获网络请求 ===")
            
            # 获取性能日志
            logs = self.driver.get_log('performance')
            print(f"获取到 {len(logs)} 条性能日志")
            
            captured_requests = set()
            # 使用集合跟踪已添加的视频URL，提高性能
            video_urls_set = set(v['url'] for v in self.video_resources)
            
            # 计数器
            video_count = 0
            resource_count = 0
            
            for entry in logs:
                try:
                    message = entry.get('message', '{}')
                    import json
                    data = json.loads(message)
                    
                    # 检查网络请求
                    if 'Network' in data.get('message', {}).get('method', ''):
                        method = data['message']['method']
                        
                        # 捕获请求发送
                        if method == 'Network.requestWillBeSent':
                            request_data = data['message']['params']['request']
                            request_url = request_data.get('url', '')
                            
                            if request_url and request_url not in captured_requests:
                                captured_requests.add(request_url)
                                resource_count += 1
                                
                                # 检查是否为视频资源
                                if self._is_video_url(request_url):
                                    video_count += 1
                                    # 只打印视频请求，减少控制台输出
                                    print(f"  发现视频请求: {request_url}")
                                    
                                    if request_url not in video_urls_set:
                                        video_urls_set.add(request_url)
                                        self.video_resources.append({
                                            'url': request_url,
                                            'type': 'network',
                                            'source': 'network',
                                            'content_type': 'video/mp4',
                                            'status': 200,
                                            'timestamp': 0
                                        })
                                
                                # 记录网络请求
                                self.network_requests.append({
                                    'url': request_url,
                                    'method': request_data.get('method', 'GET'),
                                    'headers': request_data.get('headers', {}),
                                    'timestamp': 0
                                })
                
                except Exception as e:
                    continue
            
            print(f"捕获到 {len(captured_requests)} 个唯一请求")
            print(f"识别出 {video_count} 个视频资源")
            print(f"=== 网络请求捕获完成 ===")
            
        except Exception as e:
            print(f"捕获网络请求失败: {e}")
    
    def _is_video_url(self, url: str) -> bool:
        """
        检查URL是否为视频资源（检查m3u8、key和getmovie关键词）
        """
        url_lower = url.lower()
        
        # 过滤掉明显不是视频的资源
        if any(ext in url_lower for ext in ['.js', '.css', '.html', '.php', '.png', '.jpg', '.jpeg', '.gif', '.ico', '.woff', '.woff2', '.ttf', '.eot']):
            return False
        
        # 过滤掉常见的非视频域名
        if any(domain in url_lower for domain in ['cloudflareinsights.com', 'bdimg.com', 'google-analytics.com', 'googletagmanager.com']):
            return False
        
        # 检查m3u8、key和getmovie关键词
        if 'm3u8' in url_lower or 'key' in url_lower or 'getmovie' in url_lower:
            return True
        
        return False
    
    def _extract_video_resources(self, base_url: str) -> None:
        """
        从页面内容中提取视频资源（只提取m3u8和key关键词）
        """
        try:
            soup = BeautifulSoup(self.page_content, 'html.parser')
            
            # 提取video标签（只保留包含m3u8、key或getmovie的链接）
            for video_tag in soup.find_all('video'):
                if video_tag.get('src'):
                    video_url = video_tag['src']
                    if not video_url.startswith('http'):
                        from urllib.parse import urljoin
                        video_url = urljoin(base_url, video_url)
                    
                    # 只保留包含m3u8、key或getmovie的链接
                    if 'm3u8' in video_url.lower() or 'key' in video_url.lower() or 'getmovie' in video_url.lower():
                        if not any(v['url'] == video_url for v in self.video_resources):
                            self.video_resources.append({
                                'url': video_url,
                                'type': 'video_tag',
                                'source': 'html',
                                'content_type': 'video/mp4',
                                'status': 200,
                                'timestamp': 0
                            })
                            print(f"  从video标签提取: {video_url}")
                
                # 提取source标签（只保留包含m3u8、key或getmovie的链接）
                for source_tag in video_tag.find_all('source'):
                    if source_tag.get('src'):
                        video_url = source_tag['src']
                        if not video_url.startswith('http'):
                            from urllib.parse import urljoin
                            video_url = urljoin(base_url, video_url)
                        
                        # 只保留包含m3u8、key或getmovie的链接
                        if 'm3u8' in video_url.lower() or 'key' in video_url.lower() or 'getmovie' in video_url.lower():
                            if not any(v['url'] == video_url for v in self.video_resources):
                                self.video_resources.append({
                                    'url': video_url,
                                    'type': 'source_tag',
                                    'source': 'html',
                                    'content_type': source_tag.get('type', 'video/mp4'),
                                    'status': 200,
                                    'timestamp': 0
                                })
                                print(f"  从source标签提取: {video_url}")
            
            # 提取iframe标签（只保留包含m3u8、key或getmovie的链接）
            for iframe_tag in soup.find_all('iframe'):
                if iframe_tag.get('src'):
                    iframe_url = iframe_tag['src']
                    if not iframe_url.startswith('http'):
                        from urllib.parse import urljoin
                        iframe_url = urljoin(base_url, iframe_url)
                    
                    # 过滤掉明显不是视频的iframe（如脚本文件）
                    if any(ext in iframe_url.lower() for ext in ['.js', '.css', '.html', '.php']):
                        continue
                    
                    # 只保留包含m3u8、key或getmovie的iframe
                    if 'm3u8' in iframe_url.lower() or 'key' in iframe_url.lower() or 'getmovie' in iframe_url.lower():
                        if not any(v['url'] == iframe_url for v in self.video_resources):
                            self.video_resources.append({
                                'url': iframe_url,
                                'type': 'iframe',
                                'source': 'html',
                                'content_type': 'text/html',
                                'status': 200,
                                'timestamp': 0
                            })
                            print(f"  从iframe标签提取: {iframe_url}")
            
            # 从JavaScript中提取视频链接
            self._extract_video_from_js(base_url)
            
            # 过滤非视频资源
            self._filter_non_video_resources()
            
            # 去重视频资源
            self._deduplicate_video_resources()
            
        except Exception as e:
            print(f"提取视频资源失败: {e}")
    
    def _extract_video_from_js(self, base_url: str) -> None:
        """
        从JavaScript代码中提取视频链接（提取m3u8、key和getmovie关键词）
        """
        try:
            # 提取可能的M3U8播放列表
            m3u8_pattern = re.compile(r'https?://[^\s"\']+[\w\-./?%&=]*m3u8[\w\-./?%&=]*', re.IGNORECASE)
            for match in m3u8_pattern.finditer(self.page_content):
                m3u8_url = match.group(0)
                if not any(v['url'] == m3u8_url for v in self.video_resources):
                    self.video_resources.append({
                        'url': m3u8_url,
                        'type': 'regex',
                        'source': 'html',
                        'content_type': 'application/x-mpegURL',
                        'status': 200,
                        'timestamp': 0
                    })
                    print(f"  从JavaScript提取M3U8链接: {m3u8_url}")
            
            # 提取可能的key文件
            key_pattern = re.compile(r'https?://[^\s"\']+[\w\-./?%&=]*key[\w\-./?%&=]*', re.IGNORECASE)
            for match in key_pattern.finditer(self.page_content):
                key_url = match.group(0)
                if not any(v['url'] == key_url for v in self.video_resources):
                    self.video_resources.append({
                        'url': key_url,
                        'type': 'regex',
                        'source': 'html',
                        'content_type': 'application/octet-stream',
                        'status': 200,
                        'timestamp': 0
                    })
                    print(f"  从JavaScript提取key链接: {key_url}")
            
            # 提取可能的getmovie链接
            getmovie_pattern = re.compile(r'https?://[^\s"\']+[\w\-./?%&=]*getmovie[\w\-./?%&=]*', re.IGNORECASE)
            for match in getmovie_pattern.finditer(self.page_content):
                getmovie_url = match.group(0)
                if not any(v['url'] == getmovie_url for v in self.video_resources):
                    self.video_resources.append({
                        'url': getmovie_url,
                        'type': 'regex',
                        'source': 'html',
                        'content_type': 'application/json',
                        'status': 200,
                        'timestamp': 0
                    })
                    print(f"  从JavaScript提取getmovie链接: {getmovie_url}")
            
            # 提取可能的JSON格式的getmovie数据
            json_pattern = re.compile(r'\{[^\}]*getmovie[^\}]*\}', re.IGNORECASE)
            for match in json_pattern.finditer(self.page_content):
                try:
                    json_str = match.group(0)
                    import json
                    json_data = json.loads(json_str)
                    if 'm3u8' in json_data:
                        m3u8_path = json_data['m3u8']
                        if not m3u8_path.startswith('http'):
                            m3u8_url = urljoin(base_url, m3u8_path)
                        else:
                            m3u8_url = m3u8_path
                        if not any(v['url'] == m3u8_url for v in self.video_resources):
                            self.video_resources.append({
                                'url': m3u8_url,
                                'type': 'json',
                                'source': 'html',
                                'content_type': 'application/x-mpegURL',
                                'status': 200,
                                'timestamp': 0,
                                'getmovie_data': json_data
                            })
                            print(f"  从JSON提取M3U8链接: {m3u8_url}")
                except Exception as e:
                    print(f"  解析JSON失败: {e}")
                    
        except Exception as e:
            print(f"从JavaScript提取视频链接失败: {e}")
    
    def _filter_non_video_resources(self) -> None:
        """
        过滤非视频资源
        """
        filtered_resources = []
        
        for resource in self.video_resources:
            url = resource.get('url', '')
            
            # 过滤掉明显不是视频的资源
            if any(ext in url.lower() for ext in ['.js', '.css', '.html', '.php', '.png', '.jpg', '.jpeg', '.gif', '.ico']):
                continue
            
            # 过滤掉常见的非视频域名
            if any(domain in url.lower() for domain in ['cloudflareinsights.com', 'bdimg.com', 'google-analytics.com', 'googletagmanager.com']):
                continue
            
            # 只保留包含m3u8、key和getmovie关键词的文件
            url_lower = url.lower()
            if 'm3u8' in url_lower or 'key' in url_lower or 'getmovie' in url_lower:
                filtered_resources.append(resource)
        
        self.video_resources = filtered_resources
    
    def _deduplicate_video_resources(self) -> None:
        """
        去重视频资源
        """
        seen_urls = set()
        unique_resources = []
        
        for resource in self.video_resources:
            url = resource.get('url', '')
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_resources.append(resource)
        
        self.video_resources = unique_resources
    
    def get_page_content(self) -> str:
        """
        获取页面内容
        """
        return self.page_content
    
    def get_video_resources(self) -> List[Dict[str, Any]]:
        """
        获取捕获的视频资源
        """
        return self.video_resources
    
    def get_network_requests(self) -> List[Dict[str, Any]]:
        """
        获取网络请求记录
        """
        return self.network_requests
    
    def execute_script(self, script: str) -> Any:
        """
        执行JavaScript脚本
        """
        if self.driver:
            return self.driver.execute_script(script)
        return None
    
    def close(self) -> None:
        """
        关闭浏览器模拟器
        """
        if self.driver:
            try:
                self.driver.quit()
                print("浏览器已关闭")
            except Exception as e:
                print(f"关闭浏览器失败: {e}")
            finally:
                self.driver = None
    
    def __del__(self) -> None:
        """
        析构函数，确保浏览器进程被正确关闭
        """
        if self.driver:
            try:
                self.driver.quit()
                print("浏览器已在析构时关闭")
            except Exception as e:
                print(f"析构时关闭浏览器失败: {e}")
            finally:
                self.driver = None
    
    def __enter__(self):
        """
        上下文管理器入口
        """
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        上下文管理器出口，确保浏览器被关闭
        """
        self.close()
        return False
    
    def screenshot(self, path: str) -> bool:
        """
        截取页面截图
        """
        if self.driver:
            try:
                self.driver.save_screenshot(path)
                return True
            except Exception as e:
                print(f"截图失败: {e}")
        return False

class SyncBrowserSimulator:
    """
    同步版本的浏览器模拟器
    """
    def __init__(self):
        self.simulator = BrowserSimulator()
    
    def init_browser(self, headless: bool = True) -> None:
        return self.simulator.init_browser(headless)
    
    def load_page(self, url: str, timeout: int = 60) -> bool:
        return self.simulator.load_page(url, timeout)
    
    def get_page_content(self) -> str:
        return self.simulator.get_page_content()
    
    def get_video_resources(self) -> List[Dict[str, Any]]:
        return self.simulator.get_video_resources()
    
    def get_network_requests(self) -> List[Dict[str, Any]]:
        return self.simulator.get_network_requests()
    
    def execute_script(self, script: str) -> Any:
        return self.simulator.execute_script(script)
    
    def close(self) -> None:
        return self.simulator.close()
    
    def __del__(self) -> None:
        """
        析构函数，确保浏览器进程被正确关闭
        """
        if hasattr(self, 'simulator') and self.simulator:
            try:
                self.simulator.close()
                print("SyncBrowserSimulator已在析构时关闭")
            except Exception as e:
                print(f"析构时关闭SyncBrowserSimulator失败: {e}")
    
    def __enter__(self):
        """
        上下文管理器入口
        """
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        上下文管理器出口，确保浏览器被关闭
        """
        self.close()
        return False
    
    def screenshot(self, path: str) -> bool:
        return self.simulator.screenshot(path)