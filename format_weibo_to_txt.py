import json

def format_weibo(weibo):
    user = weibo.get('user', {}).get('screen_name', '未知用户')
    created_at = weibo.get('created_at', '')
    text = weibo.get('text', '')
    comments = weibo.get('comments', [])
    s = f"【用户】{user}\n【发布时间】{created_at}\n【内容】\n{text}\n\n【评论】\n"
    for idx, c in enumerate(comments, 1):
        s += f"{idx}. {c.get('user', '未知')}：{c.get('text', '')}\n"
    s += '-'*40 + '\n'
    return s

with open('all_weibos.txt', 'r', encoding='utf-8') as fin, open('all_weibos_readable.txt', 'w', encoding='utf-8') as fout:
    for line in fin:
        try:
            weibo = json.loads(line)
            fout.write(format_weibo(weibo))
        except Exception as e:
            print('格式化失败:', e) 