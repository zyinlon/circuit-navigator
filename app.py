from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_login import LoginManager, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import uuid
import config
import json
from datetime import datetime

app = Flask(__name__)
app.config.from_object(config.Config)
app.secret_key = config.Config.SECRET_KEY

# 导入数据库模型
from models import db, User, Conversation, Message

# 初始化数据库
app.config['SQLALCHEMY_DATABASE_URI'] = config.Config.SQLALCHEMY_DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# 初始化登录管理器
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# 导入其他模块
from utils.data_loader import DataLoader
from utils.retrieval import CircuitRetriever
from utils.llm_client import DeepSeekClient
from utils.dialogue_manager import DialogueManager

# 初始化组件
print("正在初始化数据加载器...")
data_loader = DataLoader(config.Config.DATA_FILE)

print("正在初始化检索器...")
retriever = CircuitRetriever(data_loader)

print("正在初始化大模型客户端...")
llm_client = DeepSeekClient()

print("正在初始化对话管理器...")
dialogue_manager = DialogueManager(data_loader, retriever, llm_client)

print("✅ 初始化完成！")

# 创建数据库表
with app.app_context():
    try:
        db.create_all()
        print("✅ 数据库表创建成功")
    except Exception as e:
        print(f"数据库初始化失败: {e}")
        # Railway上第一次失败是正常的，PostgreSQL还没创建好

# ==================== 认证相关路由 ====================

@app.route('/login', methods=['GET', 'POST'])
def login():
    """登录页面"""
    if request.method == 'GET':
        return render_template('login.html')
    
    # POST请求处理
    data = request.json
    username = data.get('username', '').strip()
    password = data.get('password', '')
    
    # 验证用户
    user = User.query.filter_by(username=username).first()
    
    if user and check_password_hash(user.password_hash, password):
        from auth_utils import AuthUtils
        AuthUtils.login(user, db.session, remember=True)
        return jsonify({
            'success': True,
            'message': '登录成功',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email
            }
        })
    else:
        return jsonify({
            'success': False,
            'message': '用户名或密码错误'
        }), 401

@app.route('/register', methods=['GET', 'POST'])
def register():
    """注册页面"""
    if request.method == 'GET':
        return render_template('register.html')
    
    # POST请求处理
    data = request.json
    username = data.get('username', '').strip()
    email = data.get('email', '').strip()
    password = data.get('password', '')
    
    from auth_utils import AuthUtils
    
    # 验证输入
    valid, message = AuthUtils.validate_username(username)
    if not valid:
        return jsonify({'success': False, 'message': message}), 400
    
    valid, message = AuthUtils.validate_email(email)
    if not valid:
        return jsonify({'success': False, 'message': message}), 400
    
    valid, message = AuthUtils.validate_password(password)
    if not valid:
        return jsonify({'success': False, 'message': message}), 400
    
    # 检查用户名和邮箱是否已存在
    if User.query.filter_by(username=username).first():
        return jsonify({'success': False, 'message': '用户名已存在'}), 400
    
    if User.query.filter_by(email=email).first():
        return jsonify({'success': False, 'message': '邮箱已存在'}), 400
    
    # 创建新用户
    try:
        user = User(
            username=username,
            email=email,
            password_hash=AuthUtils.hash_password(password),
            created_at=datetime.utcnow()
        )
        db.session.add(user)
        db.session.commit()
        
        # 使用新创建的user对象登录
        AuthUtils.login(user, db.session, remember=True)
        
        return jsonify({
            'success': True,
            'message': '注册成功',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'注册失败: {str(e)}'}), 500

@app.route('/logout')
@login_required
def logout():
    """退出登录"""
    from auth_utils import AuthUtils
    AuthUtils.logout()
    return jsonify({'success': True, 'message': '已退出登录'})

@app.route('/check_auth')
def check_auth():
    """检查认证状态"""
    if current_user.is_authenticated:
        return jsonify({
            'authenticated': True,
            'user': {
                'id': current_user.id,
                'username': current_user.username,
                'email': current_user.email
            }
        })
    else:
        return jsonify({'authenticated': False})

# ==================== 历史对话相关路由 ====================

@app.route('/api/conversations', methods=['GET'])
@login_required
def get_conversations():
    """获取用户的所有对话历史"""
    conversations = Conversation.query.filter_by(user_id=current_user.id)\
        .order_by(Conversation.updated_at.desc())\
        .all()
    
    return jsonify({
        'success': True,
        'conversations': [conv.to_dict() for conv in conversations]
    })

@app.route('/api/conversations/<int:conversation_id>', methods=['GET'])
@login_required
def get_conversation(conversation_id):
    """获取特定对话的详细信息"""
    conversation = Conversation.query.filter_by(
        id=conversation_id, 
        user_id=current_user.id
    ).first()
    
    if not conversation:
        return jsonify({'success': False, 'message': '对话不存在'}), 404
    
    messages = Message.query.filter_by(conversation_id=conversation_id)\
        .order_by(Message.timestamp.asc())\
        .all()
    
    return jsonify({
        'success': True,
        'conversation': conversation.to_dict(),
        'messages': [msg.to_dict() for msg in messages]
    })

@app.route('/api/conversations/<int:conversation_id>', methods=['DELETE'])
@login_required
def delete_conversation(conversation_id):
    """删除对话"""
    conversation = Conversation.query.filter_by(
        id=conversation_id, 
        user_id=current_user.id
    ).first()
    
    if not conversation:
        return jsonify({'success': False, 'message': '对话不存在'}), 404
    
    try:
        db.session.delete(conversation)
        db.session.commit()
        return jsonify({'success': True, 'message': '对话已删除'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'删除失败: {str(e)}'}), 500

