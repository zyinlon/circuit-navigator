document.addEventListener('DOMContentLoaded', function() {
    const chatHistory = document.getElementById('chatHistory');
    const messageInput = document.getElementById('messageInput');
    const sendButton = document.getElementById('sendButton');
    const resetButton = document.getElementById('resetButton');
    const backButton = document.getElementById('backButton');
    const showResultsButton = document.getElementById('showResultsButton');
    const fuzzyMatchButton = document.getElementById('fuzzyMatchButton');
    const saveConversationBtn = document.getElementById('saveConversationBtn');
    const optionsContainer = document.getElementById('optionsContainer');
    
    // 用户相关元素
    const loginBtn = document.getElementById('loginBtn');
    const registerBtn = document.getElementById('registerBtn');
    const logoutBtn = document.getElementById('logoutBtn');
    const historyBtn = document.getElementById('historyBtn');
    const usernameDisplay = document.getElementById('usernameDisplay');
    const userInfo = document.getElementById('userInfo');
    const loginRegister = document.getElementById('loginRegister');
    
    // 模态窗口元素
    const fuzzyMatchModal = document.getElementById('fuzzyMatchModal');
    const closeModal = document.querySelector('.close-modal');
    const useCorrectedBtn = document.getElementById('useCorrectedBtn');
    const cancelBtn = document.getElementById('cancelBtn');
    const originalQueryText = document.getElementById('originalQueryText');
    const correctedQueryText = document.getElementById('correctedQueryText');
    const explanationText = document.getElementById('explanationText');
    const confidenceText = document.getElementById('confidenceText');
    
    // 历史对话模态窗口元素
    const historyModal = document.getElementById('historyModal');
    const closeHistoryModal = document.querySelector('.close-history-modal');
    const historyList = document.getElementById('historyList');
    
    // 保存对话模态窗口元素
    const saveConversationModal = document.getElementById('saveConversationModal');
    const closeSaveModal = document.querySelector('.close-save-modal');
    const conversationTitle = document.getElementById('conversationTitle');
    const titleError = document.getElementById('titleError');
    const confirmSaveBtn = document.getElementById('confirmSaveBtn');
    const cancelSaveBtn = document.getElementById('cancelSaveBtn');
    
    // 存储修正后的查询
    let currentCorrectedQuery = '';
    
    // 存储当前对话消息
    let conversationMessages = [];
    
    // 初始化
    checkServerStatus();
    checkAuthStatus();
    
    // 发送消息
    sendButton.addEventListener('click', sendMessage);
    messageInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });
    
    // 重置对话 - 发送特殊指令
    resetButton.addEventListener('click', function() {
        if (confirm('确定要重置对话吗？这将清除所有历史记录。')) {
            messageInput.value = '/reset';
            sendMessage();
        }
    });
    
    // 返回上一步 - 发送特殊指令
    backButton.addEventListener('click', function() {
        messageInput.value = '/back';
        sendMessage();
    });
    
    // 查看当前结果
    showResultsButton.addEventListener('click', showCurrentResults);
    
    // 模糊匹配按钮点击事件
    fuzzyMatchButton.addEventListener('click', function() {
        const query = messageInput.value.trim();
        if (!query) {
            alert('请输入查询内容后再使用模糊匹配功能。');
            return;
        }
        
        showFuzzyMatchModal(query);
    });
    
    // 保存对话按钮点击事件
    saveConversationBtn.addEventListener('click', function() {
        if (conversationMessages.length === 0) {
            alert('当前没有对话内容可保存。');
            return;
        }
        showSaveConversationModal();
    });
    
    // 用户相关按钮事件
    if (loginBtn) {
        loginBtn.addEventListener('click', function() {
            window.location.href = '/login';
        });
    }
    
    if (registerBtn) {
        registerBtn.addEventListener('click', function() {
            window.location.href = '/register';
        });
    }
    
    if (logoutBtn) {
        logoutBtn.addEventListener('click', function() {
            if (confirm('确定要退出登录吗？')) {
                fetch('/logout')
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            window.location.reload();
                        }
                    });
            }
        });
    }
    
    if (historyBtn) {
        historyBtn.addEventListener('click', function() {
            showHistoryModal();
        });
    }
    
    // 模糊匹配模态窗口关闭事件
    closeModal.addEventListener('click', function() {
        fuzzyMatchModal.style.display = 'none';
    });
    
    cancelBtn.addEventListener('click', function() {
        fuzzyMatchModal.style.display = 'none';
    });
    
    // 使用修正后查询
    useCorrectedBtn.addEventListener('click', function() {
        if (currentCorrectedQuery) {
            messageInput.value = currentCorrectedQuery;
            fuzzyMatchModal.style.display = 'none';
            // 可选：自动发送修正后的查询
            // sendMessage();
        }
    });
    
    // 历史对话模态窗口关闭事件
    if (closeHistoryModal) {
        closeHistoryModal.addEventListener('click', function() {
            historyModal.style.display = 'none';
        });
    }
    
    // 保存对话模态窗口关闭事件
    if (closeSaveModal) {
        closeSaveModal.addEventListener('click', function() {
            saveConversationModal.style.display = 'none';
        });
    }
    
    if (cancelSaveBtn) {
        cancelSaveBtn.addEventListener('click', function() {
            saveConversationModal.style.display = 'none';
        });
    }
    
    // 确认保存对话
    if (confirmSaveBtn) {
        confirmSaveBtn.addEventListener('click', function() {
            saveConversation();
        });
    }
    
    // 点击模态窗口外部关闭
    window.addEventListener('click', function(event) {
        if (event.target === fuzzyMatchModal) {
            fuzzyMatchModal.style.display = 'none';
        }
        if (event.target === historyModal) {
            historyModal.style.display = 'none';
        }
        if (event.target === saveConversationModal) {
            saveConversationModal.style.display = 'none';
        }
    });
    
    function sendMessage() {
        const message = messageInput.value.trim();
        if (!message) return;
        
        // 添加用户消息到界面
        addMessage(message, 'user');
        
        // 记录对话消息
        conversationMessages.push({
            role: 'user',
            content: message,
            timestamp: new Date().toISOString()
        });
        
        // 显示加载状态
        showLoading();
        
        // 清空输入框
        messageInput.value = '';
        
        // 隐藏选项容器
        hideOptions();
        
        // 发送请求
        fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ message: message })
        })
        .then(response => response.json())
        .then(data => {
            // 移除加载状态
            removeLoading();
            
            if (data.success) {
                // 检查是否需要清空历史（重置操作）
                if (data.response.should_clear_history) {
                    clearChatHistory();
                    addWelcomeMessage();
                    // 清空对话消息记录
                    conversationMessages = [];
                }
                
                handleResponse(data.response);
            } else {
                addMessage('抱歉，处理您的请求时出现了错误。请稍后重试。', 'assistant');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            removeLoading();
            addMessage('网络连接出现问题，请检查您的网络连接。', 'assistant');
        });
    }
    
    function showCurrentResults() {
        // 显示加载状态
        showLoading();
        
        // 发送请求
        fetch('/api/show_current_results', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        })
        .then(response => response.json())
        .then(data => {
            // 移除加载状态
            removeLoading();
            
            if (data.success) {
                // 直接显示结果，不经过大模型
                addMessage(data.response.content, 'assistant');
                
                // 记录助手消息
                conversationMessages.push({
                    role: 'assistant',
                    content: data.response.content,
                    timestamp: new Date().toISOString()
                });
            } else {
                addMessage('抱歉，获取当前结果时出现了错误。请先进行搜索。', 'assistant');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            removeLoading();
            addMessage('网络连接出现问题，请检查您的网络连接。', 'assistant');
        });
    }
    
    function showFuzzyMatchModal(query) {
        // 显示加载状态
        showLoading();
        
        // 发送模糊匹配请求
        fetch('/api/fuzzy_correct', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ query: query })
        })
        .then(response => response.json())
        .then(data => {
            // 移除加载状态
            removeLoading();
            
            if (data.success) {
                // 更新模态窗口内容
                originalQueryText.textContent = data.original;
                correctedQueryText.textContent = data.corrected;
                explanationText.textContent = data.explanation;
                
                // 设置置信度样式
                confidenceText.textContent = data.confidence;
                confidenceText.className = `confidence-${data.confidence}`;
                
                // 保存修正后的查询
                currentCorrectedQuery = data.corrected;
                
                // 显示模态窗口
                fuzzyMatchModal.style.display = 'block';
            } else {
                alert('模糊匹配修正失败，请重试。');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            removeLoading();
            alert('网络连接出现问题，请检查您的网络连接。');
        });
    }
    
    function handleResponse(response) {
        if (response.type === 'question') {
            // 显示大模型的分析和问题
            addMessage(response.content, 'assistant');
            
            // 记录助手消息
            conversationMessages.push({
                role: 'assistant',
                content: response.content,
                message_type: 'question',
                options: response.options,
                timestamp: new Date().toISOString()
            });
            
            // 显示选项按钮
            showOptions(response.options);
        } else if (response.type === 'results') {
            // 直接显示助手已经格式化好的内容
            addMessage(response.content, 'assistant');
            
            // 记录助手消息
            conversationMessages.push({
                role: 'assistant',
                content: response.content,
                message_type: 'results',
                results: response.results,
                timestamp: new Date().toISOString()
            });
        } else if (response.type === 'reset') {
            // 重置响应，已经在前端清空历史，这里只显示重置消息
            addMessage(response.content, 'assistant');
        } else {
            // 普通消息
            addMessage(response.content, 'assistant');
            
            // 记录助手消息
            conversationMessages.push({
                role: 'assistant',
                content: response.content,
                timestamp: new Date().toISOString()
            });
        }
        
        // 自动滚动到底部
        scrollToBottom();
    }
    
    function addMessage(content, sender) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}`;
        
        const messageContent = document.createElement('div');
        messageContent.className = 'message-content';
        
        // 添加消息类型标签
        const typeSpan = document.createElement('div');
        typeSpan.className = 'message-type';
        
        if (sender === 'user') {
            typeSpan.innerHTML = '<i class="fas fa-user"></i> 您';
        } else {
            typeSpan.innerHTML = '<i class="fas fa-robot"></i> 助手';
        }
        
        // 消息内容
        const textSpan = document.createElement('div');
        textSpan.innerHTML = content.replace(/\n/g, '<br>');
        
        messageContent.appendChild(typeSpan);
        messageContent.appendChild(textSpan);
        messageDiv.appendChild(messageContent);
        chatHistory.appendChild(messageDiv);
        
        scrollToBottom();
    }
    
    function clearChatHistory() {
        chatHistory.innerHTML = '';
    }
    
    function addWelcomeMessage() {
        const welcomeDiv = document.createElement('div');
        welcomeDiv.className = 'welcome-message';
        welcomeDiv.innerHTML = `
            <h3>欢迎使用车辆电路图导航助手！</h3>
            <p>您可以这样问我：</p>
            <ul>
                <li>"我要一个东风天龙的仪表图"</li>
                <li>"找一下三一挖掘机的电路图"</li>
                <li>"徐工XE135G的针脚定义"</li>
                <li>"红岩杰狮保险丝图纸"</li>
            </ul>
            <p>我会通过对话帮您精确找到所需的电路图。</p>
        `;
        chatHistory.appendChild(welcomeDiv);
    }
    
    function showOptions(options) {
        optionsContainer.innerHTML = '';
        optionsContainer.classList.add('active');
        
        const gridDiv = document.createElement('div');
        gridDiv.className = 'options-grid';
        
        options.forEach((option, index) => {
            const button = document.createElement('button');
            button.className = 'option-button';
            button.innerHTML = `<strong>${String.fromCharCode(65 + index)}.</strong> ${option}`;
            
            button.addEventListener('click', function() {
                // 直接发送选项内容
                messageInput.value = option;
                sendMessage();
            });
            
            gridDiv.appendChild(button);
        });
        
        optionsContainer.appendChild(gridDiv);
    }
    
    function hideOptions() {
        optionsContainer.classList.remove('active');
        optionsContainer.innerHTML = '';
    }
    
    function showLoading() {
        const loadingDiv = document.createElement('div');
        loadingDiv.className = 'message assistant loading';
        loadingDiv.id = 'loadingMessage';
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        
        const textSpan = document.createElement('div');
        textSpan.innerHTML = '正在搜索中';
        
        const dotsDiv = document.createElement('div');
        dotsDiv.className = 'loading-dots';
        dotsDiv.innerHTML = '<span></span><span></span><span></span>';
        
        contentDiv.appendChild(textSpan);
        contentDiv.appendChild(dotsDiv);
        loadingDiv.appendChild(contentDiv);
        chatHistory.appendChild(loadingDiv);
        
        scrollToBottom();
    }
    
    function removeLoading() {
        const loadingMessage = document.getElementById('loadingMessage');
        if (loadingMessage) {
            loadingMessage.remove();
        }
    }
    
    function checkServerStatus() {
        fetch('/api/status')
            .then(response => response.json())
            .then(data => {
                if (data.status === 'ok') {
                    console.log('服务器状态正常，数据量：', data.data_count);
                } else {
                    console.warn('服务器状态异常');
                }
            })
            .catch(error => {
                console.error('无法连接到服务器:', error);
                addMessage('无法连接到服务器，请确保后端服务正在运行。', 'assistant');
            });
    }
    
    function checkAuthStatus() {
        fetch('/check_auth')
            .then(response => response.json())
            .then(data => {
                if (data.authenticated) {
                    // 显示用户信息
                    userInfo.style.display = 'block';
                    loginRegister.style.display = 'none';
                    usernameDisplay.textContent = data.user.username;
                    
                    // 显示保存对话按钮
                    saveConversationBtn.style.display = 'flex';
                } else {
                    // 显示登录注册按钮
                    userInfo.style.display = 'none';
                    loginRegister.style.display = 'block';
                    
                    // 隐藏保存对话按钮
                    saveConversationBtn.style.display = 'none';
                }
            })
            .catch(error => {
                console.error('检查认证状态失败:', error);
            });
    }
    
    function showHistoryModal() {
        historyModal.style.display = 'block';
        historyList.innerHTML = '正在加载历史对话...';
        
        // 加载历史对话
        fetch('/api/conversations')
            .then(response => response.json())
            .then(data => {
                if (data.success && data.conversations.length > 0) {
                    let html = '';
                    data.conversations.forEach(conv => {
                        html += `
                            <div class="history-item" style="padding: 15px; margin-bottom: 10px; background-color: #f8f9fa; border-radius: 8px; border-left: 4px solid #667eea;">
                                <h4>${conv.title}</h4>
                                <p style="color: #666; font-size: 0.9rem;">
                                    创建时间: ${conv.created_at}<br>
                                    最后更新: ${conv.updated_at}<br>
                                    消息数量: ${conv.message_count} 条
                                </p>
                                <button onclick="loadConversation(${conv.id})" style="margin-top: 10px; padding: 8px 15px; background: #667eea; color: white; border: none; border-radius: 5px; cursor: pointer;">
                                    <i class="fas fa-eye"></i> 查看对话
                                </button>
                                <button onclick="deleteConversation(${conv.id})" style="margin-top: 10px; margin-left: 10px; padding: 8px 15px; background: #dc3545; color: white; border: none; border-radius: 5px; cursor: pointer;">
                                    <i class="fas fa-trash"></i> 删除
                                </button>
                            </div>
                        `;
                    });
                    historyList.innerHTML = html;
                } else {
                    historyList.innerHTML = '<p style="text-align: center; color: #666;">暂无历史对话记录</p>';
                }
            })
            .catch(error => {
                console.error('Error:', error);
                historyList.innerHTML = '<p style="color: red;">加载失败，请重试</p>';
            });
    }
    
    function showSaveConversationModal() {
        // 自动生成标题（第一条用户消息）
        let title = '新对话';
        if (conversationMessages.length > 0) {
            const firstUserMessage = conversationMessages.find(msg => msg.role === 'user');
            if (firstUserMessage) {
                title = firstUserMessage.content.substring(0, 50);
                if (firstUserMessage.content.length > 50) {
                    title += '...';
                }
            }
        }
        
        conversationTitle.value = title;
        titleError.style.display = 'none';
        saveConversationModal.style.display = 'block';
    }
    
    function saveConversation() {
        const title = conversationTitle.value.trim();
        if (!title) {
            titleError.textContent = '请输入对话标题';
            titleError.style.display = 'block';
            return;
        }
        
        if (title.length > 200) {
            titleError.textContent = '标题长度不能超过200个字符';
            titleError.style.display = 'block';
            return;
        }
        
        // 发送保存请求
        fetch('/api/save_conversation', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                title: title,
                messages: conversationMessages
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('对话保存成功！');
                saveConversationModal.style.display = 'none';
            } else {
                titleError.textContent = data.message || '保存失败';
                titleError.style.display = 'block';
            }
        })
        .catch(error => {
            console.error('Error:', error);
            titleError.textContent = '网络错误，请重试';
            titleError.style.display = 'block';
        });
    }
    
    function scrollToBottom() {
        chatHistory.scrollTop = chatHistory.scrollHeight;
    }
    
    // 键盘快捷键：Ctrl+Enter 发送，Esc 清空输入框
    document.addEventListener('keydown', function(e) {
        if (e.ctrlKey && e.key === 'Enter') {
            sendMessage();
        }
        if (e.key === 'Escape') {
            messageInput.value = '';
        }
    });
    
    // 全局函数，供历史对话按钮调用
    window.loadConversation = function(conversationId) {
        fetch(`/api/conversations/${conversationId}`)
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // 清空当前聊天历史
                    chatHistory.innerHTML = '';
                    
                    // 清空当前对话消息记录
                    conversationMessages = [];
                    
                    // 显示历史对话
                    data.messages.forEach(msg => {
                        addMessage(msg.content, msg.role);
                        
                        // 记录消息到内存
                        conversationMessages.push({
                            role: msg.role,
                            content: msg.content,
                            message_type: msg.message_type || 'message',
                            options: msg.options,
                            results: msg.results,
                            timestamp: msg.timestamp
                        });
                    });
                    
                    // 关闭历史模态窗口
                    historyModal.style.display = 'none';
                    
                    alert('历史对话已加载到当前窗口');
                } else {
                    alert('加载失败：' + (data.message || '未知错误'));
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('网络错误，请重试');
            });
    };
    
    window.deleteConversation = function(conversationId) {
        if (confirm('确定要删除这个对话吗？')) {
            fetch(`/api/conversations/${conversationId}`, {
                method: 'DELETE'
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert('对话已删除');
                    // 重新加载历史列表
                    showHistoryModal();
                } else {
                    alert('删除失败：' + (data.message || '未知错误'));
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('网络错误，请重试');
            });
        }
    };
});