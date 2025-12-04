import requests
import json
import time
import os

def load_cookies(cookies_path='weibo_cookies.json'):
    with open(cookies_path, 'r', encoding='utf-8') as f:
        cookies = json.load(f)
    cookies_dict = {c['name']: c['value'] for c in cookies}
    return cookies_dict

def collect_user_ids(seed_uid, max_count=2000, cookies_path='weibo_cookies.json', output_file='user_ids.txt'):
    cookies = load_cookies(cookies_path)
    user_ids = set()
    page = 1
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Referer': f'https://weibo.com/u/{seed_uid}',
        'Accept': 'application/json, text/plain, */*',
        'X-Requested-With': 'XMLHttpRequest',
    }
    while len(user_ids) < max_count:
        url = f'https://weibo.com/ajax/friendships/friends?uid={seed_uid}&page={page}&count=20'
        resp = requests.get(url, cookies=cookies, headers=headers)
        if resp.status_code != 200:
            print('请求失败，状态码：', resp.status_code)
            time.sleep(10)
            continue
        data = resp.json()
        users = data.get('users', [])
        if not users:
            break
        for u in users:
            user_ids.add(str(u['id']))
            if len(user_ids) >= max_count:
                break
        print(f'已采集用户数：{len(user_ids)}')
        page += 1
        time.sleep(3)
    with open(output_file, 'w', encoding='utf-8') as f:
        for uid in user_ids:
            f.write(uid + '\n')
    print(f'用户ID已保存到 {output_file}')

if __name__ == '__main__':
    # 想采集的种子用户ID
    seed_uid = '5025719938'
    collect_user_ids(seed_uid, max_count=2000)