# 飞书机器人功能增强设计文档

**日期**: 2026-02-26  
**作者**: AI Assistant  
**状态**: 已批准  

## 概述

本设计文档描述了飞书机器人三项核心功能增强：

1. **工作日日历集成** - 基于国务院法定节假日的智能提醒
2. **指令菜单系统** - 命令+卡片双模式的交互界面
3. **考勤自动化集成** - 自动同步请假/调休状态（阶段2）

**实施策略**: 分两个阶段，先实现基础功能（工作日日历+指令菜单），再实现进阶自动化（考勤集成）。

---

## 需求背景

### 当前痛点

1. **提醒不智能**: 机器人每天都提醒，包括周末和节假日
2. **操作不便**: 日报汇总、设置调休等功能需要手动修改代码或文件
3. **手动负担重**: 请假/调休人员需要手动设置，容易遗漏

### 目标

1. 只在工作日提醒未提交日报的人员
2. 提供类似 Telegram Bot 的指令菜单，方便日常操作
3. 自动同步飞书考勤数据，减少手动设置

---

## 方案选择

经过评估三种方案（本地自维护、轻量集成、深度集成），选择**方案A：轻量集成 + 渐进增强**。

### 选择理由

- ✅ 开发周期短（阶段1仅需1周）
- ✅ 使用成熟的第三方节假日API，数据准确
- ✅ 命令+卡片双模式，用户体验优秀
- ✅ 架构可扩展，支持后续功能增强
- ✅ 有完善的降级方案，不依赖单一服务

---

## 系统架构

### 整体架构图

```
┌─────────────────────────────────────────────────────────┐
│                    飞书机器人                             │
│                                                           │
│  ┌────────────────────────────────────────────────┐    │
│  │           消息处理层 (app_ws.py)                │    │
│  │                                                  │    │
│  │  ┌──────────────────────────────────────────┐ │    │
│  │  │      CommandRouter (新增)                 │ │    │
│  │  │  - 命令解析和路由                         │ │    │
│  │  │  - 卡片交互处理                           │ │    │
│  │  └──────────────────────────────────────────┘ │    │
│  └────────────────────────────────────────────────┘    │
│                        ↓                                │
│  ┌─────────────┬──────────────┬────────────────────┐  │
│  │ 日报解析    │ 关键词匹配   │ 命令处理 (新)       │  │
│  └─────────────┴──────────────┴────────────────────┘  │
│                                                         │
│  ┌─────────────────────────────────────────────────┐  │
│  │              业务逻辑层 (utils/)                  │  │
│  │                                                   │  │
│  │  ┌──────────────┐  ┌──────────────┐            │  │
│  │  │ WorkdayCalendar│  │ CommandHandler│          │  │
│  │  │   (新增)       │  │   (新增)      │          │  │
│  │  └──────────────┘  └──────────────┘            │  │
│  │                                                   │  │
│  │  ┌──────────────┐  ┌──────────────┐            │  │
│  │  │ ReminderSender│  │AttendanceSync │          │  │
│  │  │   (修改)       │  │  (新增-阶段2) │          │  │
│  │  └──────────────┘  └──────────────┘            │  │
│  │                                                   │  │
│  │  已有: VacationManager, DailyReportStorage       │  │
│  └─────────────────────────────────────────────────┘  │
│                                                         │
│  ┌─────────────────────────────────────────────────┐  │
│  │           数据层 (data/ + config/)                │  │
│  │                                                   │  │
│  │  holidays_cache.json  (新增)                     │  │
│  │  vacations.json       (已有)                     │  │
│  │  daily_reports.json   (已有)                     │  │
│  └─────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                         ↓
              ┌──────────────────────┐
              │  第三方服务            │
              │                        │
              │  - 节假日API          │
              │  - 飞书考勤API (阶段2)│
              └──────────────────────┘
```

### 核心组件

#### 新增组件

1. **WorkdayCalendar** (`utils/workday_calendar.py`)
   - 判断指定日期是否为工作日
   - 缓存节假日数据到本地
   - 自动更新和降级机制

