#!/usr/bin/env python3
"""
分析加密的M3U8视频流
用于破解网站上的加密视频
"""

import os
import json
import requests
from urllib.parse import urljoin, urlparse

def load_example_files():
    """
    加载示例文件
    """
    print("加载示例文件...")
    
    # 加载getmovie.json
    json_path = "getmovie.json"
    if not os.path.exists(json_path):
        print(f"错误: {json_path} 文件不存在")
        return None, None
    
    with open(json_path, 'r', encoding='utf-8') as f:
        try:
            json_data = json.load(f)
            m3u8_path = json_data.get('m3u8', '')
            print(f"从JSON中获取的M3U8路径: {m3u8_path}")
        except Exception as e:
            print(f"解析JSON文件失败: {e}")
            return None, None
    
    # 加载getmovie.key
    key_path = "getmovie.key"
    if not os.path.exists(key_path):
        print(f"错误: {key_path} 文件不存在")
        return m3u8_path, None
    
    with open(key_path, 'r', encoding='utf-8') as f:
        try:
            key = f.read().strip()
            print(f"从KEY文件中获取的密钥: {key}")
            print(f"密钥长度: {len(key)} 字符")
        except Exception as e:
            print(f"读取KEY文件失败: {e}")
            return m3u8_path, None
    
    return m3u8_path, key

def analyze_key(key):
    """
    分析密钥格式
    """
    print("\n分析密钥格式...")
    print(f"密钥原始值: {key}")
    print(f"密钥长度: {len(key)} 字符")
    
    # 尝试不同的密钥格式
    try:
        # 尝试作为十六进制字符串
        hex_key = bytes.fromhex(key)
        print(f"作为十六进制解码: {hex_key}")
        print(f"十六进制解码后长度: {len(hex_key)} 字节")
    except Exception as e:
        print(f"十六进制解码失败: {e}")
    
    try:
        # 尝试作为ASCII字符串
        ascii_key = key.encode('ascii')
        print(f"作为ASCII编码: {ascii_key}")
        print(f"ASCII编码后长度: {len(ascii_key)} 字节")
    except Exception as e:
        print(f"ASCII编码失败: {e}")

def construct_full_url(base_url, m3u8_path):
    """
    构造完整的M3U8 URL
    """
    print("\n构造完整的M3U8 URL...")
    full_url = urljoin(base_url, m3u8_path)
    print(f"完整的M3U8 URL: {full_url}")
    return full_url

def fetch_m3u8_content(url):
    """
    获取M3U8文件内容
    """
    print("\n获取M3U8文件内容...")
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        content = response.text
        print(f"M3U8文件长度: {len(content)} 字符")
        print("M3U8文件内容:")
        print(content)
        return content
    except Exception as e:
        print(f"获取M3U8文件失败: {e}")
        return None

def analyze_m3u8_content(content):
    """
    分析M3U8文件内容
    """
    print("\n分析M3U8文件内容...")
    if not content:
        return None
    
    lines = content.strip().split('\n')
    encryption_info = {
        'method': None,
        'key_url': None,
        'iv': None
    }
    
    for line in lines:
        line = line.strip()
        if line.startswith('#EXT-X-KEY:'):
            print(f"找到加密信息: {line}")
            # 解析加密信息
            parts = line.split(',')
            for part in parts:
                part = part.strip()
                if part.startswith('METHOD='):
                    encryption_info['method'] = part.split('=', 1)[1]
                elif part.startswith('URI='):
                    key_url = part.split('=', 1)[1]
                    # 移除引号
                    if key_url.startswith('"') and key_url.endswith('"'):
                        key_url = key_url[1:-1]
                    encryption_info['key_url'] = key_url
                elif part.startswith('IV='):
                    encryption_info['iv'] = part.split('=', 1)[1]
        elif not line.startswith('#') and line:
            print(f"找到TS分片: {line}")
    
    print(f"加密方法: {encryption_info['method']}")
    print(f"密钥URL: {encryption_info['key_url']}")
    print(f"初始化向量: {encryption_info['iv']}")
    
    return encryption_info

def main():
    """
    主函数
    """
    print("=" * 60)
    print("加密M3U8视频流分析工具")
    print("=" * 60)
    
    # 切换到示例目录
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # 加载示例文件
    m3u8_path, key = load_example_files()
    if not m3u8_path:
        print("错误: 无法加载示例文件")
        return
    
    # 分析密钥
    if key:
        analyze_key(key)
    
    # 提示用户输入网站基础URL
    base_url = input("\n请输入网站基础URL (例如: https://example.com): ").strip()
    if not base_url:
        print("错误: 必须输入网站基础URL")
        return
    
    # 构造完整的M3U8 URL
    full_m3u8_url = construct_full_url(base_url, m3u8_path)
    
    # 获取M3U8文件内容
    m3u8_content = fetch_m3u8_content(full_m3u8_url)
    
    # 分析M3U8文件内容
    if m3u8_content:
        encryption_info = analyze_m3u8_content(m3u8_content)
        
        # 提供破解方案
        print("\n" + "=" * 60)
        print("破解方案")
        print("=" * 60)
        print("1. 基础URL: " + base_url)
        print("2. M3U8路径: " + m3u8_path)
        print("3. 完整M3U8 URL: " + full_m3u8_url)
        print("4. 密钥文件内容: " + (key or "未知"))
        
        if encryption_info:
            print("5. 加密方法: " + (encryption_info['method'] or "未知"))
            print("6. 密钥URL: " + (encryption_info['key_url'] or "未知"))
            print("7. 初始化向量: " + (encryption_info['iv'] or "未知"))
        
        print("\n破解步骤:")
        print("1. 使用完整的M3U8 URL作为下载地址")
        print("2. 当需要密钥时，使用getmovie.key文件中的内容")
        print("3. 如果网站要求referer或其他headers，需要在请求中添加")
        print("4. 使用TSMerger类的download_and_merge方法下载和解密")

if __name__ == "__main__":
    main()