@app.route('/api/save_conversation', methods=['POST'])
@login_required
def save_conversation():
    """保存当前对话到数据库"""
    data = request.json
    title = data.get('title', '新对话')
    messages = data.get('messages', [])
    
    try:
        # 创建新对话
        conversation = Conversation(
            user_id=current_user.id,
            title=title[:200],  # 限制标题长度
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.session.add(conversation)
        db.session.flush()  # 获取conversation.id
        
        # 保存消息
        for msg_data in messages:
            message = Message(
                conversation_id=conversation.id,
                role=msg_data.get('role', 'user'),
                content=msg_data.get('content', ''),
                message_type=msg_data.get('message_type', 'message'),
                timestamp=datetime.utcnow()
            )
            
            # 保存选项和结果（如果有）
            if 'options' in msg_data:
                message.options = json.dumps(msg_data['options'])
            if 'results' in msg_data:
                message.results = json.dumps(msg_data['results'])
            
            db.session.add(message)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '对话已保存',
            'conversation_id': conversation.id
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'保存失败: {str(e)}'}), 500

# ==================== 原有搜索功能路由 ====================

@app.route('/')
def index():
    """主页面"""
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    """处理聊天请求"""
    user_message = request.json.get('message', '').strip()
    
    if not user_message:
        return jsonify({'error': '消息不能为空'}), 400
    
    # 获取会话ID
    session_id = session.get('session_id', str(uuid.uuid4()))
    
    try:
        session_obj = dialogue_manager.get_session(session_id)
        
        # 检查是否是选项选择（只能通过点击选项触发）
        if user_message in session_obj.available_options:
            # 直接处理选项选择
            response = dialogue_manager._handle_option_selection(session_obj, user_message)
        else:
            # 处理其他类型消息
            response = dialogue_manager.process_query(session_id, user_message)
        
        # 如果是重置响应，需要清除前端历史
        if response.get('type') == 'reset':
            # 返回特殊标记，让前端清空历史
            response['should_clear_history'] = True
        
        return jsonify({
            'success': True,
            'response': response
        })
        
    except Exception as e:
        print(f"处理消息时出错: {e}")
        return jsonify({
            'success': False,
            'error': '处理请求时出错，请重试。'
        }), 500

@app.route('/api/reset', methods=['POST'])
def reset():
    """重置对话"""
    session_id = session.get('session_id')
    if session_id:
        dialogue_manager.reset_session(session_id)
    
    # 生成新的会话ID
    session['session_id'] = str(uuid.uuid4())
    
    return jsonify({
        'success': True,
        'message': '对话已重置'
    })

@app.route('/api/status')
def status():
    """检查服务状态"""
    return jsonify({
        'status': 'ok',
        'data_count': len(data_loader.data) if data_loader.data is not None else 0,
        'initialized': True
    })

@app.route('/api/show_current_results', methods=['POST'])
def show_current_results():
    """查看当前所有结果（不经过大模型）"""
    session_id = session.get('session_id')
    if not session_id:
        return jsonify({'error': '会话不存在'}), 400
    
    try:
        session_obj = dialogue_manager.get_session(session_id)
        
        if session_obj.current_results is None or session_obj.current_results.empty:
            response = {
                'type': 'message',
                'content': '📊 **当前没有搜索结果**\n\n请先进行搜索。'
            }
        else:
            # 格式化当前所有结果
            formatted_results = retriever.format_results_for_display(session_obj.current_results)
            
            # 构建结果消息
            total_count = len(formatted_results)
            message = f"📊 **当前搜索结果（共 {total_count} 条）**\n\n"
            
            for i, result in enumerate(formatted_results, 1):
                message += f"**{i}.** `{result['ID']}` - {result['关联文件名称']}\n"
            
            # 添加统计信息
            if session_obj.current_query:
                message += f"\n🔍 **搜索关键词**：{session_obj.current_query}"
            
            if session_obj.keywords:
                message += f"\n📝 **提取关键词**：{', '.join(session_obj.keywords)}"
            
            if session_obj.previous_questions:
                message += f"\n🔧 **已筛选条件**：{len(session_obj.previous_questions)} 个"
                for j, q in enumerate(session_obj.previous_questions, 1):
                    choice = q.get('user_choice', '未选择')
                    message += f"\n    {j}. {choice}"
            
            response = {
                'type': 'message',
                'content': message
            }
        
        return jsonify({
            'success': True,
            'response': response
        })
        
    except Exception as e:
        print(f"获取当前结果时出错: {e}")
        return jsonify({
            'success': False,
            'error': '获取结果时出错，请重试。'
        }), 500

@app.route('/api/fuzzy_correct', methods=['POST'])
def fuzzy_correct():
    """模糊匹配修正用户输入"""
    user_input = request.json.get('query', '').strip()
    
    if not user_input:
        return jsonify({'error': '输入不能为空'}), 400
    
    try:
        # 使用大模型修正用户输入
        corrected_query = llm_client.fuzzy_correct_query(user_input)
        
        return jsonify({
            'success': True,
            'original': user_input,
            'corrected': corrected_query.get('corrected_query', user_input),
            'explanation': corrected_query.get('explanation', ''),
            'confidence': corrected_query.get('confidence', 'medium')
        })
        
    except Exception as e:
        print(f"模糊匹配修正失败: {e}")
        return jsonify({
            'success': False,
            'error': '修正失败，请重试。'
        }), 500

if __name__ == '__main__':
    app.run(debug=config.Config.DEBUG, host='0.0.0.0', port=5000)