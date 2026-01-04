# WebSocket 连接问题排查指南

## 问题现象

```
ERROR - receive message loop exit, err: no close frame received or sent
ERROR - receive message loop exit, err: keepalive ping timeout
ERROR - ping_timeout
```

---

## 常见原因与解决方案

### 1. 网络环境问题 ⭐⭐⭐⭐⭐

**最常见原因**：公司网络、防火墙、代理、VPN阻止WebSocket长连接

#### 解决方法：

**方法A：切换网络环境**
```bash
# 测试不同网络：
1. 关闭VPN
2. 切换到手机热点
3. 切换到家庭WiFi
4. 使用公共网络（咖啡厅等）
```

**方法B：检查防火墙**
```bash
# Windows防火墙
1. 控制面板 → Windows Defender 防火墙
2. 允许应用通过防火墙
3. 添加Python到允许列表

# macOS防火墙
1. 系统偏好设置 → 安全性与隐私 → 防火墙
2. 防火墙选项 → 添加Python
```

**方法C：检查代理设置**
```bash
# 临时禁用系统代理
Windows: 设置 → 网络和Internet → 代理 → 关闭
macOS: 系统偏好设置 → 网络 → 高级 → 代理 → 取消勾选
```

---

### 2. 飞书配置问题 ⭐⭐⭐⭐

#### 检查清单：

1. **APP_ID 和 APP_SECRET 是否正确**
   ```bash
   # 查看配置
   cat .env | grep FEISHU_APP_ID
   cat .env | grep FEISHU_APP_SECRET

   # 验证格式
   # APP_ID 应该是: cli_xxxxxxxxx
   # APP_SECRET 应该是: xxxxxxxxxxxxx
   ```

