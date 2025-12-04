import requests
import json
import time
import os
import re
import argparse
from datetime import datetime
import sys
import pickle

class WeiboCrawler:
    def __init__(self, cookie=None):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Referer': 'https://weibo.com/',
            'Origin': 'https://weibo.com',
        }
        
        if cookie:
            self.headers['Cookie'] = cookie
        
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    # 获取用户基本信息
    def get_user_info(self, user_id):
        url = f'https://weibo.com/ajax/profile/info?uid={user_id}'
        try:
            response = self.session.get(url)
            print(f"请求URL: {url}")
            print(f"响应状态码: {response.status_code}")
            print(f"响应内容: {response.text[:300]}")
            if response.status_code == 200:
                data = response.json()
                if data.get('ok') == 1 and 'data' in data:
                    return data['data']['user']
            return None
        except Exception as e:
            print(f"获取用户信息失败: {e}")
            return None
        
    # 获取用户的微博列表
    def get_user_weibos(self, user_id, page=1, count=20):
        # 尝试多个API接口
        urls_to_try = [
            f'https://weibo.com/ajax/statuses/mymblog?uid={user_id}&page={page}&count={count}',
            f'https://weibo.com/ajax/statuses/mymblog?uid={user_id}&page={page}',
            f'https://weibo.com/ajax/statuses/mymblog?uid={user_id}',
            f'https://weibo.com/ajax/statuses/user_timeline?uid={user_id}&page={page}&count={count}',
            f'https://weibo.com/ajax/statuses/user_timeline?uid={user_id}&page={page}'
        ]
        
        for url in urls_to_try:
            try:
                print(f"尝试请求: {url}")
                response = self.session.get(url, timeout=30)
                print(f"响应状态码: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"API响应: {data.get('ok', 'unknown')}")
                    
                    if data.get('ok') == 1 and 'data' in data:
                        weibo_list = data['data']['list']
                        total = data['data'].get('total', 0)
                        print(f"获取到 {len(weibo_list)} 条微博，总数: {total}")
                        return weibo_list, total
                    else:
                        print(f"API返回错误: {data}")
                elif response.status_code == 414:
                    print(f"URL过长错误(414)，尝试下一个接口...")
                    continue
                else:
                    print(f"HTTP请求失败: {response.status_code}")
                    continue
            except Exception as e:
                print(f"请求失败: {e}")
                continue
        
        print("所有API接口都失败了")
        return [], 0
    
    # 清理文本内容，去除HTML标签等
    def clean_text(self, text):
        if not text:
            return ""
        # 去除HTML标签
        text = re.sub(r'<[^>]+>', '', text)
        # 替换特殊字符
        text = text.replace('&nbsp;', ' ')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        text = text.replace('&amp;', '&')
        # 去除多余空格和换行
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    
    # 格式化微博内容
    def format_weibo(self, weibo):
        try:
            if not weibo or not isinstance(weibo, dict):
                return f"[数据格式错误] 微博数据无效\n" + "-" * 50 + "\n"
            created_at = weibo.get('created_at', '')
            if created_at:
                try:
                    created_at = datetime.strptime(created_at, '%a %b %d %H:%M:%S %z %Y').strftime('%Y-%m-%d %H:%M:%S')
                except:
                    created_at = str(created_at)
            else:
                created_at = '未知时间'
            text = weibo.get('text', '')
            if text is None:
                text = ''
            text = self.clean_text(text)
            formatted = f"[{created_at}]\n{text}\n"
            # 转发内容
            retweeted_status = weibo.get('retweeted_status')
            if retweeted_status is not None and isinstance(retweeted_status, dict):
                retweeted_user = retweeted_status.get('user')
                if retweeted_user is not None and isinstance(retweeted_user, dict):
                    retweeted_user_name = retweeted_user.get('screen_name', '未知用户')
                    if retweeted_user_name is None:
                        retweeted_user_name = '未知用户'
                else:
                    retweeted_user_name = '未知用户'
                retweeted_text = retweeted_status.get('text', '')
                if retweeted_text is None:
                    retweeted_text = ''
                retweeted_text = self.clean_text(retweeted_text)
                formatted += f"\n转发 @{retweeted_user_name}: {retweeted_text}\n"
            
            formatted += "-" * 50 + "\n"
            return formatted
        except Exception as e:
            print(f"格式化微博时出错: {e}")
            try:
                weibo_id = weibo.get('id', 'unknown') if weibo else 'unknown'
                return f"[格式化错误] 微博ID: {weibo_id}\n" + "-" * 50 + "\n"
            except:
                return f"[格式化错误] 微博数据异常\n" + "-" * 50 + "\n"
    
    # 爬取用户的所有微博
    def crawl_user_weibos(self, user_id, max_pages=None):
        user_info = self.get_user_info(user_id)
        if not user_info:
            print(f"未找到用户 {user_id} 的信息")
            return [], str(user_id)  # 返回空列表和用户ID作为用户名
        
        screen_name = user_info.get('screen_name', user_id)
        print(f"开始爬取用户 {screen_name} 的微博")
        
        all_weibos = []
        page = 1
        
        while True:
            # 检查页数限制
            if max_pages is not None and page > max_pages:
                print(f"已达到最大页数限制: {max_pages}，停止爬取")
                break
                
            print(f"正在爬取第 {page} 页...")
            weibos, total = self.get_user_weibos(user_id, page)
            
            if not weibos:
                print(f"第 {page} 页没有数据，停止爬取")
                break
                
            all_weibos.extend(weibos)
            print(f"第 {page} 页获取到 {len(weibos)} 条微博")
            
            # 如果返回的微博数量少于20条，说明可能是最后一页
            if len(weibos) < 20:
                print(f"第 {page} 页只有 {len(weibos)} 条微博，可能是最后一页")
                break
            
            page += 1
            # 防止请求过快
            time.sleep(1)
        
        print(f"共爬取到 {len(all_weibos)} 条微博")
        return all_weibos, screen_name
    
    # 爬取用户微博并保存到文件
    def save_weibos_to_file(self, user_id, max_pages=None):
        weibos, screen_name = self.crawl_user_weibos(user_id, max_pages)
        if not weibos:
            return None
        
        # 创建文件名
        filename = f"{user_id}_weibos.txt"
        
        # 写入文件
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"用户: {screen_name} (ID: {user_id})\n")
            f.write(f"爬取时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"微博数量: {len(weibos)}\n")
            f.write("=" * 50 + "\n\n")
            
            for weibo in weibos:
                formatted = self.format_weibo(weibo)
                f.write(formatted)
        
        print(f"微博内容已保存到文件: {filename}")
        return filename

    # 获取微博下的评论
    def get_comments(self, weibo_id, count=10):
        url = f"https://weibo.com/ajax/statuses/buildComments?is_reload=1&id={weibo_id}&is_show_bulletin=2&is_mix=0&count={count}"
        try:
            resp = self.session.get(url, timeout=10)
            data = resp.json()
            if data.get("ok") == 1 and "data" in data:
                comments = []
                for c in data["data"]:
                    comments.append({
                        "user": c.get("user", {}).get("screen_name", ""),
                        "text": self.clean_text(c.get("text", "")),
                        "like_count": c.get("like_count", 0)
                    })
                return comments
            else:
                return []
        except Exception as e:
            print(f"获取评论失败: {e}")
            return []

def batch_crawl(user_ids, cookie=None, max_pages=None, total_limit=10000):
    crawler = WeiboCrawler(cookie=cookie)
    all_weibos = []
    
    print(f"开始批量爬取，目标：总微博数≥{total_limit}")
    print(f"用户列表长度: {len(user_ids)}")
    print(f"每个用户最大爬取页数: {max_pages if max_pages else '无限制'}")
    
    for i, user_id in enumerate(user_ids, 1):
        print(f"\n正在处理第 {i}/{len(user_ids)} 个用户: {user_id}")
        
        try:
            weibos, screen_name = crawler.crawl_user_weibos(user_id, max_pages)
            print(f"用户 {screen_name} 爬取到 {len(weibos)} 条微博")
            
            for weibo in weibos:
                # 爬取评论
                weibo_id = weibo.get("id")
                if weibo_id:
                    comments = crawler.get_comments(weibo_id, count=10)
                    weibo["comments"] = comments
                else:
                    weibo["comments"] = []
                all_weibos.append(weibo)
                
                # 检查是否达到目标
                if len(all_weibos) >= total_limit:
                    print(f"已达到目标：总微博数 {len(all_weibos)}")
                    return all_weibos, crawler
            
            print(f"当前累计：总微博数 {len(all_weibos)}")
            
            # 如果已经爬取了足够多的用户，可以提前停止
            if i >= 20 and len(all_weibos) >= total_limit * 0.8:  # 爬取20个用户或达到80%目标
                print(f"已爬取 {i} 个用户，达到预期目标，提前停止")
                break
            
        except Exception as e:
            print(f"处理用户 {user_id} 时出错: {e}")
            continue
    
    print(f"所有用户处理完成，最终结果：总微博数 {len(all_weibos)}")
    return all_weibos, crawler

# 保存批量爬取的微博到文件
def save_batch_weibos(all_weibos, crawler=None):
    print(f"开始保存微博，总微博数: {len(all_weibos)}")
    
    # 如果没有传入crawler实例，创建一个新的
    if crawler is None:
        crawler = WeiboCrawler()
    
    # 保存所有微博为jsonl格式
    print("正在保存所有微博到 all_weibos.txt...")
    with open('all_weibos.txt', 'w', encoding='utf-8') as f:
        for weibo in all_weibos:
            try:
                f.write(json.dumps(weibo, ensure_ascii=False) + "\n")
            except Exception as e:
                print(f"保存微博json时出错: {e}")
                f.write(json.dumps({"error": str(e), "id": weibo.get('id', 'unknown')}, ensure_ascii=False) + "\n")
    
    print("所有文件保存完成！")

def main():
    parser = argparse.ArgumentParser(description='微博爬虫 - 批量爬取用户微博')
    parser.add_argument('--cookie', help='登录cookie字符串', default=None)
    parser.add_argument('--max-pages', type=int, help='最大爬取页数', default=5)
    parser.add_argument('--cookie-file', help='包含cookie的文件路径', default=None)
    parser.add_argument('--user-ids-file', help='用户ID列表txt文件', default='user_ids.txt')
    parser.add_argument('--total-limit', type=int, help='累计微博总数', default=10000)
    args = parser.parse_args()

    cookie = args.cookie
    if args.cookie_file and not cookie:
        try:
            with open(args.cookie_file, 'r', encoding='utf-8') as f:
                cookie = f.read().strip()
        except Exception as e:
            print(f"读取cookie文件失败: {e}")

    # 读取用户ID列表
    try:
        print(f"正在读取用户ID文件: {args.user_ids_file}")
        with open(args.user_ids_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            print(f"文件总行数: {len(lines)}")
            
            user_ids = []
            for i, line in enumerate(lines, 1):
                line = line.strip()
                if line and not line.startswith('#'):  # 忽略空行和注释行
                    user_ids.append(line)
            
            print(f"有效用户ID数量: {len(user_ids)}")
            if user_ids:
                print(f"前5个用户ID: {user_ids[:5]}")
            else:
                print("警告：没有找到有效的用户ID")
                
    except FileNotFoundError:
        print(f"错误：找不到文件 {args.user_ids_file}")
        sys.exit(1)
    except Exception as e:
        print(f"读取用户ID文件失败: {e}")
        sys.exit(1)

    print(f"设置最大爬取页数: {args.max_pages}")
    all_weibos, crawler = batch_crawl(user_ids, cookie, args.max_pages, args.total_limit)
    print(f"最终累计微博数: {len(all_weibos)}")
    save_batch_weibos(all_weibos, crawler)
    print("所有微博已保存到 all_weibos.txt")

if __name__ == "__main__":
    main()