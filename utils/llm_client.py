import json
import openai
from typing import List, Dict, Any
import config
import re

class DeepSeekClient:
    def __init__(self):
        openai.api_key = config.Config.LLM_API_KEY
        openai.api_base = config.Config.LLM_BASE_URL
        self.chat_model = config.Config.LLM_MODEL
        self.reasoner_model = config.Config.LLM_REASONER_MODEL
    
    def extract_keywords(self, user_query: str) -> List[str]:
        """使用大模型分词，提取关键词（移除'电路图'和'图'）"""
        prompt = f"""
请从用户查询中提取关键词。用户查询是关于车辆电路图搜索的。

要求：
1. 移除"电路图"和"图"这两个词（因为太常见且数据中表达不一致）
2. 提取其他有意义的词或短语
3. 不要合并词，保持原样
4. 保留其他专业术语如"供电"、"模块"、"ECU"等

示例：
用户查询："东风天龙仪表电路图"
输出：{{"keywords": ["东风", "天龙", "仪表"]}}

用户查询："我要找三一SY215C9的液压电脑板"
输出：{{"keywords": ["三一", "SY215C9", "液压", "电脑板"]}}

用户查询："供电模块相关图纸"
输出：{{"keywords": ["供电", "模块"]}}

用户查询："解放J6的整车电路图"
输出：{{"keywords": ["解放", "J6", "整车"]}}

现在请处理这个查询：
用户查询："{user_query}"

请以JSON格式返回，格式为：{{"keywords": ["关键词1", "关键词2", ...]}}
"""
        
        try:
            response = openai.ChatCompletion.create(
                model=self.chat_model,
                messages=[
                    {"role": "system", "content": "你是一个关键词提取助手，请准确提取用户查询中的关键词。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=500
            )
            
            content = response.choices[0].message.content.strip()
            
            # 清理JSON
            if content.startswith('```json'):
                content = content[7:-3]
            elif content.startswith('```'):
                content = content[3:-3]
            
            result = json.loads(content)
            keywords = result.get('keywords', [])
            
            # 确保都是字符串且非空
            keywords = [str(kw).strip() for kw in keywords if str(kw).strip()]
            
            print(f"提取到的关键词（已移除'电路图'和'图'）: {keywords}")
            return keywords
            
        except Exception as e:
            print(f"大模型分词失败: {e}")
            # 不进行降级，返回空列表
            return []
    
    def fuzzy_correct_query(self, user_query: str) -> Dict[str, Any]:
        """使用大模型对用户输入进行模糊匹配修正"""
        prompt = f"""
# 车辆电路图查询模糊匹配修正

## 用户原始查询
"{user_query}"

## 任务说明
请对用户的电路图搜索查询进行智能修正。用户可能输入了错别字、简写、口语化表达或不规范表述，需要修正为标准化的车辆电路图搜索术语。

## 常见的需要修正的情况
1. **品牌型号错别字**：
   - "小忪" → "小松"（工程机械品牌）
   - "重汽豪汉" → "重汽豪瀚"（重汽车型）
   - "庆龄" → "庆铃"（汽车品牌）
   - "徐工挖机" → "徐工挖掘机"

2. **数字误写**：
   - "2ooo" → "2000"
   - "25o" → "250"
   - "三一215" → "三一SY215" 或 "三一215"

3. **口语化/不完整表达**：
   - "供电的图" → "供电电路图"
   - "发动机线路" → "发动机电路图"
   - "仪表盘的图" → "仪表电路图"

4. **型号规格补全**：
   - "XE135" → "XE135G"（徐工挖掘机）
   - "天龙D" → "天龙D320"（东风车型）
   - "SY215" → "SY215C9"（三一挖掘机）

## 修正原则
1. **准确性优先**：不确定的不要乱改
2. **保持原意**：只修正明显的错误，不改变用户意图
3. **专业规范**：修正为行业通用术语
4. **补充完整**：补充常见的型号后缀

## 已知品牌型号参考
- 挖掘机：小松PC200、PC300、PC360；三一SY215、SY235、SY285；徐工XE135、XE150、XE210
- 卡车：东风天龙、天锦；重汽豪瀚、豪沃；解放J6、J7；红岩杰狮、杰豹
- 其他：庆铃、江铃、福田

## 输出格式
请返回JSON格式：
{{
    "original_query": "原始查询",
    "corrected_query": "修正后的查询",
    "explanation": "修正说明，解释做了哪些修改",
    "confidence": "high/medium/low"  // 修正置信度
}}

现在请分析和修正用户查询：
"""
        
        try:
            response = openai.ChatCompletion.create(
                model=self.chat_model,
                messages=[
                    {"role": "system", "content": "你是一个车辆电路图搜索专家，擅长识别和修正不规范的查询表述。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=800
            )
            
            content = response.choices[0].message.content.strip()
            
            # 清理JSON
            if content.startswith('```json'):
                content = content[7:-3]
            elif content.startswith('```'):
                content = content[3:-3]
            
            result = json.loads(content)
            return result
            
        except Exception as e:
            print(f"模糊匹配修正失败: {e}")
            # 返回原始查询作为备选
            return {
                "original_query": user_query,
                "corrected_query": user_query,
                "explanation": "修正失败，使用原始查询",
                "confidence": "low"
            }
    
    def design_question_from_results(self, 
                                   user_query: str, 
                                   results: List[Dict],
                                   previous_questions: List[Dict] = None) -> Dict:
        """根据搜索结果设计选择题 - 使用reasoner模型进行推理"""
        
        # 准备结果信息
        results_info = []
        for result in results:
            results_info.append({
                'ID': result['ID'],
                '层级路径': result['层级路径'],
                '关联文件名称': result['关联文件名称']
            })
        
        # 分析当前批次结果的特征
        batch_count = len(results)
        
        # 从结果中提取可能的选项
        extracted_options = self._extract_potential_options(results)
        
        prompt = f"""
# 车辆电路图搜索问题设计

## 用户查询分析
用户查询："{user_query}"

## 当前批次结果分析
正在分析 {batch_count} 个结果，设计问题帮助用户进一步筛选。

## 结果样本
{json.dumps(results_info, ensure_ascii=False, indent=2)}

## 提取的潜在选项（基于实际数据）
{json.dumps(extracted_options, ensure_ascii=False, indent=2)}

## 设计任务
请设计一个选择题来帮助用户缩小范围。请基于实际数据设计具体的、可筛选的选项。

### 关键要求：
1. **选项必须具体**：每个选项应该是用户可以直接选择的具体值，而不是描述性语言
2. **基于实际数据**：选项应来自提取的潜在选项或结果中的具体值
3. **可筛选性**：每个选项必须能在指定字段中找到匹配（通过"包含"逻辑）
4. **简洁明了**：选项应该简洁，避免括号中的解释

### 选项设计示例：
❌ 错误示例（过于描述性）：
- "完整的仪表电路图（文件名称通常含'仪表电路图'）"
- "特定控制模块（如BCM，VECU）的针脚定义文档"

✅ 正确示例（具体可筛选）：
- "仪表电路图"
- "针脚定义"
- "东风天龙仪表"
- "BCM针脚定义"

### 输出格式：
{{
    "analysis": "对当前批次结果的分析，说明设计问题的依据",
    "question": "给用户的清晰问题",
    "options": ["具体选项1", "具体选项2", "具体选项3"],
    "filter_field": "关联文件名称",  // 或"层级路径"
    "filter_logic": "包含",  // 使用"包含"而不是"等于"
    "design_reasoning": "详细说明每个选项的设计依据和有效性"
}}

现在请根据上面的分析设计问题：
"""
        
        try:
            response = openai.ChatCompletion.create(
                model=self.reasoner_model,
                messages=[
                    {"role": "system", "content": "你是一个专业的电路图搜索助手，擅长通过数据分析设计有效的问题。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=1500
            )
            
            content = response.choices[0].message.content.strip()
            
            # 清理JSON
            if content.startswith('```json'):
                content = content[7:-3]
            elif content.startswith('```'):
                content = content[3:-3]
            
            result = json.loads(content)
            
            # 验证并优化选项
            validated_result = self._validate_and_optimize_options(result, results)
            return validated_result
            
        except Exception as e:
            print(f"推理模型设计问题失败: {e}")
            # 使用提取的选项作为备选
            return {
                "analysis": f"分析了当前 {batch_count} 个结果，发现以下特征：",
                "question": "请选择您需要的文档类型：",
                "options": extracted_options.get('filename_keywords', ['仪表电路图', '针脚定义'])[:5],
                "filter_field": "关联文件名称",
                "filter_logic": "包含",
                "design_reasoning": "基于文件名关键词提取"
            }
    
    def _extract_potential_options(self, results: List[Dict]) -> Dict:
        """从结果中提取潜在的选项"""
        if not results:
            return {"filename_keywords": [], "path_keywords": []}
        
        filename_keywords = set()
        path_keywords = set()
        
        # 常见的关键词模式
        common_patterns = [
            r'【([^】]+)】',  # 方括号内的内容
            r'\[([^\]]+)\]',  # 方括号内的内容
            r'\(([^)]+)\)',  # 圆括号内的内容
        ]
        
        # 常见的关键词
        common_keywords = [
            '仪表电路图', '针脚定义', '原理图', '接线图', '电路原理',
            '整车', '仪表', '发动机', '底盘', '电气', 'ECU', 'BCM', 'VECU',
            '保险丝', '继电器', '传感器', '东风', '天龙', '三一', '徐工', '红岩'
        ]
        
        for result in results:
            # 从文件名中提取
            filename = result['关联文件名称']
            
            # 提取模式匹配的内容
            for pattern in common_patterns:
                matches = re.findall(pattern, filename)
                for match in matches:
                    if match and len(match) >= 2:
                        filename_keywords.add(match)
            
            # 检查常见关键词
            for keyword in common_keywords:
                if keyword in filename:
                    filename_keywords.add(keyword)
            
            # 从层级路径中提取
            path = result['层级路径']
            path_parts = path.split('->')
            for part in path_parts:
                part = part.strip()
                if part and len(part) > 1 and part not in ['电路图', '整车', '资料']:
                    path_keywords.add(part)
        
        return {
            "filename_keywords": list(filename_keywords)[:10],  # 限制数量
            "path_keywords": list(path_keywords)[:10]
        }
    
    def _validate_and_optimize_options(self, question_data: Dict, results: List[Dict]) -> Dict:
        """验证并优化选项，确保每个选项都能在结果中找到"""
        options = question_data.get('options', [])
        filter_field = question_data.get('filter_field', '关联文件名称')
        filter_logic = question_data.get('filter_logic', '包含')
        
        # 清理选项：移除括号中的解释和多余的描述
        cleaned_options = []
        for option in options:
            # 移除括号及括号内的内容
            cleaned = re.sub(r'（[^）]*）', '', option)  # 中文括号
            cleaned = re.sub(r'\([^)]*\)', '', cleaned)  # 英文括号
            cleaned = re.sub(r'\[[^\]]*\]', '', cleaned)  # 方括号
            cleaned = re.sub(r'【[^】]*】', '', cleaned)  # 方括号
            
            # 移除常见的描述性短语
            descriptive_phrases = [
                '完整的', '特定的', '相关', '文档', '文件', '图纸',
                '通常含', '包含', '如', '例如', '比如'
            ]
            for phrase in descriptive_phrases:
                cleaned = cleaned.replace(phrase, '')
            
            # 清理空格和标点
            cleaned = cleaned.strip(' ，、。,.')
            if cleaned:
                cleaned_options.append(cleaned)
        
        # 如果清理后选项为空，使用原始选项
        if not cleaned_options:
            cleaned_options = options
        
        # 验证每个选项是否能在结果中找到
        valid_options = []
        for option in cleaned_options:
            found = False
            
            # 首先尝试精确匹配
            for result in results:
                field_value = str(result[filter_field])
                if filter_logic == "包含" and option in field_value:
                    found = True
                    break
                elif filter_logic == "等于" and option == field_value:
                    found = True
                    break
            
            # 如果精确匹配失败，尝试部分匹配（使用选项中的关键词）
            if not found and len(option) > 2:
                # 尝试将选项拆分为关键词
                keywords = re.findall(r'[\u4e00-\u9fffA-Za-z0-9]{2,}', option)
                for keyword in keywords:
                    for result in results:
                        field_value = str(result[filter_field])
                        if keyword in field_value:
                            found = True
                            valid_options.append(keyword)  # 使用关键词作为选项
                            break
                    if found:
                        break
            
            # 如果找到匹配，使用原始选项
            if found and option not in valid_options:
                valid_options.append(option)
        
        # 如果有效选项不足，从结果中提取
        if len(valid_options) < 2:
            # 从文件名中提取常见关键词
            for result in results:
                filename = result['关联文件名称']
                # 提取长度2-6的中文词
                chinese_words = re.findall(r'[\u4e00-\u9fff]{2,6}', filename)
                for word in chinese_words:
                    if word not in valid_options and len(word) >= 2:
                        valid_options.append(word)
                        if len(valid_options) >= 5:
                            break
                if len(valid_options) >= 5:
                    break
        
        # 更新问题数据
        question_data['options'] = valid_options[:5]  # 限制最多5个选项
        
        # 更新分析说明
        if len(valid_options) < len(options):
            original_analysis = question_data.get('analysis', '')
            question_data['analysis'] = f"{original_analysis}\n\n注意：已优化选项以确保可筛选性。"
        
        return question_data
    
    def format_final_results(self, results: List[Dict], query: str) -> str:
        """格式化最终结果"""
        if not results:
            return "抱歉，没有找到相关的电路图。请尝试更换关键词重新搜索。"
        
        if len(results) == 1:
            result = results[0]
            return (
                f"✅ **已为您找到精确匹配的电路图**\n\n"
                f"📄 **文档标题**：{result['关联文件名称']}\n"
                f"🔢 **文档ID**：{result['ID']}\n"
                f"📁 **分类**：{result['层级路径']}"
            )
        else:
            formatted = f"✅ **为您找到 {len(results)} 个相关结果**\n\n"
            
            for i, result in enumerate(results, 1):
                formatted += f"**结果 {i}：**\n"
                formatted += f"📄 **文档标题**：{result['关联文件名称']}\n"
                formatted += f"🔢 **文档ID**：{result['ID']}\n"
                formatted += f"📁 **分类**：{result['层级路径']}\n"
                
                if i < len(results):
                    formatted += f"────────────────────\n\n"
                else:
                    formatted += "\n"
            
            return formatted