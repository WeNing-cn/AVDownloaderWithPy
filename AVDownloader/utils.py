import os
import re
import time
import json
import shutil
import hashlib
from datetime import datetime
from urllib.parse import urlparse, urljoin
from typing import Optional, Any, Dict, List

class Utils:
    @staticmethod
    def format_file_size(size_bytes: int) -> str:
        """
        格式化文件大小
        """
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} PB"
    
    @staticmethod
    def get_file_extension(filename: str) -> str:
        """
        获取文件扩展名
        """
        return os.path.splitext(filename)[1].lower()
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """
        清理文件名，移除非法字符
        """
        # 移除Windows非法字符
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        
        # 移除控制字符
        filename = re.sub(r'[\x00-\x1f\x7f]', '', filename)
        
        # 移除首尾空格
        filename = filename.strip()
        
        # 限制文件名长度
        if len(filename) > 255:
            filename = filename[:255]
        
        return filename
    
    @staticmethod
    def ensure_directory(directory: str) -> bool:
        """
        确保目录存在
        """
        try:
            if not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
            return True
        except Exception as e:
            print(f"创建目录失败: {e}")
            return False
    
    @staticmethod
    def delete_file(file_path: str) -> bool:
        """
        删除文件
        """
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
            return True
        except Exception as e:
            print(f"删除文件失败: {e}")
            return False
    
    @staticmethod
    def delete_directory(directory: str) -> bool:
        """
        删除目录
        """
        try:
            if os.path.exists(directory):
                shutil.rmtree(directory)
            return True
        except Exception as e:
            print(f"删除目录失败: {e}")
            return False
    
    @staticmethod
    def copy_file(src: str, dst: str) -> bool:
        """
        复制文件
        """
        try:
            # 确保目标目录存在
            dst_dir = os.path.dirname(dst)
            if dst_dir and not os.path.exists(dst_dir):
                os.makedirs(dst_dir, exist_ok=True)
            
            shutil.copy2(src, dst)
            return True
        except Exception as e:
            print(f"复制文件失败: {e}")
            return False
    
    @staticmethod
    def move_file(src: str, dst: str) -> bool:
        """
        移动文件
        """
        try:
            # 确保目标目录存在
            dst_dir = os.path.dirname(dst)
            if dst_dir and not os.path.exists(dst_dir):
                os.makedirs(dst_dir, exist_ok=True)
            
            shutil.move(src, dst)
            return True
        except Exception as e:
            print(f"移动文件失败: {e}")
            return False
    
    @staticmethod
    def get_file_hash(file_path: str, algorithm: str = 'md5') -> Optional[str]:
        """
        获取文件哈希值
        """
        try:
            hash_obj = hashlib.new(algorithm)
            with open(file_path, 'rb') as f:
                while chunk := f.read(8192):
                    hash_obj.update(chunk)
            return hash_obj.hexdigest()
        except Exception as e:
            print(f"计算文件哈希失败: {e}")
            return None
    
    @staticmethod
    def is_valid_url(url: str) -> bool:
        """
        验证URL是否有效
        """
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except:
            return False
    
    @staticmethod
    def normalize_url(url: str, base_url: str) -> str:
        """
        规范化URL，处理相对路径
        """
        try:
            if not url:
                return ''
            
            # 如果是完整URL，直接返回
            if urlparse(url).scheme in ['http', 'https']:
                return url
            
            # 否则，使用base_url构建完整URL
            return urljoin(base_url, url)
        except Exception:
            return ''
    
    @staticmethod
    def format_time(timestamp: float) -> str:
        """
        格式化时间戳
        """
        try:
            return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
        except Exception:
            return 'N/A'
    
    @staticmethod
    def format_duration(seconds: float) -> str:
        """
        格式化持续时间
        """
        try:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            secs = int(seconds % 60)
            
            if hours > 0:
                return f"{hours}:{minutes:02d}:{secs:02d}"
            elif minutes > 0:
                return f"{minutes}:{secs:02d}"
            else:
                return f"{secs}秒"
        except Exception:
            return 'N/A'
    
    @staticmethod
    def read_json(file_path: str) -> Optional[Dict]:
        """
        读取JSON文件
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"读取JSON文件失败: {e}")
            return None
    
    @staticmethod
    def write_json(file_path: str, data: Any) -> bool:
        """
        写入JSON文件
        """
        try:
            # 确保目录存在
            directory = os.path.dirname(file_path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"写入JSON文件失败: {e}")
            return False
    
    @staticmethod
    def get_timestamp() -> str:
        """
        获取当前时间戳字符串
        """
        return datetime.now().strftime('%Y%m%d%H%M%S')
    
    @staticmethod
    def get_datetime() -> str:
        """
        获取当前日期时间字符串
        """
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    @staticmethod
    def retry(func, max_retries: int = 3, delay: float = 1.0, *args, **kwargs) -> Any:
        """
        重试装饰器
        """
        retries = 0
        while retries < max_retries:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                retries += 1
                if retries >= max_retries:
                    raise
                print(f"尝试 {retries}/{max_retries} 失败: {e}")
                time.sleep(delay)
    
    @staticmethod
    def safe_execute(func, default: Any = None, *args, **kwargs) -> Any:
        """
        安全执行函数，捕获异常
        """
        try:
            return func(*args, **kwargs)
        except Exception as e:
            print(f"执行函数失败: {e}")
            return default
    
    @staticmethod
    def find_files(directory: str, extensions: List[str] = None) -> List[str]:
        """
        查找目录中的文件
        """
        found_files = []
        
        try:
            for root, dirs, files in os.walk(directory):
                for file in files:
                    if extensions:
                        if any(file.lower().endswith(ext.lower()) for ext in extensions):
                            found_files.append(os.path.join(root, file))
                    else:
                        found_files.append(os.path.join(root, file))
        except Exception as e:
            print(f"查找文件失败: {e}")
        
        return found_files
    
    @staticmethod
    def get_directory_size(directory: str) -> int:
        """
        获取目录大小
        """
        total_size = 0
        
        try:
            for root, dirs, files in os.walk(directory):
                for file in files:
                    file_path = os.path.join(root, file)
                    if os.path.exists(file_path):
                        total_size += os.path.getsize(file_path)
        except Exception as e:
            print(f"获取目录大小失败: {e}")
        
        return total_size
    
    @staticmethod
    def clean_temp_files(directory: str, max_age_hours: int = 24) -> int:
        """
        清理临时文件
        """
        cleaned_count = 0
        cutoff_time = time.time() - (max_age_hours * 3600)
        
        try:
            for root, dirs, files in os.walk(directory):
                for file in files:
                    file_path = os.path.join(root, file)
                    try:
                        if os.path.getmtime(file_path) < cutoff_time:
                            os.remove(file_path)
                            cleaned_count += 1
                    except Exception:
                        pass
                
                # 清理空目录
                for dir_name in dirs:
                    dir_path = os.path.join(root, dir_name)
                    try:
                        if not os.listdir(dir_path):
                            os.rmdir(dir_path)
                    except Exception:
                        pass
        except Exception as e:
            print(f"清理临时文件失败: {e}")
        
        return cleaned_count

# 全局工具实例
utils = Utils()
