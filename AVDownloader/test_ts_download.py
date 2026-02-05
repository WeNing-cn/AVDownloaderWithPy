from ts_merger import TSMerger

# 测试TS分片下载功能
def test_ts_download():
    print("开始测试TS分片下载功能...")
    
    # 创建TS合并器实例
    ts_merger = TSMerger()
    
    # 测试URL - 来自用户提供的日志
    test_url = "https://www.shankubf.com/m3u8/?url=https://1080p.huyall.com/play/aOYlA9Gd/index.m3u8"
    
    print(f"测试URL: {test_url}")
    
    # 测试is_m3u8_url方法
    is_m3u8 = ts_merger.is_m3u8_url(test_url)
    print(f"is_m3u8_url结果: {is_m3u8}")
    
    if not is_m3u8:
        print("错误: URL未被识别为M3U8播放列表")
        return
    
    # 测试parse_m3u8方法
    print("\n测试parse_m3u8方法...")
    ts_urls = ts_merger.parse_m3u8(test_url)
    print(f"解析结果: 找到 {len(ts_urls)} 个TS分片")
    
    if not ts_urls:
        print("错误: 未找到TS分片")
        return
    
    # 打印前5个TS分片URL
    print("\n前5个TS分片URL:")
    for i, ts_url in enumerate(ts_urls[:5]):
        print(f"{i+1}. {ts_url}")
    
    # 测试TS分片下载
    print("\n测试TS分片下载...")
    try:
        # 只下载第一个分片进行测试
        if ts_urls:
            import tempfile
            import os
            
            with tempfile.TemporaryDirectory() as temp_dir:
                test_output = os.path.join(temp_dir, "test_segment.ts")
                print(f"测试下载第一个TS分片到: {test_output}")
                
                success = ts_merger.download_ts_segment(ts_urls[0], test_output)
                print(f"下载结果: {success}")
                
                if success:
                    file_size = os.path.getsize(test_output)
                    print(f"下载的文件大小: {file_size} 字节")
                    print("TS分片下载测试成功!")
                else:
                    print("错误: TS分片下载失败")
    except Exception as e:
        print(f"测试过程中发生错误: {e}")

if __name__ == "__main__":
    test_ts_download()