2. **CommandRouter** (`utils/command_router.py`)
   - 解析命令（正则匹配）
   - 路由到对应处理器
   - 处理卡片交互回调

3. **CommandHandler** (`utils/command_handler.py`)
   - 实现具体命令逻辑
   - 生成响应消息和飞书卡片
   - 权限验证（可选）

4. **AttendanceSync** (`utils/attendance_sync.py`) - 阶段2
   - 同步飞书考勤数据
   - 支持多种数据源（API/审批/导入）
   - 自动更新 VacationManager

#### 修改组件

- **ReminderSender**: 集成 WorkdayCalendar，只在工作日提醒
- **app_ws.py**: 接入 CommandRouter 处理命令消息

---

## 详细设计

### 1. 工作日日历模块（WorkdayCalendar）

#### 功能

- 判断指定日期是否为工作日
- 自动获取和缓存国务院节假日数据
- 支持降级到本地配置

#### 接口设计

```python
class WorkdayCalendar:
    """工作日日历管理器"""
    
    def __init__(self, cache_file='data/holidays_cache.json'):
        """初始化，加载缓存"""
        
    def is_workday(self, date: str = None) -> bool:
        """
        判断是否为工作日
        
        Args:
            date: 日期字符串 YYYY-MM-DD，默认今天
            
        Returns:
            bool: True表示工作日，False表示休息日
        """
        
    def get_holidays(self, year: int = None) -> dict:
        """
        获取指定年份的节假日数据
        
        Args:
            year: 年份，默认当前年
            
        Returns:
            dict: {date: {type, name, is_workday}}
        """
        
    def refresh_cache(self, year: int = None) -> bool:
        """
        刷新缓存（从API或本地配置）
        
        Args:
            year: 年份，默认当前年
            
        Returns:
            bool: 是否成功
        """
```

#### 数据源

- **主数据源**: timor.tech API
  - URL: `http://timor.tech/api/holiday/year/{year}`
  - 免费，无需认证
  - 数据准确，包含调休信息
  
- **备用数据源**: 本地配置文件
  - `config/holidays.json`
  - 格式同 API 返回
  - 手动维护作为降级方案

#### 缓存策略

- 每年首次调用时从API获取全年数据
- 缓存到 `data/holidays_cache.json`
- 每天凌晨检查缓存有效性
- API失败时降级到本地配置

#### 数据格式示例

```json
{
  "2026": {
    "2026-01-01": {
      "name": "元旦",
      "is_workday": false,
      "type": "holiday"
    },
    "2026-02-04": {
      "name": "春节前调休",
      "is_workday": true,
      "type": "workday"
    },
    "2026-02-07": {
      "name": "春节",
      "is_workday": false,
      "type": "holiday"
    }
  }
}
```

---

### 2. 命令路由模块（CommandRouter）

#### 支持的命令

| 命令 | 格式 | 说明 | 示例 |
|------|------|------|------|
| 帮助 | `/帮助` 或 `/help` | 显示帮助菜单（卡片） | `/帮助` |
| 日报汇总 | `/日报汇总 [日期]` | 生成日报汇总，默认今天 | `/日报汇总 2026-02-26` |
| 设置调休 | `/设置调休 <姓名> [日期]` | 设置某人调休，默认今天 | `/设置调休 张三` |
| 取消调休 | `/取消调休 <姓名> [日期]` | 取消调休设置 | `/取消调休 张三 2026-02-26` |
| 查询调休 | `/查询调休 [日期]` | 查询调休人员，默认今天 | `/查询调休` |
| 我的日报 | `/我的日报 [日期]` | 查询自己的日报 | `/我的日报 昨天` |

#### 命令解析

使用正则表达式匹配：

