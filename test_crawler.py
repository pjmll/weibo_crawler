from weibo_crawler import WeiboCrawler
import sys

# 测试单个用户的微博爬取
def test_single_user(user_id, cookie_file='cookie.txt'):
    print(f"开始测试用户ID: {user_id}")
    
    # 读取cookie
    try:
        with open(cookie_file, 'r', encoding='utf-8') as f:
            cookie = f.read().strip()
        print(f"Cookie长度: {len(cookie)} 字符")
    except Exception as e:
        print(f"读取cookie失败: {e}")
        return
    
    # 创建爬虫实例
    crawler = WeiboCrawler(cookie=cookie)
    
    # 测试获取用户信息
    print("\n1. 测试获取用户信息...")
    user_info = crawler.get_user_info(user_id)
    if user_info:
        print(f"用户信息: {user_info.get('screen_name', '未知')} (@{user_info.get('screen_name', '未知')})")
    else:
        print("获取用户信息失败")
        return
    
    # 测试获取微博列表
    print("\n2. 测试获取微博列表...")
    weibos, total = crawler.get_user_weibos(user_id, page=1, count=5)
    
    if weibos:
        print(f"成功获取 {len(weibos)} 条微博")
        print(f"用户总微博数: {total}")
        
        # 显示第一条微博的详细信息
        if len(weibos) > 0:
            first_weibo = weibos[0]
            print(f"\n第一条微博:")
            print(f"  发布时间: {first_weibo.get('created_at', '未知')}")
            print(f"  内容: {first_weibo.get('text', '')[:100]}...")
            print(f"  转发数: {first_weibo.get('reposts_count', 0)}")
            print(f"  评论数: {first_weibo.get('comments_count', 0)}")
            print(f"  点赞数: {first_weibo.get('attitudes_count', 0)}")
            
            # 检查是否有视频
            page_info = first_weibo.get('page_info')
            if page_info:
                print(f"  页面信息: {page_info.get('type', '未知')}")
                if page_info.get('type') == 'video':
                    print("这是视频微博")
    else:
        print("获取微博列表失败")

def main():
    if len(sys.argv) < 2:
        print("使用方法: python test_crawler.py <用户ID>")
        print("示例: python test_crawler.py 1004524612")
        return
    
    user_id = sys.argv[1]
    test_single_user(user_id)

if __name__ == "__main__":
    main() 