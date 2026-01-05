import pandas as pd
from typing import List, Dict, Tuple
import config
import itertools

class CircuitRetriever:
    def __init__(self, data_loader):
        self.data_loader = data_loader
    
    def search(self, keywords: List[str]) -> pd.DataFrame:
        """
        执行完整搜索流程（新策略）：
        1. 层级路径：分别匹配 → 删除为0的 → 两两交集 → 取并集
        2. 文件名：分别匹配 → 删除为0的 → 两两交集 → 取并集
        3. 两者取并集（只要一方有结果就包含）
        4. 按匹配关键词数量排序
        """
        print(f"\n===== 开始搜索，关键词: {keywords} =====")
        
        # 1. 在层级路径中搜索（新策略：两两交集再并集）
        hierarchy_results = self._search_with_pairwise_intersection('层级路径', keywords)
        print(f"层级路径搜索结果: {len(hierarchy_results)} 行")
        
        # 2. 在文件名中搜索（新策略：两两交集再并集）
        filename_results = self._search_with_pairwise_intersection('关联文件名称', keywords)
        print(f"文件名搜索结果: {len(filename_results)} 行")
        
        # 3. 取并集（只要任一字段有匹配就包含）
        if hierarchy_results.empty and filename_results.empty:
            print("两个字段都没有匹配结果")
            return pd.DataFrame()
        elif hierarchy_results.empty:
            print("只有文件名有结果，返回文件名结果")
            union_results = filename_results
        elif filename_results.empty:
            print("只有层级路径有结果，返回层级路径结果")
            union_results = hierarchy_results
        else:
            # 取并集：合并两个结果，去重
            hierarchy_ids = set(hierarchy_results['ID'].tolist())
            filename_ids = set(filename_results['ID'].tolist())
            union_ids = hierarchy_ids | filename_ids  # 并集操作
            
            # 从原始数据中获取所有并集结果
            union_results = self.data_loader.data[
                self.data_loader.data['ID'].isin(union_ids)
            ].copy()
            
            print(f"并集结果: {len(union_results)} 行")
        
        # 4. 按匹配关键词数量排序
        if not union_results.empty and keywords:
            union_results = self._sort_by_keyword_matches(union_results, keywords)
        
        return union_results
    
    def _search_with_pairwise_intersection(self, field: str, keywords: List[str]) -> pd.DataFrame:
        """
        新策略：先两两交集，再取并集
        """
        if not keywords:
            return pd.DataFrame()
        
        print(f"在字段 '{field}' 中搜索关键词: {keywords}")
        
        # 1. 获取每个关键词的匹配结果
        keyword_matches = {}
        valid_keywords = []
        
        for keyword in keywords:
            # 单个关键词匹配
            mask = self.data_loader.data[field].str.contains(keyword, case=False, na=False)
            match_df = self.data_loader.data[mask].copy()
            
            print(f"  关键词 '{keyword}' 匹配到 {len(match_df)} 行")
            
            if not match_df.empty:
                keyword_matches[keyword] = match_df
                valid_keywords.append(keyword)
            else:
                print(f"  关键词 '{keyword}' 匹配结果为0，将被忽略")
        
        print(f"在字段 '{field}' 中，有效关键词: {valid_keywords}")
        
        if not valid_keywords:
            return pd.DataFrame()
        
        # 如果只有一个有效关键词，直接返回该关键词的结果
        if len(valid_keywords) == 1:
            return keyword_matches[valid_keywords[0]]
        
        # 2. 两两取交集，然后取并集
        all_pairwise_ids = set()
        
        # 生成所有两两组合
        keyword_pairs = list(itertools.combinations(valid_keywords, 2))
        print(f"  生成 {len(keyword_pairs)} 个两两组合")
        
        for keyword1, keyword2 in keyword_pairs:
            # 获取两个关键词的结果
            df1 = keyword_matches[keyword1]
            df2 = keyword_matches[keyword2]
            
            # 取交集
            ids1 = set(df1['ID'].tolist())
            ids2 = set(df2['ID'].tolist())
            intersection_ids = ids1 & ids2
            
            if intersection_ids:
                print(f"    组合 '{keyword1}' + '{keyword2}' 交集: {len(intersection_ids)} 行")
                all_pairwise_ids.update(intersection_ids)
            else:
                print(f"    组合 '{keyword1}' + '{keyword2}' 交集: 0 行")
        
        # 3. 返回所有两两交集的并集
        if all_pairwise_ids:
            result = self.data_loader.data[
                self.data_loader.data['ID'].isin(all_pairwise_ids)
            ].copy()
            print(f"在字段 '{field}' 中，两两交集再并集后结果: {len(result)} 行")
            return result
        else:
            print(f"在字段 '{field}' 中，所有两两组合都没有共同匹配的行")
            return pd.DataFrame()
    
    def _sort_by_keyword_matches(self, results: pd.DataFrame, keywords: List[str]) -> pd.DataFrame:
        """按匹配关键词数量排序"""
        def count_matches(text):
            if pd.isna(text):
                return 0
            count = 0
            for keyword in keywords:
                if keyword.lower() in str(text).lower():
                    count += 1
            return count
        
        # 计算总匹配分数
        results['match_score'] = results.apply(
            lambda row: count_matches(row['层级路径']) + count_matches(row['关联文件名称']), 
            axis=1
        )
        
        # 按分数降序排序
        results = results.sort_values('match_score', ascending=False)
        
        # 移除临时列
        results = results.drop('match_score', axis=1)
        
        return results
    
    def format_results_for_display(self, results: pd.DataFrame, max_results: int = None) -> List[Dict]:
        """格式化结果用于显示"""
        if results.empty:
            return []
        
        # 限制结果数量
        if max_results:
            results = results.head(max_results)
        
        formatted = []
        for _, row in results.iterrows():
            formatted.append({
                'ID': row['ID'],
                '层级路径': row['层级路径'],
                '关联文件名称': row['关联文件名称']
            })
        
        return formatted