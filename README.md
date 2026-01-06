## README.md

### 智能车辆电路图导航助手

一个基于大语言模型的对话式车辆电路图检索系统，通过多轮对话帮助用户快速定位所需文档。

---

### 项目概述

本项目实现了一个智能Chatbot，能够理解用户关于车辆电路图的自然语言查询，从CSV资料库中检索相关文档，并通过选择题引导用户精准定位目标图纸。

### 核心功能

✅ **意图理解与关键词提取**
- 使用DeepSeek大模型自动提取搜索关键词
- 支持模糊查询修正（如"小忪"→"小松"）

✅ **智能检索算法**
- 在"层级路径"和"文件名称"两个字段中交叉搜索
- 采用两两关键词交集策略，提高匹配准确性
- 按匹配度排序返回结果

✅ **多轮对话引导**
- 结果>5个时自动生成交互式选择题
- 动态分析当前结果集特征，生成3-5个筛选选项
- 支持点击选项直接筛选

✅ **对话管理**
- 返回上一步功能（保存状态栈）
- 重置对话功能
- 查看当前所有结果

✅ **用户系统**
- 用户注册/登录
- 对话历史保存与加载
- 历史记录管理（查看、加载、删除）

### 技术栈

- **后端**：Flask + Python 3.9.25
- **数据库**：SQLAlchemy（支持SQLite/PostgreSQL）
- **大语言模型**：DeepSeek API（deepseek-chat / deepseek-reasoner）
- **前端**：原生HTML/CSS/JavaScript
- **部署支持**：Gunicorn + Railway

### 项目结构

```
Chatbot/
├── app.py                  # Flask主应用
├── config.py              # 配置文件（支持环境变量）
├── models.py              # 数据库模型（User/Conversation/Message）
├── auth_utils.py          # 认证工具
├── requirements.txt       # Python依赖
├── runtime.txt           # Python版本(3.9.25)
├── Procfile              # Railway启动配置
├── .gitignore            # Git忽略文件
├── data/
│   └── 资料清单.csv       # 电路图资料库
├── utils/
│   ├── data_loader.py     # 数据加载与搜索
│   ├── retrieval.py       # 检索引擎
│   ├── llm_client.py      # 大模型客户端
│   └── dialogue_manager.py # 对话状态管理
├── static/
│   ├── css/style.css      # 样式文件
│   └── js/script.js       # 前端交互
└── templates/
    ├── index.html         # 主聊天界面
    ├── login.html         # 登录页
    └── register.html      # 注册页
```

### 本地运行

1. **安装依赖**
```bash
pip install -r requirements.txt
```

2. **配置环境变量**
```bash
# 创建.env文件（参考.env.example）
SECRET_KEY=your-secret-key
LLM_API_KEY=sk-your-deepseek-key
```

3. **运行应用**
```bash
python app.py
```

4. **访问**：http://localhost:5000

### Railway部署

1. **推送代码到GitHub**
```bash
git add . && git commit -m "ready for deploy"
git push origin main
```

2. **Railway配置**
   - 新建项目 → 连接GitHub仓库
   - 添加PostgreSQL数据库
   - 配置环境变量：`SECRET_KEY`, `LLM_API_KEY`
   - 自动部署

3. **访问**：Railway提供的`.up.railway.app`域名

### 使用示例

```
用户：我要找东风天龙的仪表电路图

助手：🔍 为您找到32个相关结果。请问您需要的是：
A. 东风天龙KL系列仪表图
B. 东风天龙KC系列仪表图
C. 东风天龙VL系列仪表图
D. 其他（还有12个结果）

用户：A

助手：📊 为您找到3个相关结果：
1. 【ID: 12345】东风天龙KL整车仪表电路图
2. 【ID: 12346】东风天龙KL ECU仪表针脚定义
3. 【ID: 12347】东风天龙KL仪表保险丝布局
```

### 搜索算法说明

1. **两两交集策略**：每两个关键词先取交集，再将所有交集结果合并
2. **字段覆盖**：同时在"层级路径"和"文件名称"中搜索
3. **选项生成**：基于当前结果集提取高频关键词，生成可筛选的选项

### 满足项目要求对照

| 需求项 | 实现情况 |
|--------|----------|
| 意图理解 | ✅ 使用LLM提取关键词，支持模糊修正 |
| 智能检索 | ✅ 双字段搜索+两两交集算法 |
| 多轮对话 | ✅ 选择题引导，动态生成选项 |
| 结果限制 | ✅ 超过5个自动继续提问 |
| 交互体验 | ✅ 支持返回/重置，界面友好 |
| Web部署 | ✅ Flask应用，支持Railway部署 |
| 界面要求 | ✅ 清晰聊天界面，可点击选项 |

---
