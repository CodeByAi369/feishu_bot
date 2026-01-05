# Windows 部署指南

## ⚠️ 重要更新（2025-10-21）

### 加密工具修复

已修复 Windows 上的加密工具导入错误：
- ✅ `encrypt_env.py`: 修复 `PBKDF2` 导入错误
- ✅ `encrypt_env_aes256.py`: 修复 `PBKDF2` 导入错误

**如果你之前遇到以下错误：**
```
ImportError: cannot import name 'PBKDF2' from 'cryptography.hazmat.primitives.kdf.pbkdf2'
```

**解决方案：**
1. 从 Mac 同步最新的代码到 Windows
2. 或者手动替换这两个文件
3. 重新运行加密命令

**测试修复：**
```powershell
# 激活虚拟环境
venv\Scripts\activate

# 测试加密工具
python test_encryption.py 

# 如果显示 "✅ 所有加密模块测试通过！" 说明修复成功
```

---

## 📋 前置要求

### 1. 安装Python
- 下载并安装 Python 3.9 或更高版本
- 下载地址: https://www.python.org/downloads/
- **重要**: 安装时勾选 "Add Python to PATH"

### 2. 验证Python安装
打开命令提示符（CMD）或PowerShell，运行：
```bash
python --version
```
应该显示类似 `Python 3.x.x`

## 🚀 部署步骤

### 方法1：使用批处理脚本（推荐，简单）

1. **将整个项目文件夹复制到Windows电脑**

2. **配置环境变量**
   - 复制 `.env.example` 为 `.env`
   - 编辑 `.env` 文件，填写配置信息（与Mac上相同）

3. **首次运行（安装依赖）**
   ```bash
   双击运行: start_ws.bat install
   ```
   或在命令提示符中：
   ```bash
   start_ws.bat install
   ```

4. **启动服务**
   ```bash
   双击运行: start_ws.bat
   ```
   或在命令提示符中：
   ```bash
   start_ws.bat
   ```

5. **停止服务**
   - 按 `Ctrl+C`
   - 或直接关闭窗口

### 方法2：使用PowerShell脚本（功能更强大）

1. **设置执行策略**（首次使用需要）

   以管理员身份运行PowerShell，执行：
   ```powershell
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
   ```

2. **配置环境变量**
   - 同上，配置 `.env` 文件

3. **首次运行（安装依赖）**
   ```powershell
   .\start_ws.ps1 install
   ```

4. **启动服务**
   ```powershell
   .\start_ws.ps1
   ```

5. **停止服务**
   - 按 `Ctrl+C`

### 方法3：手动启动（适合开发调试）

```bash
# 1. 创建虚拟环境
python -m venv venv

# 2. 激活虚拟环境
venv\Scripts\activate.bat

# 3. 安装依赖
pip install -r requirements.txt

# 4. 启动服务
python app_ws.py
```

## 📁 需要复制的文件和文件夹

从Mac复制到Windows时，确保包含：

```
feishu_bot_mailer/
├── app_ws.py                 # 主程序（长连接模式）
├── app.py                    # 备用程序（Webhook模式）
├── requirements.txt          # Python依赖列表
├── .env                      # 环境变量配置（需手动配置）
├── .env.example              # 配置示例
├── start_ws.bat              # Windows启动脚本（批处理）
├── start_ws.ps1              # Windows启动脚本（PowerShell）
├── config/                   # 配置文件夹
│   ├── config.py
│   ├── keywords.json
│   └── user_names.json
├── utils/                    # 工具类文件夹
│   ├── email_sender.py
│   ├── daily_report_parser.py
│   ├── daily_report_storage.py
│   ├── report_table_generator.py
│   ├── reminder_sender.py
│   ├── keyword_matcher.py
│   └── vacation_manager.py
├── data/                     # 数据存储文件夹
│   ├── daily_reports.json
│   └── vacations.json
└── logs/                     # 日志文件夹
    └── bot.log
```

**不需要复制的文件夹：**
- `venv/` - 虚拟环境（Windows上重新创建）
- `__pycache__/` - Python缓存文件
- `.git/` - Git仓库文件（如果不需要版本控制）

## ⚙️ Windows特有配置

### 1. 防火墙设置
如果使用Webhook模式（app.py），需要：
- 允许Python通过Windows防火墙
- 开放配置的端口（默认5000）

### 2. 文件路径
- Windows使用反斜杠 `\`，但Python会自动处理
- 代码中的相对路径在Windows上同样有效

### 3. 字符编码
- 启动脚本已设置UTF-8编码
- 确保 `.env` 文件使用UTF-8编码保存

## 🔧 常见问题

### Q1: 双击 .bat 文件闪退
**解决方案：**
- 在命令提示符中运行，查看错误信息
- 检查Python是否正确安装并添加到PATH

### Q2: PowerShell提示"无法加载文件，因为在此系统上禁止运行脚本"
**解决方案：**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Q3: 找不到模块（ModuleNotFoundError）
**解决方案：**
```bash
# 确保虚拟环境已激活
venv\Scripts\activate.bat

# 重新安装依赖
pip install -r requirements.txt
```

### Q4: 中文乱码
**解决方案：**
- 确保命令提示符/PowerShell使用UTF-8编码
- 启动脚本已自动设置，如果仍有问题，手动运行：
  ```bash
  chcp 65001
  ```

### Q5: 连接飞书服务器失败
**解决方案：**
- 检查网络连接
- 检查防火墙设置
- 确认 `.env` 中的 APP_ID 和 APP_SECRET 正确

## 🎯 配置验证

启动服务后，应该看到类似输出：

```
======================================
启动飞书机器人邮件转发服务（长连接模式）...
使用飞书官方 lark-oapi SDK - WebSocket 长连接
已加载 0 个关键字规则
======================================
📊 日报功能已启用
   - 日报群组: oc_xxxxxx
   - 正在初始化群成员列表...
   ✅ 成功初始化 10 个用户姓名映射
   - 发送模式: 🎯 手动触发
   - 收件人: xxx@xxx.com
======================================
正在连接飞书服务器...
```

## 📝 后台运行（可选）

如果需要Windows后台运行，可以：

### 方法1：使用nssm（推荐）
1. 下载nssm: https://nssm.cc/download
2. 安装为Windows服务：
   ```bash
   nssm install FeishuBot "C:\path\to\venv\Scripts\python.exe" "C:\path\to\app_ws.py"
   nssm start FeishuBot
   ```

### 方法2：使用任务计划程序
1. 打开"任务计划程序"
2. 创建基本任务
3. 触发器：系统启动时
4. 操作：启动程序 `start_ws.bat`

### 方法3：使用pythonw.exe（隐藏窗口）
```bash
pythonw app_ws.py
```

## ✅ 完成检查清单

- [ ] Python已安装并添加到PATH
- [ ] 项目文件已复制到Windows
- [ ] `.env` 文件已配置
- [ ] 虚拟环境已创建
- [ ] 依赖包已安装
- [ ] 服务成功启动
- [ ] 在飞书群测试消息接收
- [ ] 日报功能测试通过

## 🆘 需要帮助？

如遇到问题，请检查：
1. `logs/bot.log` 日志文件
2. 命令行错误输出
3. 防火墙和网络设置
4. Python和依赖版本

---

部署完成后，服务应该与Mac上完全相同！
