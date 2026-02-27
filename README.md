# 🤖 飞书机器人消息监听与邮件转发系统

一个功能强大的飞书机器人，支持日报解析、关键词匹配、请假管理、定时提醒等功能。

## 🚀 快速开始（30秒部署）

### Windows：
```bash
setup_and_start.bat
```

### Mac/Linux：
```bash
python setup_and_start.py
```

**就这么简单！** 脚本会自动：
- ✅ 创建虚拟环境并安装依赖
- ✅ 引导设置密码并加密配置文件
- ✅ 启动机器人（配置在内存中，安全防护）

---

## ✨ 功能特性

### 核心功能
- 🔐 **安全加密** - .env 文件加密存储，配置在内存中解密
- 📊 **日报解析** - 自动识别和解析日报内容，生成报表
- 🔍 **关键词监听** - 智能匹配关键词并转发邮件
- 📅 **请假管理** - 请假申请、审批、查询
- ⏰ **定时提醒** - 未提交日报自动提醒
- 📧 **邮件转发** - HTML格式邮件自动发送
- 📝 **完整日志** - 详细的操作和错误日志
- 🗓️ **工作日日历** - 基于法定节假日，仅在工作日执行提醒
- 💬 **指令菜单** - 支持 `/日报汇总`、`/设置调休`、`/我的日报` 等命令
- 📘 **命令文档** - 详见 [docs/COMMANDS.md](docs/COMMANDS.md)

### 技术特性
- ✅ 使用飞书官方 lark-oapi SDK
- ✅ 长连接模式，无需公网 IP
- ✅ 配置加密存储，内存解密
- ✅ 自动重连机制
- ✅ 完整的错误处理

---

## 📁 项目结构

```
feishu_bot/
├── 🚀 启动脚本
│   ├── setup_and_start.bat        # Windows 一键启动
│   └── setup_and_start.py         # Mac/Linux 一键启动
│
├── 🔐 安全加密
│   ├── encrypt_env.py             # 加密/解密工具
│   └── secure_loader.py           # 内存解密模块
│
├── 📱 主程序
│   ├── app_ws.py                  # 长连接模式主程序
│   └── app.py                     # Webhook 模式
│
├── ⚙️ 配置
│   ├── config/
│   │   ├── config.py              # 配置类
│   │   ├── keywords.json          # 关键词规则
│   │   └── user_names.json        # 用户姓名映射
│   ├── .env                       # 环境变量（加密前）
│   └── .env.encrypted             # 加密后的配置
│
├── 🛠️ 工具模块
│   └── utils/
│       ├── keyword_matcher.py     # 关键词匹配
│       ├── email_sender.py        # 邮件发送
│       ├── daily_report_parser.py # 日报解析
│       ├── daily_report_storage.py # 日报存储
│       ├── vacation_manager.py    # 请假管理
│       ├── reminder_sender.py     # 提醒功能
│       └── report_table_generator.py # 报表生成
│
├── 📊 数据存储
│   └── data/
│       ├── daily_reports.json     # 日报数据
│       └── vacations.json         # 请假数据
│
├── 📝 日志
│   └── logs/
│
├── 🧪 测试脚本
│   ├── test_connection.py         # 测试连接
│   ├── test_config.py             # 测试配置
│   ├── test_encryption.py         # 测试加密
│   └── test_*.py                  # 其他测试
│
└── 📚 文档
    ├── README.md                  # 项目说明
    ├── 安全部署方案.md            # 安全部署指南
    └── WINDOWS部署指南.md         # Windows 部署
```

## 部署步骤

### 1. 创建飞书机器人

