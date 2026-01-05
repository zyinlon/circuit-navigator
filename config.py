# config.py
import os

class Config:
    # Flask配置
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')
    DEBUG = False
    
    # 数据文件
    DATA_FILE = 'data/资料清单.csv'
    
    # 大模型配置
    LLM_API_KEY = os.environ.get('LLM_API_KEY')  # 本地开发可以保留
    LLM_BASE_URL = os.environ.get('LLM_BASE_URL', 'https://api.deepseek.com')
    LLM_MODEL = os.environ.get('LLM_MODEL', 'deepseek-chat')
    LLM_REASONER_MODEL = os.environ.get('LLM_REASONER_MODEL', 'deepseek-reasoner')
    
    # 搜索配置
    MAX_RESULTS_DISPLAY = 5
    MAX_RESULTS_ANALYSIS = 20
    MAX_OPTIONS_DISPLAY = 6
    
    # 数据库配置：关键修改点！
    DATABASE_URL = os.environ.get('DATABASE_URL')
    if DATABASE_URL:
        # Railway生产环境：使用PostgreSQL
        SQLALCHEMY_DATABASE_URI = DATABASE_URL
    else:
        # 本地开发环境：使用SQLite
        base_dir = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(base_dir, 'instance', 'circuit_search.db')
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        SQLALCHEMY_DATABASE_URI = f'sqlite:///{db_path}'
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False