```python
COMMAND_PATTERNS = {
    'help': r'^[/／]帮助|^[/／]help$',
    'summary': r'^[/／]日报汇总\s*(\d{4}-\d{2}-\d{2})?',
    'set_vacation': r'^[/／]设置调休\s+(\S+)\s*(\d{4}-\d{2}-\d{2})?',
    'cancel_vacation': r'^[/／]取消调休\s+(\S+)\s*(\d{4}-\d{2}-\d{2})?',
    'query_vacation': r'^[/／]查询调休\s*(\d{4}-\d{2}-\d{2})?',
    'my_report': r'^[/／]我的日报\s*(今天|昨天|\d{4}-\d{2}-\d{2})?',
}
```

#### 卡片交互设计

**1. 帮助卡片**

```json
{
  "header": {"title": "🤖 飞书机器人指令菜单"},
  "elements": [
    {
      "tag": "action",
      "actions": [
        {"tag": "button", "text": "📊 日报汇总", "value": "summary"},
        {"tag": "button", "text": "🏖️ 设置调休", "value": "set_vacation"}
      ]
    }
  ]
}
```

**2. 日报汇总卡片**

显示当日日报统计和详情，支持选择日期。

**3. 调休管理卡片**

显示当前调休人员列表，支持快速添加/删除。

---

### 3. 命令处理模块（CommandHandler）

#### 核心方法

```python
class CommandHandler:
    """命令处理器"""
    
    def handle_help(self, context) -> dict:
        """处理帮助命令，返回卡片消息"""
        
    def handle_summary(self, date=None) -> dict:
        """处理日报汇总命令"""
        
    def handle_set_vacation(self, name, date=None) -> str:
        """处理设置调休命令"""
        
    def handle_cancel_vacation(self, name, date=None) -> str:
        """处理取消调休命令"""
        
    def handle_query_vacation(self, date=None) -> str:
        """处理查询调休命令"""
        
    def handle_my_report(self, user_id, date=None) -> str:
        """处理我的日报命令"""
```

#### 响应格式

- **文本响应**: 简单结果直接返回文本
- **卡片响应**: 复杂结果使用飞书消息卡片
- **错误提示**: 友好的错误信息+使用示例

---

### 4. 日报提醒流程（修改）

#### 原流程

```
定时任务 (21:00) → 获取已提交用户 → 获取调休人员 → 计算未提交 → 发送提醒
```

#### 新流程

```
定时任务 (21:00)
    ↓
检查是否为工作日 (WorkdayCalendar.is_workday())
    ↓ 是工作日
获取已提交日报的用户
    ↓
获取调休人员 (VacationManager.get_vacation_users())
    ↓
计算未提交人员 = 所有人 - 已提交 - 调休
    ↓
发送提醒消息
    ↓ (如果是非工作日)
记录日志 "今天是休息日，跳过提醒"
```

#### 代码修改点

在 `ReminderSender.check_and_send_reminders()` 开头添加：

```python
# 检查是否为工作日
from utils.workday_calendar import WorkdayCalendar

calendar = WorkdayCalendar()
if not calendar.is_workday():
    logger.info(f"今天是休息日，跳过日报提醒")
    return
```

---

### 5. 考勤自动化（阶段2）

#### 数据源优先级

1. **主方案**: 飞书考勤 API
   - 接口: `attendance.v1.user_flow.query`
   - 需要权限: `attendance:user_flow:read`
   
2. **备用方案**: 审批事件监听
   - 监听审批通过事件
   - 解析请假类型和日期
   
3. **兜底方案**: 手动导入
   - 从考勤系统导出 Excel
   - 批量导入到 VacationManager

#### 同步策略

- 每天早上 9:00 自动同步一次
- 检测到审批事件时实时同步
- 保留手动设置优先级更高

#### AttendanceSync 接口

```python
class AttendanceSync:
    """考勤同步管理器"""
    
    def sync_from_feishu_api(self, date=None) -> dict:
        """从飞书考勤API同步"""
        
    def sync_from_approval(self, approval_instance) -> bool:
        """从审批事件同步"""
        
    def import_from_excel(self, file_path) -> dict:
        """从Excel导入"""
        
    def get_sync_status(self, date=None) -> dict:
        """获取同步状态"""
```

