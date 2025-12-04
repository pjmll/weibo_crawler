import json
import os
import re
import csv
from collections import Counter, defaultdict
from datetime import datetime
import pandas as pd

class WeiboAnalyzer:
    def __init__(self, file_path):
        self.file_path = file_path
        self.df = None
        self.keywords = []
    
    # 加载数据并进行预处理
    def load_and_clean_data(self):
        print(f"正在加载数据: {self.file_path} ...")
        data_list = []
        
        if not os.path.exists(self.file_path):
            print(f"错误: 文件 {self.file_path} 不存在")
            return False

        with open(self.file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line: continue
                try:
                    weibo = json.loads(line)
                    # 提取关键字段
                    created_at = weibo.get('created_at', '')
                    text = weibo.get('text_raw', weibo.get('text', '')) # 优先使用raw文本
                    
                    # 清洗文本 (去除HTML标签等)
                    text_clean = re.sub(r'<[^>]+>', '', text)
                    text_clean = re.sub(r'http\S+', '', text_clean)
                    
                    # 解析时间 (微博时间格式通常为: Wed Dec 03 10:00:00 +0800 2025)
                    # 这里做简单的格式尝试，根据实际爬虫返回格式调整
                    try:
                        dt = datetime.strptime(created_at, '%a %b %d %H:%M:%S %z %Y')
                    except:
                        # 如果解析失败，尝试使用当前时间或跳过
                        continue

                    data_list.append({
                        'created_at': dt,
                        'text': text_clean,
                        'hashtags': re.findall(r'#([^#]+)#', text_clean)
                    })
                except json.JSONDecodeError:
                    continue
        
        self.df = pd.DataFrame(data_list)
        print(f"数据加载完成，共清洗有效微博 {len(self.df)} 条")
        return True
    
    # 分析关键词的时间趋势
    def analyze_trends(self, keywords, interval='M'):
        print("\n正在进行时间趋势分析...")
        self.keywords = keywords
        
        # 设置时间索引
        self.df.set_index('created_at', inplace=True)
        
        trend_data = {}
        
        for kw in keywords:
            # 统计包含该关键词的微博数量，按时间重采样
            # 使用 lambda 函数判断文本中是否包含关键词
            mask = self.df['text'].apply(lambda x: kw in x)
            resampled = self.df[mask].resample(interval).size()
            trend_data[kw] = resampled
            
        trend_df = pd.DataFrame(trend_data).fillna(0)
        
        # 保存趋势数据
        trend_df.to_csv('analysis_keyword_trends.csv', encoding='utf-8-sig')
        print("趋势数据已保存至 analysis_keyword_trends.csv")
        
        # 恢复索引
        self.df.reset_index(inplace=True)

    # 分析关键词共现矩阵
    def analyze_cooccurrence(self, keywords):
        print("\n正在进行共现分析...")
        matrix = pd.DataFrame(0, index=keywords, columns=keywords)
        
        for text in self.df['text']:
            found_kws = [kw for kw in keywords if kw in text]
            if len(found_kws) > 1:
                for i in range(len(found_kws)):
                    for j in range(i + 1, len(found_kws)):
                        k1, k2 = found_kws[i], found_kws[j]
                        matrix.loc[k1, k2] += 1
                        matrix.loc[k2, k1] += 1
                        
        matrix.to_csv('analysis_cooccurrence_matrix.csv', encoding='utf-8-sig')
        print("共现矩阵已保存至 analysis_cooccurrence_matrix.csv")
        return matrix
    
    # 提取相关的高频话题标签
    def extract_top_hashtags(self, top_n=20):
        print("\n正在提取高频话题...")
        all_hashtags = []
        for tags in self.df['hashtags']:
            all_hashtags.extend(tags)
            
        counter = Counter(all_hashtags)
        
        print("-" * 40)
        print(f"{'热门话题':<20} | {'频次':<10}")
        print("-" * 40)
        for tag, count in counter.most_common(top_n):
            print(f"#{tag:<18} | {count:<10}")
        print("-" * 40)
        
        with open('analysis_top_hashtags.csv', 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['话题', '频次'])
            writer.writerows(counter.most_common(top_n))

if __name__ == "__main__":
    # 报告核心关键词组
    KEYWORDS = [
        '情绪价值', '悦己', '仪式感', '宠物', 'Citywalk', 
        '泡泡玛特', '周边游', '治愈', '平替', '搭子'
    ]
    
    DATA_FILE = 'all_weibos.txt'
    
    analyzer = WeiboAnalyzer(DATA_FILE)
    if analyzer.load_and_clean_data():
        # 1. 趋势分析 (按月)
        analyzer.analyze_trends(KEYWORDS, interval='M')
        
        # 2. 共现分析 (查看哪些词经常一起出现)
        analyzer.analyze_cooccurrence(KEYWORDS)
        
        # 3. 热门话题提取
        analyzer.extract_top_hashtags()