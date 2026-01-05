from typing import Dict, List, Any, Optional
import uuid
import pandas as pd
import re
import json
import config
import random

class DialogueState:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.current_query = ""
        self.keywords = []
        self.current_results = None  # DataFrame
        self.all_search_results = None  # 所有搜索结果（初始搜索，未筛选）
        self.conversation_history = []
        self.current_question = None  # 当前问题信息
        self.available_options = []
        self.previous_questions = []  # 记录之前的问题和选择
        self.filters_applied = []  # 已应用的筛选条件
        self.retry_count = 0  # 问题设计重试次数
        self.state_stack = []  # 用于支持回退的状态栈
        self.analysis_start_index = 0  # 当前分析结果的起始索引
        self.in_guidance_process = False  # 是否在引导过程中
        
    def add_question(self, question_data: Dict, user_choice: str = None):
        """记录问题和用户选择"""
        record = {
            'question': question_data.get('question', ''),
            'options': question_data.get('options', []),
            'filter_field': question_data.get('filter_field', ''),
            'filter_logic': question_data.get('filter_logic', ''),
            'user_choice': user_choice
        }
        self.previous_questions.append(record)
        
    def add_filter(self, filter_info: Dict):
        """记录筛选条件"""
        self.filters_applied.append(filter_info)
        
    def reset_retry_count(self):
        """重置重试计数"""
        self.retry_count = 0
        
    def save_state(self):
        """保存当前状态到栈中"""
        state_snapshot = {
            'current_query': self.current_query,
            'keywords': self.keywords.copy(),
            'current_results': self.current_results.copy() if self.current_results is not None else None,
            'all_search_results': self.all_search_results.copy() if self.all_search_results is not None else None,
            'previous_questions': self.previous_questions.copy(),
            'filters_applied': self.filters_applied.copy(),
            'current_question': self.current_question.copy() if self.current_question else None,
            'available_options': self.available_options.copy(),
            'analysis_start_index': self.analysis_start_index,
            'in_guidance_process': self.in_guidance_process,
            'conversation_history': self.conversation_history.copy()  # 保存对话历史
        }
        self.state_stack.append(state_snapshot)
        # 限制栈大小，防止内存泄漏
        if len(self.state_stack) > 10:
            self.state_stack.pop(0)
            
    def restore_state(self):
        """从栈中恢复上一个状态"""
        if self.state_stack:
            last_state = self.state_stack.pop()
            self.current_query = last_state['current_query']
            self.keywords = last_state['keywords']
            self.current_results = last_state['current_results']
            self.all_search_results = last_state['all_search_results']
            self.previous_questions = last_state['previous_questions']
            self.filters_applied = last_state['filters_applied']
            self.current_question = last_state['current_question']
            self.available_options = last_state['available_options']
            self.analysis_start_index = last_state['analysis_start_index']
            self.in_guidance_process = last_state['in_guidance_process']
            self.conversation_history = last_state['conversation_history']  # 恢复对话历史
            return True
        return False
        
    def clear(self):
        """清空所有状态"""
        self.current_query = ""
        self.keywords = []
        self.current_results = None
        self.all_search_results = None
        self.current_question = None
        self.available_options = []
        self.previous_questions = []
        self.filters_applied = []
        self.retry_count = 0
        self.state_stack = []
        self.analysis_start_index = 0
        self.in_guidance_process = False
        # 保留欢迎消息的历史
        if self.conversation_history:
            self.conversation_history = [self.conversation_history[0]] if self.conversation_history[0].get('role') == 'assistant' else []