---

## 错误处理

### 1. 节假日API失败

**场景**: timor.tech API 无法访问

**处理**:
- 降级到本地配置文件 `config/holidays.json`
- 记录警告日志
- 如果本地配置也缺失，按周末规则判断（周一到周五为工作日）
- 发送管理员通知（可选）

### 2. 命令解析失败

**场景**: 用户输入命令格式错误

**处理**:
- 返回友好的错误提示
- 显示正确的命令格式示例
- 提供帮助卡片链接

示例：
```
❌ 命令格式错误

正确格式: /设置调休 <姓名> [日期]
示例: /设置调休 张三 2026-02-26

输入 /帮助 查看所有命令
```

### 3. 考勤API失败（阶段2）

**场景**: 飞书考勤API调用失败或无权限

**处理**:
- 保留手动设置功能正常运行
- 降级到审批事件监听
- 记录错误并通知管理员
- 在帮助菜单中提示当前模式

### 4. 并发安全

**场景**: 多个命令同时修改调休数据

**处理**:
- VacationManager 使用线程锁保护
- 文件操作使用原子写入
- 失败时重试机制

---

## 测试策略

### 单元测试

每个工具类独立测试：

1. **WorkdayCalendar**
   - 测试工作日判断逻辑
   - 测试缓存加载和刷新
   - 测试降级机制
   - 测试边界条件（跨年、节假日调休）

2. **CommandRouter**
   - 测试命令正则匹配
   - 测试参数解析
   - 测试路由逻辑

3. **CommandHandler**
   - 测试每个命令的业务逻辑
   - 测试错误处理
   - 测试权限验证

4. **AttendanceSync** (阶段2)
   - 测试API调用
   - 测试数据转换
   - 测试多数据源降级

### 集成测试

端到端测试：

1. 发送命令消息 → 接收响应
2. 定时任务触发 → 检查工作日 → 发送提醒
3. 考勤同步 → 调休设置 → 提醒过滤

### 边界测试

1. **日期边界**
   - 跨年日期
   - 2月29日（闰年）
   - 节假日调休日

2. **命令边界**
   - 空参数
   - 无效日期格式
   - 不存在的用户名

3. **并发边界**
   - 多个命令同时执行
   - 定时任务与命令冲突

---

## 性能考虑

### 1. 缓存策略

- 节假日数据缓存全年，减少API调用
- 命令频繁查询的数据使用内存缓存
- 设置合理的缓存过期时间

### 2. API调用优化

- 批量查询考勤数据，避免单次查询
- 使用异步调用，不阻塞主线程
- 设置合理的超时和重试

### 3. 数据库考虑

当前使用 JSON 文件存储，对于小团队（<50人）足够。如果团队规模扩大，考虑迁移到：
- SQLite（轻量级）
- Redis（缓存优化）
- PostgreSQL（企业级）

---

## 安全考虑

### 1. 权限控制

- 敏感命令（如日报汇总）仅限管理员或HR
- 普通用户只能查询自己的日报
- 调休设置需要验证权限

### 2. 数据保护

- 节假日缓存文件只读权限
- 调休数据文件权限控制
- API密钥安全存储（.env文件）

### 3. 输入验证

- 命令参数严格验证
- 日期格式校验
- 用户名白名单检查

---

## 实施计划

### 阶段1：基础功能（1周，2026-02-26 至 2026-03-04）

#### Day 1-2: 工作日日历
- [ ] 实现 WorkdayCalendar 类
- [ ] 集成 timor.tech API
- [ ] 实现缓存机制
- [ ] 编写单元测试
- [ ] 修改 ReminderSender 集成工作日判断

#### Day 3-4: 命令路由框架
- [ ] 实现 CommandRouter 类
- [ ] 实现命令正则匹配和路由
- [ ] 实现 CommandHandler 框架
- [ ] 集成到 app_ws.py 消息处理流程

