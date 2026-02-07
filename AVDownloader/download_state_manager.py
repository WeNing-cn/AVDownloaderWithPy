import os
import configparser
from typing import List, Dict, Any, Optional
from datetime import datetime

class DownloadStateManager:
    """
    下载状态管理器
    用于保存和读取下载任务的状态
    """
    
    def __init__(self, config_file: str = None):
        """
        初始化状态管理器
        
        Args:
            config_file: 配置文件路径，如果为None则使用默认路径
        """
        if config_file is None:
            # 获取程序根目录
            import sys
            root_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
            # 确保Resources目录存在
            resources_dir = os.path.join(root_dir, "Resources")
            os.makedirs(resources_dir, exist_ok=True)
            # 配置文件路径
            config_file = os.path.join(resources_dir, "download_state.ini")
        
        self.config_file = config_file
        self.config = configparser.ConfigParser()
        
        print(f"[状态管理器] 配置文件路径: {self.config_file}")
        
        # 如果配置文件不存在，创建一个空的
        if not os.path.exists(config_file):
            print(f"[状态管理器] 配置文件不存在，创建新文件")
            self._create_empty_config()
        else:
            print(f"[状态管理器] 配置文件已存在，加载配置")
            self._load_config()
    
    def _create_empty_config(self):
        """
        创建空的配置文件
        """
        self.config['General'] = {
            'version': '1.0',
            'created_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        self.config['Tasks'] = {}
        self._save_config()
    
    def _save_config(self):
        """
        保存配置到文件
        """
        with open(self.config_file, 'w', encoding='utf-8') as f:
            self.config.write(f)
    
    def _load_config(self):
        """
        从文件加载配置
        """
        self.config.read(self.config_file, encoding='utf-8')
    
    def save_task(self, task_id: str, task_info: Dict[str, Any]):
        """
        保存任务信息
        
        Args:
            task_id: 任务ID
            task_info: 任务信息字典
        """
        print(f"[状态管理器] 开始保存任务: {task_id}")
        self._load_config()
        
        if 'Tasks' not in self.config:
            self.config['Tasks'] = {}
        
        # 将任务信息转换为字符串
        task_section = f'Task_{task_id}'
        self.config[task_section] = {}
        
        for key, value in task_info.items():
            if isinstance(value, (list, dict)):
                import json
                self.config[task_section][key] = json.dumps(value, ensure_ascii=False)
            else:
                self.config[task_section][key] = str(value)
        
        # 更新任务列表
        if 'Tasks' not in self.config:
            self.config['Tasks'] = {}
        
        tasks = self.config['Tasks'].get('list', '') if 'list' in self.config['Tasks'] else ''
        task_list = tasks.split(',') if tasks else []
        if task_id not in task_list:
            task_list.append(task_id)
            self.config['Tasks']['list'] = ','.join(task_list)
        
        # 更新最后更新时间
        self.config['General']['last_update'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        print(f"[状态管理器] 准备保存配置到文件")
        self._save_config()
        print(f"[状态管理器] 任务 {task_id} 保存成功")
    
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        获取任务信息
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务信息字典，如果不存在则返回None
        """
        self._load_config()
        
        task_section = f'Task_{task_id}'
        if task_section not in self.config:
            return None
        
        task_info = {}
        for key, value in self.config[task_section].items():
            try:
                import json
                task_info[key] = json.loads(value)
            except:
                task_info[key] = value
        
        return task_info
    
    def get_all_tasks(self) -> List[Dict[str, Any]]:
        """
        获取所有任务
        
        Returns:
            任务信息列表
        """
        self._load_config()
        
        tasks = []
        
        # 获取任务列表
        if 'Tasks' in self.config and 'list' in self.config['Tasks']:
            tasks_list = self.config['Tasks']['list'].split(',')
        else:
            tasks_list = []
        
        for task_id in tasks_list:
            if task_id:
                task = self.get_task(task_id)
                if task:
                    task['id'] = task_id
                    tasks.append(task)
        
        return tasks
    
    def delete_task(self, task_id: str):
        """
        删除任务
        
        Args:
            task_id: 任务ID
        """
        self._load_config()
        
        task_section = f'Task_{task_id}'
        if task_section in self.config:
            del self.config[task_section]
        
        # 更新任务列表
        if 'Tasks' in self.config and 'list' in self.config['Tasks']:
            tasks = self.config['Tasks']['list'].split(',')
            if task_id in tasks:
                tasks.remove(task_id)
                self.config['Tasks']['list'] = ','.join(tasks)
        
        self._save_config()
    
    def clear_all_tasks(self):
        """
        清除所有任务
        """
        self._load_config()
        
        # 删除所有任务section
        if 'Tasks' in self.config and 'list' in self.config['Tasks']:
            tasks_list = self.config['Tasks']['list'].split(',')
            for task_id in tasks_list:
                task_section = f'Task_{task_id}'
                if task_section in self.config:
                    del self.config[task_section]
        
        # 清空任务列表
        self.config['Tasks'] = {}
        
        self._save_config()
    
    def has_pending_tasks(self) -> bool:
        """
        检查是否有未完成的任务
        
        Returns:
            如果有未完成的任务返回True，否则返回False
        """
        tasks = self.get_all_tasks()
        for task in tasks:
            if task.get('status') in ['pending', 'downloading', 'paused']:
                return True
        return False
    
    def get_pending_tasks(self) -> List[Dict[str, Any]]:
        """
        获取所有未完成的任务
        
        Returns:
            未完成任务列表
        """
        tasks = self.get_all_tasks()
        pending_tasks = []
        
        for task in tasks:
            if task.get('status') in ['pending', 'downloading', 'paused']:
                pending_tasks.append(task)
        
        return pending_tasks
    
    def update_task_status(self, task_id: str, status: str):
        """
        更新任务状态
        
        Args:
            task_id: 任务ID
            status: 新状态
        """
        self._load_config()
        
        task_section = f'Task_{task_id}'
        if task_section in self.config:
            self.config[task_section]['status'] = status
            self.config[task_section]['last_update'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self._save_config()
    
    def update_task_info(self, task_id: str, info: Dict[str, Any]):
        """
        更新任务信息
        
        Args:
            task_id: 任务ID
            info: 要更新的信息字典
        """
        self._load_config()
        
        task_section = f'Task_{task_id}'
        if task_section in self.config:
            for key, value in info.items():
                if isinstance(value, (list, dict)):
                    import json
                    self.config[task_section][key] = json.dumps(value, ensure_ascii=False)
                else:
                    self.config[task_section][key] = str(value)
            self.config[task_section]['last_update'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self._save_config()
            print(f"[状态管理器] 任务 {task_id} 信息已更新: {info}")
    
    def update_task_progress(self, task_id: str, progress: float, downloaded: int, total: int):
        """
        更新任务进度
        
        Args:
            task_id: 任务ID
            progress: 进度百分比 (0-100)
            downloaded: 已下载数量
            total: 总数量
        """
        self._load_config()
        
        task_section = f'Task_{task_id}'
        if task_section in self.config:
            self.config[task_section]['progress'] = str(progress)
            self.config[task_section]['downloaded'] = str(downloaded)
            self.config[task_section]['total'] = str(total)
            self.config[task_section]['last_update'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self._save_config()
    
    def add_downloaded_segment(self, task_id: str, segment_index: int):
        """
        添加已下载的ts分片
        
        Args:
            task_id: 任务ID
            segment_index: 分片索引
        """
        self._load_config()
        
        task_section = f'Task_{task_id}'
        if task_section not in self.config:
            print(f"[状态管理器] 任务 {task_id} 不存在，无法添加分片记录")
            return
        
        # 获取已下载的分片列表
        downloaded_segments = self.config[task_section].get('downloaded_segments', '')
        segments_list = downloaded_segments.split(',') if downloaded_segments else []
        
        # 添加新的分片索引
        if str(segment_index) not in segments_list:
            segments_list.append(str(segment_index))
            segments_list.sort(key=int)  # 按索引排序
            self.config[task_section]['downloaded_segments'] = ','.join(segments_list)
            self.config[task_section]['last_update'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self._save_config()
            print(f"[状态管理器] 任务 {task_id} 添加已下载分片: {segment_index}")
    
    def get_downloaded_segments(self, task_id: str) -> List[int]:
        """
        获取已下载的ts分片列表
        
        Args:
            task_id: 任务ID
            
        Returns:
            已下载分片索引列表
        """
        self._load_config()
        
        task_section = f'Task_{task_id}'
        if task_section not in self.config:
            return []
        
        downloaded_segments = self.config[task_section].get('downloaded_segments', '')
        segments_list = downloaded_segments.split(',') if downloaded_segments else []
        
        # 转换为整数列表
        return [int(seg) for seg in segments_list if seg.strip()]
    
    def clear_downloaded_segments(self, task_id: str):
        """
        清除任务的已下载分片记录
        
        Args:
            task_id: 任务ID
        """
        self._load_config()
        
        task_section = f'Task_{task_id}'
        if task_section in self.config:
            self.config[task_section]['downloaded_segments'] = ''
            self.config[task_section]['last_update'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self._save_config()
            print(f"[状态管理器] 任务 {task_id} 已清除分片记录")
    
    def remove_task(self, task_id: str):
        """
        移除指定任务
        
        Args:
            task_id: 任务ID
        """
        self._load_config()
        
        # 删除任务section
        task_section = f'Task_{task_id}'
        if task_section in self.config:
            del self.config[task_section]
            print(f"[状态管理器] 已删除任务section: {task_section}")
        
        # 更新任务列表
        if 'Tasks' in self.config and 'list' in self.config['Tasks']:
            tasks_list = self.config['Tasks']['list'].split(',')
            if task_id in tasks_list:
                tasks_list.remove(task_id)
                if tasks_list:
                    self.config['Tasks']['list'] = ','.join(tasks_list)
                    print(f"[状态管理器] 已更新任务列表: {tasks_list}")
                else:
                    # 如果任务列表为空，删除Tasks section
                    del self.config['Tasks']
                    print(f"[状态管理器] 任务列表为空，已删除Tasks section")
        
        self._save_config()
        print(f"[状态管理器] 任务 {task_id} 已完全移除")
