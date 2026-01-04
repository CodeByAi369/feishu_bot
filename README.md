# 飞书机器人消息监听与邮件转发系统

这是一个基于 Python Flask 和飞书官方 lark-oapi SDK 的机器人应用，能够监听飞书群聊消息，检测关键字后自动将消息转发为邮件发送给指定收件人。

## 功能特性

- ✅ 使用飞书官方 lark-oapi SDK
- ✅ **支持两种模式**：Webhook 模式和长连接（WebSocket）模式
- ✅ 监听飞书群组消息
- ✅ 支持模糊关键字匹配（可配置大小写敏感）
- ✅ 自动发送HTML格式邮件
- ✅ 支持一个关键字对应多个收件人
- ✅ 支持多个关键字规则
- ✅ 完整的日志记录
- ✅ 支持本地部署
- ✅ 自动处理签名验证和 URL 验证
- ✅ 长连接模式无需公网 IP 和内网穿透

## 两种部署模式对比

| 特性 | Webhook 模式 | 长连接模式（推荐） |
|------|-------------|-----------------|
| 需要公网 IP | ✅ 是 | ❌ 否 |
| 需要内网穿透 | ✅ 是（本地开发） | ❌ 否 |
| 配置难度 | 中等 | 简单 |
| 开发速度 | ~1周 | ~5分钟 |
| 防火墙配置 | 需要 | 不需要 |
| 适用场景 | 生产环境 | 开发测试/本地部署 |

## 目录结构

```
feishu_bot_mailer/
├── app.py                  # Webhook 模式主程序
├── app_ws.py              # 长连接模式主程序（推荐）
├── config/                 # 配置目录
│   ├── config.py          # 配置类
│   └── keywords.json      # 关键字配置文件
├── utils/                 # 工具类
│   ├── keyword_matcher.py # 关键字匹配器
│   └── email_sender.py    # 邮件发送器
├── logs/                  # 日志目录
├── venv/                  # Python 虚拟环境
├── .env                   # 环境变量配置
├── .env.example           # 环境变量配置示例
├── requirements.txt       # Python依赖
├── start.sh              # Webhook 模式启动脚本
├── start_ws.sh           # 长连接模式启动脚本（推荐）
└── README.md             # 说明文档
```

## 部署步骤

### 1. 创建飞书机器人

