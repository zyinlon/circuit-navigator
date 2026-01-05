import pandas as pd
from typing import List, Dict
import re

class DataLoader:
    def __init__(self, data_path: str):
        self.data_path = data_path
        self.data = None
        self._load_data()
    
    def _load_data(self):
        """加载数据，不做任何处理"""
        try:
            self.data = pd.read_csv(self.data_path, encoding='utf-8')
            print(f"成功加载数据，共 {len(self.data)} 行")
            
            # 确保列名正确
            self.data.columns = ['ID', '层级路径', '关联文件名称']
            
            # 清理数据
            self.data = self.data.dropna()
            self.data['ID'] = self.data['ID'].astype(str)
            
            print("数据加载完成")
            
        except Exception as e:
            print(f"数据加载失败: {e}")
            raise
    
    def search_keywords_separately(self, field: str, keywords: List[str]) -> pd.DataFrame:
        """
        分别对每个关键词匹配，删除匹配数为0的关键词，再取交集
        """
        if not keywords:
            return pd.DataFrame()
        
        # 存储每个关键词的匹配结果
        keyword_matches = []
        valid_keywords = []
        
        print(f"在字段 '{field}' 中搜索关键词: {keywords}")
        
        for keyword in keywords:
            # 单个关键词匹配
            mask = self.data[field].str.contains(keyword, case=False, na=False)
            match_df = self.data[mask].copy()
            
            print(f"  关键词 '{keyword}' 匹配到 {len(match_df)} 行")
            
            if not match_df.empty:
                keyword_matches.append(match_df)
                valid_keywords.append(keyword)
            else:
                print(f"  关键词 '{keyword}' 匹配结果为0，将被忽略")
        
        print(f"在字段 '{field}' 中，有效关键词: {valid_keywords}")
        
        if not keyword_matches:
            return pd.DataFrame()
        
        # 取交集：需要所有有效关键词都匹配的行
        # 方法：通过ID取交集
        common_ids = set(keyword_matches[0]['ID'].tolist())
        
        for i in range(1, len(keyword_matches)):
            current_ids = set(keyword_matches[i]['ID'].tolist())
            common_ids = common_ids & current_ids
        
        # 返回交集结果
        if common_ids:
            result = self.data[self.data['ID'].isin(common_ids)].copy()
            print(f"在字段 '{field}' 中，取交集后结果: {len(result)} 行")
            return result
        else:
            print(f"在字段 '{field}' 中，有效关键词没有共同匹配的行")
            return pd.DataFrame()
    
    def search_in_field(self, field: str, keywords: List[str]) -> pd.DataFrame:
        """
        在指定字段中搜索关键词
        返回所有关键词都匹配的行（交集）
        """
        if not keywords:
            return pd.DataFrame()
        
        # 初始化为全部为True的掩码
        mask = pd.Series([True] * len(self.data))
        
        for keyword in keywords:
            if keyword:  # 确保关键词非空
                # 在该字段中搜索关键词（不区分大小写）
                keyword_mask = self.data[field].str.contains(keyword, case=False, na=False)
                mask = mask & keyword_mask
        
        return self.data[mask].copy()
    
    def filter_by_selection(self, 
                           current_results: pd.DataFrame, 
                           selection: str, 
                           filter_field: str, 
                           filter_logic: str) -> pd.DataFrame:
        """根据用户选择筛选结果"""
        if current_results.empty:
            return current_results
        
        # 清理选择文本
        cleaned_selection = self._clean_selection_text(selection)
        
        print(f"筛选条件：字段={filter_field}, 逻辑={filter_logic}, 值='{selection}' (清理后='{cleaned_selection}')")
        
        # 尝试不同的匹配策略
        results = self._try_filter_strategies(current_results, cleaned_selection, filter_field, filter_logic)
        
        return results
    
    def _clean_selection_text(self, selection: str) -> str:
        """清理选择文本，移除描述性内容"""
        # 移除括号及括号内的内容
        cleaned = re.sub(r'（[^）]*）', '', selection)  # 中文括号
        cleaned = re.sub(r'\([^)]*\)', '', cleaned)  # 英文括号
        cleaned = re.sub(r'\[[^\]]*\]', '', cleaned)  # 方括号
        cleaned = re.sub(r'【[^】]*】', '', cleaned)  # 方括号
        
        # 移除常见的描述性短语
        descriptive_phrases = [
            '完整的', '特定的', '相关', '文档', '文件', '图纸',
            '通常含', '包含', '如', '例如', '比如', '不确定', '都需要看看',
            '仪表电路图（文件名称通常含', '针脚定义文档'
        ]
        for phrase in descriptive_phrases:
            cleaned = cleaned.replace(phrase, '')
        
        # 清理空格和标点
        cleaned = cleaned.strip(' ，、。,.')
        
        return cleaned if cleaned else selection
    
    def _try_filter_strategies(self, current_results: pd.DataFrame, selection: str, filter_field: str, filter_logic: str) -> pd.DataFrame:
        """尝试不同的筛选策略"""
        strategies = [
            # 策略1: 完全匹配
            lambda df, sel, field: df[field] == sel,
            
            # 策略2: 包含匹配
            lambda df, sel, field: df[field].str.contains(sel, case=False, na=False),
            
            # 策略3: 部分关键词匹配
            lambda df, sel, field: self._partial_keyword_match(df, sel, field),
            
            # 策略4: 提取关键词匹配
            lambda df, sel, field: self._extract_keywords_match(df, sel, field),
        ]
        
        for strategy in strategies:
            try:
                if filter_logic == "包含" or "等于":
                    mask = strategy(current_results, selection, filter_field)
                    filtered = current_results[mask].copy()
                    
                    if not filtered.empty:
                        print(f"  筛选成功，匹配到 {len(filtered)} 行")
                        return filtered
            except Exception as e:
                print(f"  筛选策略失败: {e}")
                continue
        
        print(f"  所有筛选策略都未匹配到结果")
        return pd.DataFrame()
    
    def _partial_keyword_match(self, df: pd.DataFrame, selection: str, field: str) -> pd.Series:
        """部分关键词匹配"""
        # 如果选择文本较长，尝试使用其中的关键词
        if len(selection) > 4:
            # 提取中文关键词
            keywords = re.findall(r'[\u4e00-\u9fff]{2,}', selection)
            if keywords:
                mask = pd.Series([False] * len(df))
                for keyword in keywords:
                    mask = mask | df[field].str.contains(keyword, case=False, na=False)
                return mask
        
        # 默认返回全False
        return pd.Series([False] * len(df))
    
    def _extract_keywords_match(self, df: pd.DataFrame, selection: str, field: str) -> pd.Series:
        """提取关键词匹配"""
        # 常见的技术关键词
        tech_keywords = [
            '电路图', '原理图', '接线图', '针脚', '定义', '仪表',
            '发动机', '底盘', '电气', 'ECU', 'BCM', 'VECU', '保险丝', '继电器'
        ]
        
        mask = pd.Series([False] * len(df))
        
        # 检查选择文本中是否包含技术关键词
        for keyword in tech_keywords:
            if keyword in selection:
                mask = mask | df[field].str.contains(keyword, case=False, na=False)
        
        return mask