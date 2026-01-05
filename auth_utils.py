from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user
from datetime import datetime
import re

# 注意：这里不导入db，而是在使用时通过参数传递

class AuthUtils:
    """认证工具类"""
    
    @staticmethod
    def validate_username(username):
        """验证用户名"""
        if not username or len(username) < 3 or len(username) > 20:
            return False, "用户名长度必须在3-20个字符之间"
        
        # 只允许字母、数字、下划线
        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            return False, "用户名只能包含字母、数字和下划线"
        
        return True, ""
    
    @staticmethod
    def validate_email(email):
        """验证邮箱"""
        if not email:
            return False, "邮箱不能为空"
        
        # 简单的邮箱格式验证
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            return False, "邮箱格式不正确"
        
        return True, ""
    
    @staticmethod
    def validate_password(password):
        """验证密码"""
        if not password or len(password) < 6:
            return False, "密码长度至少为6个字符"
        
        return True, ""
    
    @staticmethod
    def hash_password(password):
        """生成密码哈希"""
        return generate_password_hash(password)
    
    @staticmethod
    def check_password(password_hash, password):
        """验证密码"""
        return check_password_hash(password_hash, password)
    
    @staticmethod
    def login(user, db_session, remember=False):
        """用户登录 - 需要传入db_session"""
        user.last_login = datetime.utcnow()
        db_session.commit()
        return login_user(user, remember=remember)
    
    @staticmethod
    def logout():
        """用户登出"""
        logout_user()