2. **机器人权限是否正确**
   - 登录 [飞书开放平台](https://open.feishu.cn/)
   - 进入应用 → 权限管理
   - 确认已申请并通过：
     - `im:message` (接收消息)
     - `im:message.group_at_msg` (接收群组@消息)

3. **事件订阅是否启用**
   - 进入应用 → 事件订阅
   - 确认选择了"使用长连接"（不是Webhook）
   - 确认已订阅事件：
     - `im.message.receive_v1` (接收消息)
     - `im.message.recalled_v1` (消息撤回) - 可选

4. **应用版本是否已发布**
   - 进入应用 → 版本管理与发布
   - 确认最新版本已发布
   - 如果有未发布的版本，点击"发布版本"

---

### 3. 群组配置问题 ⭐⭐⭐

#### 问题：机器人收到其他群组的消息

**原因**：WebSocket长连接会接收机器人加入的所有群组消息

**解决**：配置 `DAILY_REPORT_CHAT_ID` 过滤群组

```bash
# .env 文件
DAILY_REPORT_CHAT_ID=oc_xxxxxxxxxxxxx

# 如何获取群组ID：
# 1. 在群中发送消息
# 2. 查看日志 logs/bot.log
# 3. 找到 "群组: oc_xxxxx"
# 4. 复制该ID到配置文件
```

**验证**：重启后应该只处理目标群组消息
```bash
# 查看日志，应该看到：
🔒 群组过滤已启用 - 只处理群组: oc_xxxxx
其他群组的消息将被自动忽略
```

---

### 4. 连接超时与心跳问题 ⭐⭐⭐

#### 原因：
- 网络不稳定导致心跳包丢失
- 飞书服务器主动断开空闲连接
- 本地网络带宽限制

#### 解决方法：

**使用健壮版启动脚本（自动重连）**
```bash
# macOS/Linux
./start_ws_robust.sh

# Windows
start_ws_robust.bat
```

**特点**：
- 自动检测网络连接
- 服务异常退出后自动重启
- 最多重试10次
- 每次重试间隔5秒

---

### 5. 系统资源问题 ⭐⭐

#### 检查方法：

```bash
# 查看Python进程
ps aux | grep app_ws.py

# 检查CPU和内存占用
top -p $(pgrep -f app_ws.py)

# 查看打开的连接数
lsof -p $(pgrep -f app_ws.py) | grep TCP
```

#### 解决方法：
- 重启机器人服务
- 清理日志文件（`logs/bot.log`）
- 增加系统内存

---

## 日志分析

### 正常启动日志：
```
======================================
启动飞书机器人邮件转发服务（长连接模式）...
使用飞书官方 lark-oapi SDK - WebSocket 长连接
已加载 0 个关键字规则
======================================
✅ 已注册事件处理器：
   - im.message.receive_v1 (消息接收)
   - im.message.recalled_v1 (消息撤回)
🔒 群组过滤已启用 - 只处理群组: oc_xxxxx
======================================
🔌 正在连接飞书服务器...
   - 使用WebSocket长连接
   - 自动重连已启用
======================================
[Lark] connected to wss://xxxxxxx
```

### 异常日志及含义：

| 错误信息 | 含义 | 解决方法 |
|---------|------|---------|
| `no close frame received or sent` | WebSocket连接异常断开 | 检查网络，使用健壮版脚本 |
| `keepalive ping timeout` | 心跳超时，网络不稳定 | 切换网络环境 |
| `ping_timeout` | Ping超时 | 检查防火墙和代理 |
| `sent 1011 (internal error)` | 内部错误 | 重启服务，检查配置 |

---

## 测试与验证

### 1. 测试网络连接
```bash
# 测试飞书服务器连通性
curl -I https://open.feishu.cn

# 应该返回 HTTP/2 200
```

### 2. 测试机器人配置
```bash
# 运行配置测试脚本
python test_config.py

# 应该显示所有配置项正常
```

### 3. 测试消息接收
```bash
# 1. 启动机器人
./start_ws_robust.sh

# 2. 在配置的群组中发送测试消息
# 3. 查看日志是否收到
tail -f logs/bot.log

# 应该看到：
处理消息 - 发送者: xxx, 群组: oc_xxx, 内容: xxx
```

---

## 推荐配置

### .env 配置示例（最佳实践）
```bash
# 飞书机器人配置
FEISHU_APP_ID=cli_xxxxxxxxxxxxx
FEISHU_APP_SECRET=xxxxxxxxxxxxx
FEISHU_VERIFICATION_TOKEN=xxxxxxxxxxxxx
FEISHU_ENCRYPT_KEY=xxxxxxxxxxxxx

# 日报功能配置
DAILY_REPORT_ENABLED=True
DAILY_REPORT_CHAT_ID=oc_xxxxxxxxxxxxx  # 重要：配置目标群组ID
DAILY_REPORT_SEND_MODE=manual
DAILY_REPORT_RECIPIENTS=manager@example.com

# SMTP邮件配置
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password
USE_TLS=True
```

---

## 常见问题 FAQ

### Q1: 为什么日志中出现其他群组的消息？
**A**: 如果未配置 `DAILY_REPORT_CHAT_ID`，机器人会处理所有群组消息。请配置目标群组ID。

### Q2: WebSocket连接频繁断开怎么办？
**A**:
1. 使用健壮版启动脚本（自动重连）
2. 切换网络环境（关闭VPN）
3. 检查防火墙设置

### Q3: 如何确认机器人是否正常运行？
**A**:
1. 查看日志最后一行是否为 "connected to wss://xxx"
2. 在群中发送消息，查看日志是否打印
3. 查看进程是否存在：`ps aux | grep app_ws.py`

### Q4: 日志文件太大怎么办？
**A**:
```bash
# 清空日志
> logs/bot.log

# 或删除旧日志
rm logs/bot.log
```

### Q5: 在Windows上无法启动？
**A**:
1. 确认Python已安装并添加到PATH
2. 使用 `start_ws_robust.bat` 而不是 `.sh`
3. 以管理员身份运行命令提示符

---

## 技术支持

如果以上方法都无法解决问题，请收集以下信息：

1. **日志文件**：`logs/bot.log`（最近100行）
2. **系统信息**：操作系统版本、Python版本
3. **网络环境**：公司网络/家庭网络/VPN等
4. **错误截图**：完整的错误信息

然后联系技术支持或提交Issue。

---

**更新时间**: 2025-10-27
**版本**: v1.0