#### Day 5-6: 核心命令实现
- [ ] 实现帮助命令（文本+卡片）
- [ ] 实现日报汇总命令
- [ ] 实现调休管理命令（设置/取消/查询）
- [ ] 实现我的日报命令
- [ ] 飞书卡片设计和实现

#### Day 7: 测试和文档
- [ ] 集成测试
- [ ] 边界测试
- [ ] 用户文档编写
- [ ] 部署上线

### 阶段2：考勤自动化（1周，待定）

#### Day 1-2: 权限和API测试
- [ ] 飞书考勤权限申请
- [ ] API调用测试
- [ ] 数据格式分析

#### Day 3-4: AttendanceSync 实现
- [ ] API数据获取
- [ ] 数据格式转换
- [ ] 与 VacationManager 集成
- [ ] 定时同步任务

#### Day 5-6: 多数据源适配
- [ ] 审批事件监听
- [ ] Excel导入功能
- [ ] 降级策略实现

#### Day 7: 测试和优化
- [ ] 完整测试
- [ ] 性能优化
- [ ] 文档更新

---

## 配置项

需要添加到 `.env` 文件：

```bash
# 工作日日历配置
HOLIDAY_API_URL=http://timor.tech/api/holiday/year/{year}
HOLIDAY_CACHE_FILE=data/holidays_cache.json
HOLIDAY_CONFIG_FILE=config/holidays.json

# 命令功能配置
COMMAND_ENABLED=True
COMMAND_ADMIN_USERS=user_id_1,user_id_2  # 管理员用户ID列表

# 考勤同步配置（阶段2）
ATTENDANCE_SYNC_ENABLED=False
ATTENDANCE_SYNC_TIME=09:00  # 每天同步时间
ATTENDANCE_API_MODE=api  # api/approval/manual
```

---

## 依赖项

无需新增 Python 依赖，使用现有的：
- `requests` - API调用
- `lark-oapi` - 飞书SDK
- `APScheduler` - 定时任务

---

## 回滚计划

如果新功能出现问题：

1. **工作日判断失败**
   - 降级到原有的每天提醒模式
   - 配置项: `WORKDAY_CHECK_ENABLED=False`

2. **命令功能异常**
   - 禁用命令路由
   - 保留原有消息处理流程
   - 配置项: `COMMAND_ENABLED=False`

3. **考勤同步问题**
   - 回退到手动设置模式
   - 配置项: `ATTENDANCE_SYNC_ENABLED=False`

---

## 交付物

### 阶段1
- [ ] 代码: `utils/workday_calendar.py`
- [ ] 代码: `utils/command_router.py`
- [ ] 代码: `utils/command_handler.py`
- [ ] 配置: `config/holidays.json` (备用)
- [ ] 修改: `utils/reminder_sender.py`
- [ ] 修改: `app_ws.py`
- [ ] 测试: `tests/test_workday_calendar.py`
- [ ] 测试: `tests/test_commands.py`
- [ ] 文档: `docs/COMMANDS.md` (用户手册)
- [ ] 文档: 更新 `README.md`

### 阶段2
- [ ] 代码: `utils/attendance_sync.py`
- [ ] 配置: 考勤相关配置项
- [ ] 测试: `tests/test_attendance_sync.py`
- [ ] 文档: `docs/ATTENDANCE_SYNC.md`

---

## 总结

本设计采用**轻量集成 + 渐进增强**策略，通过两个阶段逐步实现功能：

**阶段1（1周）** 解决核心痛点：
- ✅ 工作日智能提醒
- ✅ 便捷的指令操作
- ✅ 改善用户体验

**阶段2（1周）** 实现自动化升级：
- ✅ 考勤数据自动同步
- ✅ 减少手动操作
- ✅ 提高数据准确性

整体设计注重：
- **可靠性**: 多重降级方案，确保核心功能不受影响
- **可扩展性**: 模块化设计，便于未来增强
- **易维护性**: 代码清晰，测试完备，文档齐全

---

**设计批准**: ✅ 已批准  
**下一步**: 转入实施阶段，创建详细实施计划
