import time
from browser_simulator import BrowserSimulator

# 测试浏览器模拟器的性能
def test_browser_performance():
    print("开始测试浏览器模拟器性能...")
    
    # 创建浏览器模拟器实例
    browser = BrowserSimulator()
    
    try:
        # 初始化浏览器
        print("初始化浏览器...")
        browser.init_browser(headless=True)
        
        # 测试URL - 使用一个简单的网页
        test_url = "https://www.baidu.com"
        print(f"加载测试URL: {test_url}")
        
        # 记录开始时间
        start_time = time.time()
        
        # 加载页面
        success = browser.load_page(test_url, timeout=30)
        
        # 记录结束时间
        end_time = time.time()
        
        print(f"页面加载 {'成功' if success else '失败'}")
        print(f"加载时间: {end_time - start_time:.2f} 秒")
        
        # 打印视频资源数量
        video_resources = browser.get_video_resources()
        print(f"找到 {len(video_resources)} 个视频资源")
        
        # 打印网络请求数量
        network_requests = browser.get_network_requests()
        print(f"捕获到 {len(network_requests)} 个网络请求")
        
        print("测试完成，浏览器模拟器性能正常！")
        
    except Exception as e:
        print(f"测试失败: {e}")
    finally:
        # 关闭浏览器
        print("关闭浏览器...")
        browser.close()

if __name__ == "__main__":
    test_browser_performance()
