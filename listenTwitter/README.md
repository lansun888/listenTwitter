我的推特号：@JLiang93823 感谢您的关注

# Twitter 监控通知系统

这是一个自动监控 Twitter 账号并通过邮件通知新推文的工具。

## 功能特点

- 🔄 实时监控多个 Twitter 账号的新推文
- 📧 通过 Gmail 发送邮件通知
- 💾 自动保存推文数据到本地
- ⚙️ 支持动态配置监控账号
- 🔒 安全的配置管理
- 📝 详细的日志记录

## 安装要求

- Python 3.7+
- Chrome 浏览器
- ChromeDriver (会自动安装)

### 必需的 Python 包
pip install selenium
pip install webdriver_manager

文件结构：
├── listenMaskTwitter.py # 主程序
├── config.json # 配置文件
├── config.json.example # 配置文件模板
├── twitter_accounts.json # 监控账号配置
├── tweets_data/ # 推文数据保存目录
├── twitter_monitor.log # 运行日志
└── README.md # 说明文档

### 1. config.json

这个文件包含主要的认证信息和邮件设置:
json
{
"twitter_credentials": {
"email": "你的Twitter邮箱",
"username": "你的Twitter用户名",
"password": "你的Twitter密码"
},
"email_settings": {
"smtp_server": "smtp.gmail.com",
"smtp_port": 587,
"sender_email": "发送邮箱地址",
"sender_password": "邮箱应用专用密码",
"recipients": [
"接收通知的邮箱地址"
]
}
}
#### 配置说明:
- `twitter_credentials`: Twitter账号登录信息
- `email_settings`: 用于发送通知的邮件配置
  - 目前支持Gmail SMTP服务器
  - 需要在Gmail中开启"应用专用密码"功能

### 2. twitter_accounts.json

这个文件用于配置需要监控的Twitter账号列表:
json
{
"账号ID": {
"name": "显示名称",
"username": "用户名",
"last_tweet_id": "最后一条已处理的推文ID",
"enabled": true/false
}
}


#### 配置说明:
- `name`: 账号显示名称
- `username`: Twitter用户名(不含@符号)
- `last_tweet_id`: 记录最后处理的推文ID,用于增量更新
- `enabled`: 是否启用监控(true/false)

## 使用方法

1. 在 `config.json` 并填入你的认证信息
2. 在 `twitter_accounts.json` 中添加需要监控的账号
3. 确保所有监控账号的 `enabled` 值设为 `true`
4. 运行程序开始监控

## 注意事项

1. 请确保 Twitter 认证信息正确
2. Gmail 需要开启"低安全性应用访问"或使用应用专用密码
3. 建议定期检查 `last_tweet_id` 是否正常更新
4. 请遵守 Twitter API 使用规范和限制

## 安全提示

请妥善保管你的认证信息,建议:
- 不要将包含密码的配置文件提交到代码仓库
- 将 `config.json` 添加到 `.gitignore` 文件中
- 定期更改密码和邮箱应用专用密码