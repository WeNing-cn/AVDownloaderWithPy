"""
解密已下载的加密TS文件
"""
import os
from ts_merger import TSMerger

def decrypt_existing_ts_files(m3u8_url: str, temp_subdir: str, output_file: str):
    """
    解密已下载的加密TS文件并合并
    
    Args:
        m3u8_url: 原始的M3U8 URL，用于获取解密密钥
        temp_subdir: 包含加密TS文件的临时目录
        output_file: 输出文件路径
    """
    # 创建TS合并器
    merger = TSMerger()
    
    print(f"开始解密已下载的TS文件")
    print(f"M3U8 URL: {m3u8_url}")
    print(f"临时目录: {temp_subdir}")
    print(f"输出文件: {output_file}")
    
    # 1. 解析M3U8获取加密信息
    print("\n1. 解析M3U8获取加密信息...")
    ts_urls, encryption_info = merger.parse_m3u8(m3u8_url)
    
    if encryption_info['method'] == 'NONE':
        print("✓ 未检测到加密，直接合并")
        # 直接合并
        ts_files = merger.get_ts_files_in_subdir(temp_subdir)
        success = merger.merge_ts_segments(ts_files, output_file)
        return success
    
    if not encryption_info['key']:
        print("✗ 无法获取解密密钥")
        return False
    
    print(f"✓ 获取到解密密钥，加密方法: {encryption_info['method']}")
    
    # 2. 获取已下载的TS文件
    print("\n2. 获取已下载的TS文件...")
    ts_files = merger.get_ts_files_in_subdir(temp_subdir)
    
    if not ts_files:
        print("✗ 没有找到TS文件")
        return False
    
    print(f"✓ 找到 {len(ts_files)} 个TS文件")
    
    # 3. 解密所有TS文件
    print("\n3. 开始解密TS文件...")
    decrypted_files = []
    
    for i, ts_file in enumerate(ts_files):
        try:
            # 读取加密的TS文件
            with open(ts_file, 'rb') as f:
                encrypted_data = f.read()
            
            # 解密
            decrypted_data = merger.decrypt_ts_segment(encrypted_data, encryption_info, i)
            
            # 保存解密后的文件
            decrypted_file = ts_file.replace('.ts', '_decrypted.ts')
            with open(decrypted_file, 'wb') as f:
                f.write(decrypted_data)
            
            decrypted_files.append(decrypted_file)
            print(f"  解密进度: {i+1}/{len(ts_files)}")
            
        except Exception as e:
            print(f"  ✗ 解密文件失败 {ts_file}: {e}")
    
    if not decrypted_files:
        print("✗ 没有成功解密任何文件")
        return False
    
    print(f"✓ 成功解密 {len(decrypted_files)} 个文件")
    
    # 4. 合并解密后的文件
    print("\n4. 合并解密后的文件...")
    success = merger.merge_ts_segments(decrypted_files, output_file)
    
    if success:
        print(f"✓ 合并成功: {output_file}")
        
        # 5. 清理解密后的临时文件
        print("\n5. 清理解密后的临时文件...")
        for decrypted_file in decrypted_files:
            try:
                os.remove(decrypted_file)
            except Exception as e:
                print(f"  删除文件失败 {decrypted_file}: {e}")
        
        # 6. 询问是否删除原始加密文件
        print("\n6. 处理原始加密文件...")
        print("注意: 原始加密文件保留在临时目录中，可以手动删除")
    
    return success

if __name__ == "__main__":
    print("解密已下载的加密TS文件")
    print("=" * 50)
    
    # 示例使用（需要替换为实际的M3U8 URL）
    m3u8_url = "https://example.com/video.m3u8"  # 替换为实际的M3U8 URL
    temp_subdir = "download_1770226090"  # 替换为实际的临时目录名称
    output_file = r"C:\index\decrypted_video.mp4"
    
    print("请提供以下信息:")
    print("1. 原始的M3U8 URL（用于获取解密密钥）")
    print("2. 临时目录名称（包含加密的TS文件）")
    print("3. 输出文件路径")
    print()
    print("示例:")
    print(f"  M3U8 URL: {m3u8_url}")
    print(f"  临时目录: {temp_subdir}")
    print(f"  输出文件: {output_file}")
    print()
    print("请在代码中修改这些参数，然后重新运行")