1. 访问 [飞书开放平台](https://open.feishu.cn/)，创建企业自建应用
2. 获取 **App ID** 和 **App Secret**
3. 启用「机器人」功能
4. 申请权限：
   - `im:message`（接收消息）
   - `im:message.group_at_msg`（接收群组@消息）
5. 在「事件订阅」中选择「使用长连接」（无需公网 IP）
6. 发布版本并添加机器人到群组

### 2. 配置环境变量

创建 `.env` 文件：

```bash
# 飞书应用配置
FEISHU_APP_ID=cli_xxxxxxxxxxxxxx
FEISHU_APP_SECRET=xxxxxxxxxxxxxx

# 邮箱配置
SMTP_SERVER=smtp.qq.com
SMTP_PORT=587
SMTP_USER=your_email@qq.com
SMTP_PASSWORD=your_auth_code
SMTP_FROM=your_email@qq.com

# 提醒配置（可选）
REMINDER_CHAT_ID=oc_xxxxxxxxxxxxxx
REMINDER_TIME=18:00
```

常用邮箱 SMTP 配置：
- **QQ邮箱**: `smtp.qq.com:587`（需要授权码）
- **Gmail**: `smtp.gmail.com:587`（需要应用专用密码）
- **163邮箱**: `smtp.163.com:465`

### 3. 启动机器人

#### 一键启动（推荐）：

```bash
cd ~/feishu_bot_mailer
./start.sh install
```

#### 方式二：手动安装

```bash
cd ~/feishu_bot_mailer
```bash
# Windows
setup_and_start.bat

# Mac/Linux
python setup_and_start.py
```

脚本会自动：
1. 检查并创建虚拟环境
2. 安装所需依赖
3. 引导加密配置文件
4. 启动机器人

#### 手动启动：

如果需要手动控制环境：

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境 (Windows)
venv\Scripts\activate

# 激活虚拟环境 (Mac/Linux)
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 启动机器人
python app_ws.py
```

---

## 📖 使用说明

### 关键词配置

编辑 [config/keywords.json](config/keywords.json)：

```json
[
  {
    "keyword": "紧急",
    "recipients": ["urgent@example.com"]
  },
  {
    "keyword": "故障",
    "recipients": ["ops@example.com", "manager@example.com"]
  }
]
```

### 日报功能

机器人会自动识别日报格式：
```
今日完成：
1. 完成项目A开发
2. 修复bug #123

明日计划：
1. 继续项目B
2. 代码审查
```

查询命令：
- `查看日报` - 查看今日所有人的日报
- `查看未提交` - 查看未提交日报的人员

### 请假功能

申请请假：
```
请假
开始时间：2026-01-05
结束时间：2026-01-06
原因：家中有事
```

查询命令：
- `查看请假` - 查看所有请假记录
- `我的请假` - 查看自己的请假记录

### 提醒设置

使用 [setup_reminder.py](setup_reminder.py) 配置定时提醒：

```bash
python setup_reminder.py
```

---

## 🔐 安全说明

本项目采用加密存储方案：
- ✅ .env 配置文件加密存储为 .env.encrypted
- ✅ 配置在内存中解密，不生成明文文件
- ✅ 其他人无法查看敏感信息

详见 [安全部署方案.md](安全部署方案.md)

---

## 🧪 测试

```bash
# 测试飞书连接
python test_connection.py

# 测试配置
python test_config.py

# 测试加密
python test_encryption.py
```

---

## 📝 日志

日志文件位于 `logs/` 目录：
- `bot.log` - 机器人运行日志
- 自动按大小轮转（最大 10MB）
- 保留最近 5 个日志文件

---

## ❓ 常见问题

### 1. 虚拟环境问题
**Q: 提示"ModuleNotFoundError: No module named 'xxx'"**

A: 使用一键启动脚本会自动处理，或手动安装：
```bash
python -m pip install -r requirements.txt
```

### 2. PowerShell 执行策略错误
**Q: Windows 提示"禁止运行脚本"**

A: 直接使用 Python 脚本：
```bash
python setup_and_start.py
```

### 3. 密码忘记
**Q: 忘记加密密码怎么办？**

A: 从备份恢复 .env 文件，删除 .env.encrypted，重新运行 setup_and_start.bat

### 4. 机器人无响应
**Q: 机器人不回复消息**

A: 检查：
1. 日志中是否有连接成功提示
2. 机器人是否在群组中
3. 是否有权限（im:message）
4. 环境变量是否正确配置

### 5. 邮件发送失败
**Q: 关键词触发但邮件未发送**

A: 检查：
1. SMTP 配置是否正确
2. 是否开启了邮箱的 SMTP 服务
3. 是否使用了授权码（不是登录密码）
4. 查看日志中的详细错误信息

---

## 📄 许可证

MIT License

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

## 📮 联系方式

如有问题，请提交 Issue。

### Q1: WebSocket连接频繁断开？⭐⭐⭐⭐⭐

**错误信息**：
```
ERROR - receive message loop exit, err: no close frame received or sent
ERROR - keepalive ping timeout
```

**解决方法**：
1. **使用健壮版启动脚本（推荐）**：
   ```bash
   # macOS/Linux
   ./start_ws_robust.sh

   # Windows
   start_ws_robust.bat
   ```
   特点：自动重连、网络检测、最多重试10次

2. **切换网络环境**：
   - 关闭VPN
   - 切换到手机热点或其他网络
   - 检查防火墙和代理设置

3. **运行连接测试**：
   ```bash
   python test_connection.py
   ```

4. **查看详细排查指南**：
   - 文档：`WebSocket连接问题排查指南.md`
   - 包含详细的问题分析和解决方案

### Q2: 日志中出现其他群组的消息？⭐⭐⭐⭐

**原因**：WebSocket长连接会接收机器人加入的所有群组消息

**解决方法**：
1. 配置 `.env` 文件中的 `DAILY_REPORT_CHAT_ID`：
   ```bash
   DAILY_REPORT_CHAT_ID=oc_xxxxxxxxxxxxx
   ```

2. 获取群组ID的方法：
   - 在目标群中发送任意消息
   - 查看日志 `logs/bot.log`
   - 找到 "群组: oc_xxxxx"
   - 复制该ID到配置文件

3. 重启服务后验证：
   ```
   🔒 群组过滤已启用 - 只处理群组: oc_xxxxx
      其他群组的消息将被自动忽略
   ```

### Q3: 收不到飞书消息？
- 检查机器人是否已添加到群组
- 检查事件订阅配置是否正确（选择"使用长连接"）
- 检查应用版本是否已发布
- 运行 `python test_connection.py` 测试配置
- 查看日志文件 `logs/bot.log`

### Q4: 邮件发送失败？
- 检查SMTP配置是否正确
- 确认邮箱开启了SMTP服务
- Gmail需要使用应用专用密码，不能使用账户密码
- 检查网络是否能连接SMTP服务器

### Q5: 关键字不匹配？
- 检查 `config/keywords.json` 配置是否正确
- 默认不区分大小写，如需区分请设置 `CASE_SENSITIVE=True`
- 查看日志确认消息是否被正确接收

### Q6: 服务启动失败？
- 检查Python版本（需要3.7+）
- 检查依赖是否正确安装
- 运行 `python test_connection.py` 检测配置

## 日志

所有日志保存在 `logs/bot.log`，包含：
- 消息接收记录
- 关键字匹配结果
- 邮件发送状态
- 错误信息

## 关于官方 SDK

本项目使用飞书官方的 `lark-oapi` Python SDK，相比手动处理 webhook 有以下优势：

### SDK 优势

1. **自动化处理**：SDK 自动处理 URL 验证、签名验证等底层逻辑
2. **类型安全**：提供完整的类型提示，开发体验更好
3. **官方维护**：由飞书官方维护，及时跟进 API 变化
4. **标准化**：使用官方推荐的最佳实践
5. **简化代码**：减少样板代码，逻辑更清晰

### SDK 文档

- 官方文档：[https://open.feishu.cn/document/server-docs/getting-started/server-sdk/python-sdk](https://open.feishu.cn/document/server-docs/getting-started/server-sdk/python-sdk)
- GitHub：[https://github.com/larksuite/oapi-sdk-python](https://github.com/larksuite/oapi-sdk-python)

## 扩展功能

### 1. 支持正则表达式匹配

修改 `utils/keyword_matcher.py`，使用 `match_regex` 方法。

### 2. 添加更多邮件模板

修改 `app.py` 中的 `email_body` 部分，自定义邮件格式。

### 3. 数据库存储

可以集成数据库（如SQLite、MySQL）存储消息记录。

### 4. 多群组支持

在 `keywords.json` 中添加 `chat_id` 字段，实现不同群组使用不同规则。

### 5. 使用 SDK 发送消息

可以使用 `lark-oapi` SDK 的消息发送功能，让机器人在群里回复消息：

```python
from lark_oapi.api.im.v1 import CreateMessageRequest, CreateMessageRequestBody

# 发送文本消息
request = CreateMessageRequest.builder() \
    .receive_id_type("chat_id") \
    .request_body(CreateMessageRequestBody.builder()
        .receive_id(chat_id)
        .msg_type("text")
        .content("{\"text\":\"已收到并转发邮件\"}")
        .build()) \
    .build()

response = client.im.v1.message.create(request)
```

## 安全建议

1. 不要将 `.env` 文件提交到版本控制系统
2. 定期更换 SMTP 密码和飞书应用密钥
3. 启用飞书签名验证（配置 `ENCRYPT_KEY`）
4. 使用HTTPS部署生产环境
5. 限制服务器访问权限

## 许可

MIT License

## 作者

Created by Claude Code

---

如有问题或建议，欢迎提交 Issue！