1. 访问 [飞书开放平台](https://open.feishu.cn/)
2. 创建企业自建应用
3. 获取 **App ID** 和 **App Secret**
4. 在「应用功能 - 机器人」中启用机器人功能
5. 在「权限管理」中申请以下权限：
   - `im:message`（接收消息）
   - `im:message.group_at_msg`（接收群组@消息）

#### 长连接模式配置（推荐）

6. 在「事件订阅」中选择「使用长连接」
   - 无需配置请求网址
   - 无需公网 IP 或域名
7. 发布版本并添加机器人到目标群组

#### Webhook 模式配置（可选）

6. 在「事件订阅」中选择「使用 Webhook」
   - 请求网址：`http://your-server-ip:5000/webhook`
   - 订阅事件：`接收消息 v2.0` (im.message.receive_v1)
7. 发布版本并添加机器人到目标群组

### 2. 配置邮箱SMTP

以下是常用邮箱的SMTP配置：

#### Gmail
- SMTP服务器：`smtp.gmail.com`
- 端口：`587` (TLS) 或 `465` (SSL)
- 需要开启「两步验证」并生成「应用专用密码」

#### QQ邮箱
- SMTP服务器：`smtp.qq.com`
- 端口：`587` 或 `465`
- 需要在邮箱设置中开启SMTP服务并获取授权码

#### 163邮箱
- SMTP服务器：`smtp.163.com`
- 端口：`25` 或 `465`
- 需要在邮箱设置中开启SMTP服务

### 3. 安装依赖

本项目使用飞书官方的 lark-oapi SDK 和 Python 虚拟环境。

#### 方式一：使用启动脚本（推荐）

启动脚本会自动创建虚拟环境并安装依赖：

```bash
cd ~/feishu_bot_mailer
./start.sh install
```

#### 方式二：手动安装

```bash
cd ~/feishu_bot_mailer

# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

主要依赖：
- `Flask`: Web 框架
- `lark-oapi`: 飞书官方 Python SDK (1.4.23)
- `python-dotenv`: 环境变量管理
- `requests`: HTTP 请求库

> **注意**: 本项目使用虚拟环境避免污染系统 Python 环境。macOS 上 Homebrew 安装的 Python 默认不允许全局安装包，必须使用虚拟环境。

### 4. 配置环境变量

编辑 `.env` 文件，填写以下配置：

```bash
# 飞书机器人配置
FEISHU_APP_ID=cli_xxxxxxxxxxxxx
FEISHU_APP_SECRET=xxxxxxxxxxxxx
FEISHU_VERIFICATION_TOKEN=xxxxxxxxxxxxx
FEISHU_ENCRYPT_KEY=xxxxxxxxxxxxx

# SMTP邮件配置
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password
FROM_EMAIL=your_email@gmail.com
FROM_NAME=飞书消息提醒机器人
USE_TLS=True
```

### 5. 配置关键字规则

编辑 `config/keywords.json`，配置关键字和对应的收件人：

```json
[
  {
    "keyword": "紧急",
    "recipients": ["urgent@example.com"]
  },
  {
    "keyword": "故障",
    "recipients": ["ops@example.com", "manager@example.com"]
  },
  {
    "keyword": "报销",
    "recipients": ["finance@example.com"]
  }
]
```

### 6. 启动服务

#### 长连接模式启动（推荐，无需公网 IP）

**方式一：使用启动脚本**

```bash
./start_ws.sh
```

启动成功后会显示：
```
======================================
启动飞书机器人（长连接模式）
======================================
正在连接飞书服务器...
connected to wss://xxxxxxxxx
```

**方式二：手动启动**

```bash
# 激活虚拟环境
source venv/bin/activate

# 启动长连接服务
python app_ws.py
```

#### Webhook 模式启动（需要公网 IP）

**方式一：使用启动脚本**

```bash
./start.sh
```

**方式二：手动启动**

```bash
# 激活虚拟环境
source venv/bin/activate

# 启动 Webhook 服务
python app.py
```

### 7. 配置内网穿透（仅 Webhook 模式需要）

**注意：长连接模式无需此步骤！**

如果使用 Webhook 模式，由于飞书需要公网可访问的地址，本地部署需要配置内网穿透：

#### 使用 ngrok（推荐）
```bash
# 安装ngrok
brew install ngrok

# 启动内网穿透
ngrok http 5000
```

将 ngrok 提供的公网地址（如 `https://xxxx.ngrok.io`）配置到飞书开放平台的「事件订阅 - 请求网址」：
```
https://xxxx.ngrok.io/webhook
```

#### 使用 frp
也可以使用 frp 等其他内网穿透工具。

## 使用说明

1. 确保机器人已添加到目标群组
2. 启动服务后，机器人会自动监听群消息
3. 当群成员发送包含关键字的消息时，系统会：
   - 检测消息中的关键字（模糊匹配）
   - 提取消息内容和发送者信息
   - 格式化为HTML邮件
   - 发送给配置的收件人

### 示例

**群聊消息：**
```
@机器人 线上服务出现故障，需要紧急处理！
```

**触发关键字：** `故障`, `紧急`

**发送邮件：**
- 收件人：`ops@example.com`, `manager@example.com`, `urgent@example.com`
- 主题：`[飞书消息提醒] 检测到关键字: 故障`
- 正文包含：发送者、时间、群组、完整消息内容

## 测试

### 测试健康检查
```bash
curl http://localhost:5000/health
```

### 测试消息接收
在飞书群组中发送包含关键字的消息，观察日志输出：
```bash
tail -f logs/bot.log
```

## 常见问题

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