class DialogueManager:
    def __init__(self, data_loader, retriever, llm_client):
        self.data_loader = data_loader
        self.retriever = retriever
        self.llm_client = llm_client
        self.sessions = {}
    
    def get_session(self, session_id: str) -> DialogueState:
        if session_id not in self.sessions:
            self.sessions[session_id] = DialogueState(session_id)
        return self.sessions[session_id]
    
    def reset_session(self, session_id: str):
        if session_id in self.sessions:
            # 清空会话状态
            self.sessions[session_id].clear()
    
    def process_query(self, session_id: str, user_input: str) -> Dict:
        """处理用户查询 - 主入口点"""
        session = self.get_session(session_id)
        
        # 检查特殊指令
        if user_input == "/back":
            return self._handle_back_intent(session)
        elif user_input == "/reset":
            return self._handle_reset_intent(session, session_id)
        
        # 记录对话历史
        session.conversation_history.append({
            'role': 'user',
            'content': user_input
        })
        
        # 意图识别 - 只处理搜索相关意图
        intent_result = self._recognize_intent_for_search(session, user_input)
        intent = intent_result.get('intent', 'unknown')
        
        print(f"🔍 意图识别结果: {intent}")
        print(f"意图详情: {intent_result}")
        
        # 根据意图处理
        if intent == 'new_search':
            # 新搜索请求
            return self._handle_new_search_intent(session, session_id, user_input, intent_result)
            
        elif intent == 'provide_clue':
            # 提供线索/补充信息
            return self._handle_clue_intent(session, user_input, intent_result)
            
        elif intent == 'other':
            # 与电路图搜索无关的输入
            return self._handle_other_intent(session, user_input)
            
        else:
            # 未知意图，按其他处理
            return self._handle_other_intent(session, user_input)
    
    def _recognize_intent_for_search(self, session: DialogueState, user_input: str) -> Dict:
        """
        识别用户意图 - 只识别搜索相关意图
        reset和back只能通过按钮触发，option_selection只能通过点击选项触发
        """
        # 使用大模型进行意图识别
        return self._recognize_intent_with_llm(session, user_input)
    
    def _recognize_intent_with_llm(self, session: DialogueState, user_input: str) -> Dict:
        """使用大模型识别意图 - 只识别搜索相关意图"""
        
        # 准备上下文信息
        context = {
            'current_query': session.current_query,
            'has_current_question': bool(session.current_question),
            'current_question': session.current_question.get('question', '') if session.current_question else '',
            'available_options': session.available_options,
            'previous_questions_count': len(session.previous_questions),
            'filters_applied_count': len(session.filters_applied)
        }
        
        prompt = f"""
# 电路图搜索助手意图识别

## 用户输入
"{user_input}"

## 当前对话上下文
- 当前搜索主题: {context['current_query']}
- 是否有进行中的问题: {'是' if context['has_current_question'] else '否'}
{'- 当前问题: ' + context['current_question'] if context['current_question'] else ''}
{'- 当前选项: ' + ', '.join(context['available_options']) if context['available_options'] else ''}
- 已进行的问题轮数: {context['previous_questions_count']}
- 已应用的筛选条件: {context['filters_applied_count']}

## 意图分类（只识别与电路图搜索相关的意图）
1. **新搜索请求 (new_search)** - 用户提出了一个全新的电路图搜索需求
2. **提供线索 (provide_clue)** - 用户在现有搜索基础上提供了额外信息来缩小范围
3. **其他 (other)** - 与电路图搜索无关的输入，包括问候、闲聊等

**注意**：选项选择、返回上一步、重置对话只能通过按钮触发，不在此识别

## 分析要点
- 如果用户描述了一个全新的电路图需求，可能是新搜索意图
- 如果用户在现有搜索基础上提供信息，可能是提供线索
- **如果用户输入与电路图搜索完全无关，返回"other"**

## 电路图搜索相关关键词参考
- 电路图、电路、图纸、接线图、原理图、针脚、线路图
- 车型品牌：东风、三一、徐工、红岩、解放、重汽
- 系统部件：仪表、发动机、底盘、电气、ECU、BCM、保险丝、继电器
- 查询动词：找、需要、查、搜索、定位

## 输出格式
请返回JSON格式：
{{
    "intent": "意图类型",
    "confidence": "high/medium/low",
    "reasoning": "判断理由",
    "additional_info": {{  // 根据意图的附加信息
        "clue_keywords": [],  // 如果是提供线索，提取的关键词
        "new_query": ""       // 如果是新搜索，提取的查询内容
    }}
}}

现在请分析用户输入并返回意图识别结果：
"""
        
        try:
            import openai
            
            response = openai.ChatCompletion.create(
                model=config.Config.LLM_MODEL,
                messages=[
                    {"role": "system", "content": "你是一个意图识别专家，请准确分析用户的意图。"},
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
            print(f"意图识别失败: {e}")
            # 降级到规则匹配
            return self._fallback_intent_recognition(session, user_input)
    
    def _fallback_intent_recognition(self, session: DialogueState, user_input: str) -> Dict:
        """降级意图识别：基于规则"""
        
        # 首先检查是否是明确的电路图搜索意图
        circuit_keywords = [
            '电路图', '电路', '图纸', '接线图', '原理图', '针脚', '线路图',
            '东风', '三一', '徐工', '红岩', '解放', '重汽', '仪表', '发动机',
            '底盘', '电气', 'ECU', 'BCM', '保险丝', '继电器', '找', '需要',
            '查', '搜索', '定位'
        ]
        
        # 检查是否包含电路图搜索相关关键词
        has_circuit_keyword = any(keyword in user_input for keyword in circuit_keywords)
        
        # 检查是否是电路图相关的新查询
        if has_circuit_keyword:
            # 判断是否是全新的查询（没有当前查询，或者与当前查询明显不同）
            if not session.current_query or self._is_significantly_different(session.current_query, user_input):
                return {
                    'intent': 'new_search',
                    'confidence': 'medium',
                    'reasoning': '用户提出了新的电路图搜索需求',
                    'additional_info': {
                        'new_query': user_input
                    }
                }
            else:
                # 现有搜索的补充
                return {
                    'intent': 'provide_clue',
                    'confidence': 'medium',
                    'reasoning': '用户提供了额外的搜索线索',
                    'additional_info': {
                        'clue_keywords': [user_input]
                    }
                }
        
        # 默认：其他（与电路图搜索无关）
        return {
            'intent': 'other',
            'confidence': 'high',
            'reasoning': '用户输入与电路图搜索无关',
            'additional_info': {}
        }
    
    def _is_significantly_different(self, old_query: str, new_query: str) -> bool:
        """判断两个查询是否显著不同"""
        import re
        
        old_words = set(re.findall(r'[\u4e00-\u9fffA-Za-z0-9]+', old_query.lower()))
        new_words = set(re.findall(r'[\u4e00-\u9fffA-Za-z0-9]+', new_query.lower()))
        
        # 计算Jaccard相似度
        intersection = len(old_words & new_words)
        union = len(old_words | new_words)
        
        if union == 0:
            return True
        
        similarity = intersection / union
        return similarity < 0.3
    
    def _handle_other_intent(self, session: DialogueState, user_input: str) -> Dict:
        """处理与电路图搜索无关的输入"""
        # 友好回复一句，并引导回电路图搜索
        friendly_responses = [
            "您好！我是车辆电路图导航助手，主要帮助您查找车辆电路图文档。如果您需要搜索电路图，请告诉我车型、系统或部件名称。",
            "我专注于车辆电路图搜索服务。请告诉我您需要查找的电路图信息，例如：'东风天龙的仪表图'或'三一挖掘机的电路图'。",
            "我是电路图搜索助手，可以帮您快速定位车辆电路图。请输入您的搜索需求，例如：'徐工XE135G的针脚定义'或'红岩杰狮保险丝图纸'。",
            "欢迎使用车辆电路图导航助手！我可以帮您查找各种车辆电路图。请描述您的需求，比如车型和需要的电路图类型。"
        ]
        
        response_content = random.choice(friendly_responses)
        
        # 如果有当前搜索上下文，可以提一下
        if session.current_query:
            response_content += f"\n\n（您当前正在搜索：{session.current_query}）"
        
        response = {
            'type': 'message',
            'content': response_content
        }
        
        session.conversation_history.append({
            'role': 'assistant',
            'content': response.get('content', '')
        })
        
        return response
    
    def _handle_reset_intent(self, session: DialogueState, session_id: str) -> Dict:
        """处理重置意图 - 清空所有状态"""
        # 清空会话状态
        session.clear()
        
        response = {
            'type': 'reset',
            'content': '✅ 对话已重置，您可以开始新的搜索。'
        }
        
        return response
    
    def _handle_back_intent(self, session: DialogueState) -> Dict:
        """处理返回上一步意图"""
        if session.restore_state():
            # 成功恢复状态
            if session.current_question:
                # 返回到问题状态
                response = {
                    'type': 'question',
                    'content': f"✅ 已返回上一步。\n\n{session.current_question.get('analysis', '')}\n\n{session.current_question.get('question', '')}",
                    'options': session.available_options,
                    'filter_field': session.current_question.get('filter_field', '层级路径'),
                    'filter_logic': session.current_question.get('filter_logic', '包含'),
                    'has_results': False
                }
            elif session.current_results is not None and not session.current_results.empty:
                # 返回到结果状态，重新处理结果
                return self._handle_search_results(session, session.current_query, session.current_results)
            else:
                response = {
                    'type': 'message',
                    'content': '✅ 已返回上一步，请继续您的搜索。'
                }
        else:
            # 无法返回
            response = {
                'type': 'message',
                'content': '❌ 已经是第一步，无法返回。'
            }
        
        return response
    
    def _handle_new_search_intent(self, session: DialogueState, session_id: str, user_input: str, intent_result: Dict) -> Dict:
        """处理新搜索意图"""
        # 获取新查询内容
        new_query = intent_result.get('additional_info', {}).get('new_query', user_input)
        
        # 保存当前状态以便回退
        session.save_state()
        
        # 执行新搜索
        session.current_query = new_query
        session.keywords = self.llm_client.extract_keywords(new_query)
        
        # 执行搜索
        session.current_results = self.retriever.search(session.keywords)
        session.all_search_results = session.current_results.copy() if session.current_results is not None else None
        
        # 处理搜索结果
        return self._handle_search_results(session, new_query, session.current_results)
    
    def _handle_clue_intent(self, session: DialogueState, user_input: str, intent_result: Dict) -> Dict:
        """处理提供线索意图"""
        # 保存当前状态以便回退
        session.save_state()
        
        # 如果没有初始搜索结果，先进行搜索
        if session.all_search_results is None or session.all_search_results.empty:
            # 将线索作为新查询
            combined_query = user_input
            session.current_query = combined_query
            session.keywords = self.llm_client.extract_keywords(combined_query)
            session.current_results = self.retriever.search(session.keywords)
            session.all_search_results = session.current_results.copy() if session.current_results is not None else None
        else:
            # 在初始搜索结果中应用线索
            clue_keywords = intent_result.get('additional_info', {}).get('clue_keywords', [user_input])
            
            # 在初始搜索结果中应用线索筛选
            filtered_results = session.all_search_results.copy()
            for keyword in clue_keywords:
                if keyword:
                    # 同时在两个字段中搜索
                    filename_mask = filtered_results['关联文件名称'].str.contains(keyword, case=False, na=False)
                    path_mask = filtered_results['层级路径'].str.contains(keyword, case=False, na=False)
                    combined_mask = filename_mask | path_mask
                    filtered_results = filtered_results[combined_mask]
            
            session.current_results = filtered_results
            session.current_query = f"{session.current_query} {user_input}".strip()
        
        # 处理搜索结果
        return self._handle_search_results(session, session.current_query, session.current_results)
    
    def _handle_search_results(self, session: DialogueState, query: str, results: pd.DataFrame) -> Dict:
        """处理搜索结果"""
        # 注意：这里不再保存状态，由调用者负责保存状态
        
        if results is None or results.empty:
            response = {
                'type': 'message',
                'content': '🔍 抱歉，没有找到相关的电路图。\n\n建议：\n1. 使用更具体的车型或系统名称\n2. 检查关键词是否有误\n3. 尝试不同的表述方式'
            }
        else:
            total_results = len(results)
            
            # 告诉用户总结果数和前5个结果
            top5_results = self.retriever.format_results_for_display(results.head(5))
            message = f"🔍 为您找到 {total_results} 个相关结果。以下是前 5 个结果：\n\n"
            
            for i, result in enumerate(top5_results, 1):
                message += f"{i}. **ID:** {result['ID']} - **文件名称:** {result['关联文件名称']}\n"
            
            # 根据结果数量决定下一步
            if total_results <= config.Config.MAX_RESULTS_DISPLAY:
                # 直接显示所有结果
                formatted_results = self.retriever.format_results_for_display(results)
                response_text = self.llm_client.format_final_results(formatted_results, query)
                
                response = {
                    'type': 'results',
                    'content': response_text,
                    'results': formatted_results,
                    'has_results': True,
                    'results_count': len(formatted_results)
                }
            else:
                # 结果太多，开始引导过程
                session.in_guidance_process = True
                session.analysis_start_index = 0
                return self._start_guidance_process(session, query, results)
        
        session.conversation_history.append({
            'role': 'assistant',
            'content': response.get('content', '')
        })
        
        return response
    
    def _start_guidance_process(self, session: DialogueState, query: str, results: pd.DataFrame) -> Dict:
        """开始引导过程"""
        total_results = len(results)
        start_index = session.analysis_start_index
        end_index = min(start_index + config.Config.MAX_RESULTS_ANALYSIS, total_results)
        
        # 获取当前批次的结果
        current_batch = results.iloc[start_index:end_index]
        remaining_count = total_results - end_index
        
        # 格式化当前批次结果
        formatted_batch = self.retriever.format_results_for_display(current_batch)
        
        # 使用大模型设计问题
        question_data = self.llm_client.design_question_from_results(
            query,
            formatted_batch,
            session.previous_questions
        )
        
        # 准备选项
        options = question_data.get('options', [])
        
        # 如果有剩余结果，添加"其他"选项
        if remaining_count > 0:
            options.append(f"其他（还有{remaining_count}个结果）")
        
        # 限制选项数量
        options = options[:config.Config.MAX_OPTIONS_DISPLAY]
        
        # 更新会话状态
        session.current_question = question_data
        session.available_options = options
        
        # 构建响应消息
        analysis = question_data.get('analysis', '')
        question = question_data.get('question', '')
        
        # 添加当前批次信息
        batch_info = f"\n\n📊 **当前分析批次信息**\n- 正在分析第 {start_index+1}-{end_index} 个结果（共 {total_results} 个）"
        if remaining_count > 0:
            batch_info += f"\n- 后续还有 {remaining_count} 个结果待分析"
        
        response_content = f"{analysis}{batch_info}\n\n{question}"
        
        response = {
            'type': 'question',
            'content': response_content,
            'options': options,
            'filter_field': question_data.get('filter_field', '层级路径'),
            'filter_logic': question_data.get('filter_logic', '包含'),
            'has_results': False
        }
        
        session.conversation_history.append({
            'role': 'assistant',
            'content': response.get('content', '')
        })
        
        return response
    
    def _handle_option_selection(self, session: DialogueState, selection: str) -> Dict:
        """处理用户选择的选项 - 只能通过点击选项触发"""
        if not session.current_question:
            return {'type': 'message', 'content': '请先提出搜索需求。'}
        
        # 保存状态以便回退
        session.save_state()
        
        # 检查是否是"其他"选项
        if "其他" in selection:
            # 更新分析起始索引
            session.analysis_start_index += config.Config.MAX_RESULTS_ANALYSIS
            
            # 检查是否还有结果
            if session.analysis_start_index < len(session.current_results):
                # 继续引导过程
                return self._start_guidance_process(session, session.current_query, session.current_results)
            else:
                # 没有更多结果了
                response = {
                    'type': 'message',
                    'content': '❌ 已经没有更多结果了，请尝试其他搜索条件。'
                }
        else:
            # 应用筛选
            filter_field = session.current_question.get('filter_field', '层级路径')
            filter_logic = session.current_question.get('filter_logic', '包含')
            
            # 记录原始结果数量
            original_count = len(session.current_results)
            
            # 筛选结果
            filtered_results = self.data_loader.filter_by_selection(
                session.current_results,
                selection,
                filter_field,
                filter_logic
            )
            
            print(f"筛选结果：{original_count} -> {len(filtered_results)} 行")
            
            # 更新当前结果
            session.current_results = filtered_results
            
            # 记录问题和选择
            session.add_question(session.current_question, selection)
            
            # 重置问题状态
            session.current_question = None
            session.available_options = []
            
            # 检查结果数量
            if session.current_results.empty:
                # 提供更详细的错误信息
                response = {
                    'type': 'message',
                    'content': f'❌ 根据您选择的"{selection}"，没有找到相关电路图。\n\n可能的原因：\n1. 选项文本与实际数据不匹配\n2. 数据中可能使用不同的表述\n\n建议：\n1. 尝试更简洁的表述（如"仪表电路图"而不是"完整的仪表电路图"）\n2. 使用"返回上一步"选择其他选项\n3. 重新描述您的具体需求'
                }
            else:
                # 继续处理结果
                return self._handle_search_results(session, session.current_query, session.current_results)
        
        session.conversation_history.append({
            'role': 'assistant',
            'content': response.get('content', '')
        })
        
        return response