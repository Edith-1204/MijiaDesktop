# Mijia Desktop 项目计划书 V1.0

## 一、项目概述

### 1.1 项目名称

**Mijia Desktop**

中文名称：

**米家桌面控制中心**

### 1.2 项目定位

Mijia Desktop 是一款面向 Windows 11 平台的开源桌面应用，用于在电脑端查看和控制用户米家账号下的智能设备。

项目以“轻量、稳定、快速控制”为核心目标，不试图完整复制米家 APP，而是重点解决以下场景：

- 在 Windows 桌面快速查看米家设备状态；
- 直接控制常用智能设备；
- 将常用设备加入收藏；
- 通过系统托盘快速开关收藏设备；
- 对不同米家设备进行动态适配；
- 为无法专门适配的设备提供通用控制界面；
- 为开发和兼容性排查提供高级 MIoT 调试能力。

项目采用免费开源方式发布。

---

# 二、项目目标

## 2.1 总体目标

开发一款稳定运行于 Windows 11 的米家桌面控制程序，实现：

```text
Windows Desktop
      ↓
Mijia Desktop
      ↓
mijiaAPI
      ↓
Xiaomi Cloud
      ↓
Mijia Devices
```

用户完成米家账号登录后，可以直接查看账号中的设备，并在电脑端进行设备控制。

---

## 2.2 V0.1 Alpha 核心目标

V0.1 必须打通完整链路：

```text
启动程序
    ↓
检测登录状态
    ↓
扫码登录米家
    ↓
获取账号全部设备
    ↓
识别设备能力
    ↓
显示设备列表
    ↓
查询设备状态
    ↓
控制设备
    ↓
收藏设备
    ↓
托盘快速控制
    ↓
关闭窗口最小化至托盘
    ↓
打包 Windows EXE
```

V0.1 的核心标准不是功能数量，而是：

**控制链路稳定、设备兼容机制合理、程序架构可持续扩展。**

---

# 三、用户需求基线

## 3.1 操作系统

主要目标平台：

**Windows 11 64 位**

V0.1 暂不将 Windows 10 作为正式测试平台。

---

## 3.2 米家账号

默认使用：

**中国大陆区域**

V0.1：

- 支持单米家账号；
- 使用扫码登录；
- 自动保存登录状态；
- 登录失效时要求重新登录；
- 设置页面允许主动退出账号。

---

## 3.3 设备范围

登录后读取：

**当前米家账号中 API 可获取的全部设备。**

不采用固定型号白名单。

优先优化设备类型：

- 灯；
- 风扇；
- 空调 / 空调伴侣；
- 智能插座。

但应用整体设计必须支持：

**全部设备可见。**

未知设备使用通用设备控制页面。

---

## 3.4 家庭和房间

V0.1 不实现：

- 家庭切换；
- 房间分类；
- 房间管理。

首页统一显示：

**全部设备。**

后续版本再增加房间功能。

---

## 3.5 系统托盘

系统托盘属于 V0.1 必选功能。

点击主窗口右上角关闭按钮时：

**不退出程序，而是隐藏窗口并最小化到系统托盘。**

托盘中展示：

- 打开主界面；
- 刷新设备；
- 收藏设备快速开关；
- 退出程序。

---

## 3.6 开机启动

默认：

**不开启。**

在设置页面提供：

```text
开机自动运行
```

开关。

---

## 3.7 状态刷新

默认：

**30 秒刷新一次。**

用户可以在设置页面修改刷新间隔。

建议可选：

```text
5 秒
10 秒
30 秒
60 秒
120 秒
手动
```

默认值：

```text
30 秒
```

---

## 3.8 设备排序

默认排序：

```text
收藏设备
    ↓
普通设备
```

同一级内：

**按设备名称排序。**

V0.1 不实现拖动排序。

---

## 3.9 UI 主题

支持：

- 浅色；
- 深色；
- 跟随 Windows 系统。

默认：

**跟随 Windows。**

---

## 3.10 高级模式

设置中提供：

```text
高级模式
```

开启后允许显示：

- DID；
- Model；
- SIID；
- PIID；
- AIID；
- Property；
- Action；
- 原始 MIoT 信息；
- 部分 API 返回数据；
- 调试信息。

该功能主要用于：

**设备兼容性分析与开发调试。**

---

# 四、参考技术基础

项目使用：

**Do1e/mijia-api**

作为米家接口层。

mijiaAPI 当前基于 Python，要求 Python 3.10 及以上，并提供扫码登录、设备列表查询、属性读取、属性写入以及设备 Action 调用能力。

其 `mijiaDevice` 已对 MIoT 的 SIID / PIID 机制进行了较高级的封装，可通过属性名称访问设备能力，并能够获取设备支持的 Property 和 Action 列表，因此适合作为桌面端动态设备模型的数据来源。

mijiaAPI 本身为 GPL-3.0-or-later，因此 Mijia Desktop 计划采用兼容的 GPL-3.0-or-later 开源许可。

---

# 五、技术选型

## 5.1 开发语言

推荐：

**Python 3.12**

最低建议：

```text
Python >= 3.11
```

---

## 5.2 GUI

采用：

**PySide6 / Qt 6**

原因：

- Windows 桌面支持成熟；
- 与 Python 设备控制代码天然集成；
- 支持系统托盘；
- 支持多线程和事件机制；
- 支持现代化 UI；
- 便于后续打包；
- 不需要额外维护 Web 前端和 IPC。

---

## 5.3 米家接口

采用：

```text
mijiaAPI
```

但必须通过：

```text
MijiaAdapter
```

进行二次封装。

任何 UI 模块都不得直接调用 mijiaAPI。

---

## 5.4 本地存储

采用：

```text
SQLite
+
QSettings / JSON
```

SQLite 保存：

- 收藏设备；
- UI 个性化数据；
- 本地设备别名；
- 部分设备元数据；
- 未来场景数据。

QSettings 保存：

- 主题；
- 自动刷新周期；
- 高级模式；
- 开机启动；
- 关闭窗口行为。

---

## 5.5 登录凭据

米家认证文件必须避免随意明文暴露。

优先考虑：

**Windows DPAPI**

必要时配合：

```text
%APPDATA%\MijiaDesktop\
```

存储加密后的认证数据。

日志中不得输出：

- Cookie；
- Token；
- Auth 数据；
- 账号密码；
- 完整认证请求。

---

## 5.6 日志

采用：

```text
logging
```

日志等级：

```text
INFO
WARNING
ERROR
DEBUG
```

默认：

```text
INFO
```

开启高级模式后允许：

```text
DEBUG
```

日志目录建议：

```text
%LOCALAPPDATA%\MijiaDesktop\logs\
```

---

## 5.7 打包

第一阶段采用：

**PyInstaller**

目标输出：

```text
MijiaDesktop.exe
```

后续可评估：

- Nuitka；
- MSIX；
- Windows Installer。

---

# 六、软件总体架构

采用分层架构：

```text
┌───────────────────────────┐
│          UI Layer         │
├───────────────────────────┤
│     Application Layer     │
├───────────────────────────┤
│ Device Abstraction Layer  │
├───────────────────────────┤
│       Mijia Adapter       │
├───────────────────────────┤
│         mijiaAPI          │
├───────────────────────────┤
│      Xiaomi Cloud         │
└───────────────────────────┘
```

---

# 七、模块设计

## 7.1 UI Layer

负责：

- 页面显示；
- 用户交互；
- 状态展示；
- 输入校验；
- 动画；
- Toast；
- Dialog。

UI 不允许：

```text
直接调用 mijiaAPI
```

---

## 7.2 AccountManager

负责：

- 登录；
- 登录状态判断；
- 登录失效检测；
- 注销；
- 认证数据路径管理。

接口示例：

```text
login()

logout()

is_authenticated()

ensure_authenticated()
```

---

## 7.3 MijiaAdapter

这是整个项目的重要隔离层。

负责把：

```text
mijiaAPI
```

转换成 Mijia Desktop 内部统一接口。

包括：

```text
login()

get_devices()

get_properties()

set_property()

run_action()

get_device_spec()
```

如果未来：

- mijiaAPI 接口变化；
- 更换米家 API；
- 增加其他实现；

只修改：

```text
MijiaAdapter
```

原则上不影响 UI。

---

## 7.4 DeviceManager

负责整个设备生命周期。

包括：

- 获取设备；
- 创建 Device 对象；
- 查询属性；
- 修改属性；
- Action 调用；
- 收藏设备；
- 设备查找；
- 设备类型识别。

---

## 7.5 StateManager

负责设备状态同步。

流程：

```text
mijiaAPI
   ↓
MijiaAdapter
   ↓
StateManager
   ↓
State Cache
   ↓
UI
```

StateManager 必须支持：

- 后台刷新；
- 批量查询；
- 刷新锁；
- 失败重试；
- 状态缓存；
- 信号通知。

参考库已经建议在多设备场景下优先使用批量属性查询，因此 StateManager 应尽量避免每个设备卡片单独请求云端接口。

---

# 八、设备抽象设计

## 8.1 BaseDevice

所有米家设备统一抽象为：

```text
BaseDevice
```

建议字段：

```text
did

name

model

device_type

online

favorite

properties

actions

primary_state

metadata
```

---

## 8.2 DeviceCapability

Property 统一转换成：

```text
DeviceCapability
```

例如：

```text
name

description

type

readable

writable

value

unit

min_value

max_value

step

enum_values

siid

piid
```

---

## 8.3 DeviceAction

Action 转换成：

```text
DeviceAction
```

包括：

```text
name

description

siid

aiid

parameters
```

---

# 九、设备类型识别

建立：

```text
DeviceClassifier
```

输出类型：

```text
LIGHT

FAN

AIR_CONDITIONER

PLUG

SENSOR

CURTAIN

PURIFIER

HUMIDIFIER

VACUUM

CAMERA

OTHER
```

判断依据优先级：

```text
model
+
MIoT spec
+
properties
+
actions
```

不能识别的设备：

```text
OTHER
```

---

# 十、设备 UI 策略

采用：

**专用 UI + 动态通用 UI。**

---

## 10.1 灯

优先适配：

```text
on

brightness

color-temperature

color

mode
```

显示形式：

```text
电源
亮度 Slider
色温 Slider
颜色
模式
```

---

## 10.2 风扇

优先适配：

```text
on

fan-level

mode

horizontal-swing

vertical-swing

angle
```

设备不支持时：

自动隐藏对应控件。

---

## 10.3 空调 / 空调伴侣

优先适配：

```text
on

mode

target-temperature

fan-level

swing
```

由于不同空调伴侣型号差异可能较大，应首先依赖 Capability，而不是型号硬编码。

---

## 10.4 智能插座

优先适配：

```text
on

electric-power

voltage

electric-current

power-consumption
```

---

# 十一、Generic Device UI

未知设备自动根据 Capability 构建 UI。

规则：

```text
bool + writable
→ Switch

number + writable + range
→ Slider

number + writable
→ SpinBox

enum + writable
→ ComboBox

readonly
→ Status Label

action
→ Button
```

例如设备返回：

```text
on                bool
brightness        1~100
mode              enum
temperature       readonly
```

界面自动生成：

```text
[开关]

亮度
────────●─────

模式
[自然 ▼]

温度
24.5 ℃
```

这部分应作为：

**V0.1 的核心架构能力。**

---

# 十二、页面规划

V0.1 只包含：

```text
LoginPage

DevicesPage

FavoritesPage

DeviceDetailPage

SettingsPage
```

---

# 十三、登录页面

首次启动：

```text
Mijia Desktop

登录米家

[二维码]

请使用米家 APP 扫码登录
```

登录成功：

```text
LoginPage
   ↓
Device Sync
   ↓
DevicesPage
```

---

# 十四、设备首页

页面结构：

```text
┌──────────────────────────────────────────┐
│ Mijia Desktop                      ─ □ × │
├──────────────┬───────────────────────────┤
│              │ 我的设备                  │
│  全部设备    │                           │
│              │ 搜索设备 __________       │
│  收藏        │                           │
│              │ [Device] [Device]         │
│  设置        │ [Device] [Device]         │
│              │                           │
└──────────────┴───────────────────────────┘
```

设备排列：

```text
收藏
↓
普通设备
```

分别按名称排序。

---

# 十五、设备卡片

设备卡片必须支持：

- 设备图标；
- 名称；
- 在线状态；
- 主要状态；
- 收藏按钮；
- 快速开关。

示例：

```text
┌─────────────────┐
│ 💡 书房台灯   ★ │
│                 │
│ ● 在线          │
│                 │
│       ON        │
│                 │
│ 亮度 70%        │
└─────────────────┘
```

---

# 十六、收藏页面

显示：

```text
favorite == True
```

的设备。

收藏设备同时进入：

**Windows 托盘快捷菜单。**

---

# 十七、设备详情页面

分为：

```text
常用控制

全部属性

Actions

设备信息
```

高级模式开启后增加：

```text
MIoT Debug
```

---

# 十八、系统托盘

程序启动后创建：

```text
QSystemTrayIcon
```

关闭窗口：

```text
hide()
```

不执行：

```text
quit()
```

托盘：

```text
Mijia Desktop

----------------

★ 台灯        开 / 关

★ 风扇        开 / 关

★ 空调        开 / 关

----------------

打开主界面

刷新设备

退出
```

只有同时满足：

```text
favorite == True
```

并且设备具有：

```text
on
```

能力时才显示快速开关。

---

# 十九、后台刷新机制

默认刷新周期：

```text
30 秒
```

推荐机制：

```text
QTimer
 ↓
StateManager
 ↓
Worker Thread
 ↓
mijiaAPI
 ↓
State Cache
 ↓
Signal
 ↓
UI
```

禁止：

```text
UI Thread
 ↓
requests
```

因为网络阻塞会造成 GUI 卡死。

---

# 二十、网络调用规范

所有网络 API：

**必须在工作线程执行。**

统一实现：

```text
Worker
```

负责：

- network call；
- exception capture；
- result；
- signal。

---

# 二十一、错误处理

至少定义：

```text
AuthenticationError

NetworkError

DeviceNotFoundError

DeviceOfflineError

PropertyReadError

PropertyWriteError

ActionError

UnsupportedDeviceError
```

普通用户界面不得出现：

```text
Traceback
```

例如：

```text
设备控制失败

“书房台灯”暂时没有响应。

[重试]
```

详细错误写入日志。

---

# 二十二、UI 设计规范

视觉方向：

**Windows 11 Fluent Design + 米家设备卡片语言**

界面要求：

- 简洁；
- 低信息噪声；
- 圆角；
- 适度留白；
- 状态信息清晰；
- 避免复杂菜单；
- 高频控制一到两次点击完成。

---

# 二十三、主题设计

主题：

```text
SYSTEM
LIGHT
DARK
```

默认：

```text
SYSTEM
```

系统主题改变时允许同步切换。

---

# 二十四、高级模式

Settings：

```text
[ ] 高级模式
```

开启以后：

设备详情额外显示：

```text
Model

DID

SIID

PIID

AIID

Raw Property

Raw Action

MIoT Spec
```

用于开发者诊断。

---

# 二十五、建议项目目录

```text
mijia-desktop/

├── app/
│
│   ├── main.py
│   ├── application.py
│
│   ├── core/
│   │   ├── account_manager.py
│   │   ├── device_manager.py
│   │   ├── state_manager.py
│   │   ├── settings_manager.py
│   │   └── exceptions.py
│
│   ├── mijia/
│   │   ├── adapter.py
│   │   ├── auth.py
│   │   ├── parser.py
│   │   └── classifier.py
│
│   ├── models/
│   │   ├── device.py
│   │   ├── capability.py
│   │   └── action.py
│
│   ├── ui/
│   │
│   │   ├── main_window.py
│   │
│   │   ├── pages/
│   │   │   ├── login_page.py
│   │   │   ├── devices_page.py
│   │   │   ├── favorites_page.py
│   │   │   ├── device_detail_page.py
│   │   │   └── settings_page.py
│   │
│   │   ├── widgets/
│   │   │   ├── device_card.py
│   │   │   ├── property_widget.py
│   │   │   └── action_widget.py
│   │
│   │   └── device_controls/
│   │       ├── generic_control.py
│   │       ├── light_control.py
│   │       ├── fan_control.py
│   │       ├── air_conditioner_control.py
│   │       └── plug_control.py
│
│   ├── services/
│   │   ├── tray_service.py
│   │   ├── startup_service.py
│   │   └── theme_service.py
│
│   ├── storage/
│   │   ├── database.py
│   │   └── repository.py
│
│   ├── workers/
│   │   ├── base_worker.py
│   │   ├── device_worker.py
│   │   └── state_worker.py
│
│   └── utils/
│       ├── logger.py
│       └── paths.py
│
├── resources/
│   ├── icons/
│   └── styles/
│
├── tests/
│   ├── unit/
│   └── integration/
│
├── scripts/
│
├── pyproject.toml
├── README.md
├── LICENSE
└── .gitignore
```

---

# 二十六、开发阶段

## Phase 0 — 项目初始化

目标：

建立可运行工程骨架。

完成：

```text
pyproject.toml

PySide6

mijiaAPI

logging

目录结构

基础配置
```

验收：

```text
python -m app.main
```

能够启动空白主窗口。

---

# 二十七、Phase 1 — mijiaAPI PoC

目标：

验证米家访问链路。

实现：

```text
扫码登录

获取设备列表

打印 Model

打印 DID

读取 Property

设置 Property

执行 Action
```

该阶段：

**暂时不重点开发 UI。**

验收：

至少一个真实设备完成：

```text
OFF
 ↓
程序控制
 ↓
ON
```

---

# 二十八、Phase 2 — Adapter 与设备模型

开发：

```text
MijiaAdapter

BaseDevice

DeviceCapability

DeviceAction

DeviceClassifier

DeviceManager
```

验收：

mijiaAPI 原始数据成功转换成统一 Device Model。

---

# 二十九、Phase 3 — 主界面

开发：

```text
MainWindow

Navigation

DevicesPage

DeviceCard
```

支持：

- 全部设备；
- 搜索；
- 在线状态；
- 基础状态；
- 快速开关。

---

# 三十、Phase 4 — Generic Device UI

这是 V0.1 的关键阶段。

实现：

```text
Capability
 ↓
Widget Factory
```

至少支持：

```text
Boolean

Number

Enum

ReadOnly

Action
```

验收：

未知设备无需写专用代码即可展示大部分可用属性。

---

# 三十一、Phase 5 — 专用设备 UI

按顺序开发：

```text
Light

Plug

Fan

Air Conditioner
```

专用控件不得直接访问 mijiaAPI。

必须使用：

```text
DeviceManager
```

---

# 三十二、Phase 6 — StateManager

实现：

- 30 秒定时刷新；
- 手动刷新；
- 控制后立即刷新；
- 批量属性查询；
- 状态缓存；
- 刷新异常处理。

---

# 三十三、Phase 7 — 收藏与托盘

实现：

```text
收藏

FavoritesPage

QSystemTrayIcon

收藏设备快速开关
```

关闭窗口：

```text
hide
```

退出：

只能通过：

```text
托盘 → 退出
```

或明确调用程序退出。

---

# 三十四、Phase 8 — 设置

实现：

```text
主题

状态刷新周期

开机启动

高级模式

重新登录

退出账号
```

---

# 三十五、Phase 9 — 打包

PyInstaller 构建：

```text
MijiaDesktop.exe
```

验收：

在未安装 Python 的 Windows 11 电脑上能够启动。

---

# 三十六、Phase 10 — Alpha 发布

创建：

```text
GitHub Release
```

发布：

```text
Mijia Desktop v0.1.0-alpha
```

包括：

- EXE；
- README；
- LICENSE；
- 已知问题；
- 支持设备说明。

---

# 三十七、测试计划

## 37.1 Unit Test

重点测试：

```text
DeviceClassifier

Capability Parser

Settings

Favorites

Device Model
```

---

## 37.2 Mock API Test

对 mijiaAPI 进行 Mock。

测试：

```text
login

device list

get prop

set prop

action
```

保证开发不完全依赖真实设备。

---

# 三十八、真实设备测试

至少测试：

```text
灯

风扇

空调伴侣

智能插座
```

测试内容：

```text
设备识别

状态查询

状态刷新

开关

属性修改

Action

掉线

网络异常
```

---

# 三十九、异常测试

至少覆盖：

```text
无网络

API 超时

Token 失效

设备离线

属性不存在

属性不可写

Value 越界

Action 失败

云端返回异常
```

---

# 四十、性能目标

V0.1 建议目标：

冷启动：

```text
< 5 秒
```

主窗口 UI：

```text
操作无明显卡顿
```

设备控制后 UI 反馈：

```text
立即显示操作中状态
```

网络响应最终状态：

```text
异步更新
```

支持至少：

```text
50 台设备
```

而不明显影响 UI 流畅度。

---

# 四十一、UI 状态设计

设备控制时不能简单等待云端结果。

推荐：

```text
用户点击 ON
 ↓
按钮进入 pending
 ↓
API 请求
 ↓
成功
 ↓
刷新真实状态
```

失败：

```text
恢复旧状态
+
Toast
```

---

# 四十二、日志规范

示例：

```text
INFO
Device sync started

INFO
38 devices loaded

INFO
Set property: device=xxxx property=on

ERROR
DeviceSetError device=xxxx
```

禁止：

```text
print(token)

print(cookie)

print(auth_json)
```

---

# 四十三、Codex 开发约束

后续使用 Codex 开发时，应始终遵守以下规则。

### 规则 1

**不要一次性实现整个项目。**

按 Phase 提交。

---

### 规则 2

任何 mijiaAPI 调用必须通过：

```text
MijiaAdapter
```

---

### 规则 3

UI 禁止调用：

```text
mijiaAPI
```

---

### 规则 4

网络操作不得运行于：

```text
Qt Main Thread
```

---

### 规则 5

新增设备支持优先扩展：

```text
Capability
+
Generic UI
```

其次才增加专用设备 UI。

---

### 规则 6

不要大量依赖：

```text
model == "xxxx"
```

进行设备逻辑判断。

---

### 规则 7

设备操作必须统一从：

```text
DeviceManager
```

进入。

---

### 规则 8

所有异常必须：

```text
捕获
↓
日志
↓
转换应用异常
↓
UI 提示
```

---

### 规则 9

不得将：

```text
Token

Cookie

Authentication Data
```

提交到 Git。

---

### 规则 10

每完成一个 Phase：

必须：

```text
运行测试

确认应用可启动

提交 Git Commit
```

---

# 四十四、推荐 Git 分支策略

主分支：

```text
main
```

开发功能：

```text
feature/*
```

例如：

```text
feature/auth

feature/device-model

feature/generic-device-ui

feature/system-tray
```

Bug：

```text
fix/*
```

---

# 四十五、推荐 Commit 风格

采用：

```text
feat:
fix:
refactor:
test:
docs:
build:
```

例如：

```text
feat: add mijia login support

feat: implement generic device control

fix: prevent UI blocking during property refresh

refactor: isolate mijia api adapter
```

---

# 四十六、V0.1 不做的功能

为了控制开发范围，明确排除：

```text
家庭管理

房间管理

设备配网

固件升级

米家自动化同步

视频监控

语音助手

多账号

插件系统

远程 HTTP API

Webhook

场景编辑器

历史曲线

设备拖动排序
```

后续按需求进入 V0.2 以后开发。

---

# 四十七、V0.2 候选功能

V0.2 优先考虑：

```text
家庭 / 房间

用户自定义排序

更多专用设备 UI

全局快捷键

Windows 通知

场景
```

---

# 四十八、V0.3 候选功能

进一步考虑：

```text
Windows 自动化

电脑锁屏触发

登录触发

定时任务

场景快捷方式

托盘高级控制
```

---

# 四十九、主要风险

## 49.1 米家接口风险

mijiaAPI 底层依赖非官方米家接口。

可能发生：

- API 参数变化；
- 登录机制变化；
- 云端风控；
- 请求频率限制。

对策：

```text
MijiaAdapter 隔离
```

---

## 49.2 设备差异

米家设备型号极多。

对策：

```text
Capability Driven UI
```

而不是：

```text
Model Driven UI
```

---

## 49.3 请求延迟

米家云端可能出现：

```text
500 ms
~
数秒
```

响应延迟。

因此所有请求必须异步。

---

## 49.4 状态不一致

控制成功后设备状态可能延迟更新。

采用：

```text
Optimistic UI
+
后续真实状态刷新
```

---

## 49.5 GPL

由于依赖 GPL-3.0-or-later 项目，Mijia Desktop 计划保持兼容 GPL 的开源发布方式。

---

# 五十、项目完成判定

V0.1 Alpha 达标必须同时满足：

### 登录

```text
可以扫码登录
```

### 设备

```text
可以读取账号设备
```

### 状态

```text
可以读取设备属性
```

### 控制

```text
可以设置可写 Property
```

### Action

```text
可以调用支持的设备 Action
```

### UI

```text
主界面无明显卡顿
```

### 通用设备

```text
未知设备能够通过 Generic UI 展示主要能力
```

### 收藏

```text
设备可以收藏
```

### 托盘

```text
收藏设备能够快速开关
```

### Windows

```text
关闭窗口进入托盘
```

### 主题

```text
支持 System / Light / Dark
```

### 设置

```text
可以修改刷新周期
```

### 调试

```text
高级模式可以查看 MIoT 信息
```

### 发布

```text
可以打包为独立 Windows EXE
```

---

# 五十一、推荐 Codex 第一条任务

项目正式开发时，不要先要求 Codex 创建完整 GUI。

第一条任务建议为：

```text
按照《Mijia Desktop 项目计划书 V1.0》创建项目基础工程。

要求：

1. 使用 Python 3.12 + PySide6；
2. 使用 pyproject.toml 管理项目；
3. 建立计划书规定的目录结构；
4. 创建 app/main.py；
5. 创建最基础 MainWindow；
6. 配置 logging；
7. 配置 pytest；
8. 配置 .gitignore；
9. 创建 GPL-3.0-or-later LICENSE；
10. 创建 README.md；
11. 暂时不要实现米家登录和设备控制；
12. 确保 python -m app.main 能启动窗口；
13. 确保 pytest 可以正常执行；
14. 完成后说明新增文件、运行命令及测试结果。
```

完成该任务后，再进入：

```text
Phase 1
mijiaAPI PoC
```

而不是直接开始开发设备卡片。

---

# 五十二、最终技术原则

整个项目应始终坚持：

**API 与 UI 分离。**

**设备型号与 UI 解耦。**

**网络线程与 UI 线程分离。**

**通用设备支持优先于型号硬编码。**

**DeviceManager 作为设备操作唯一入口。**

**StateManager 统一维护设备状态。**

**MijiaAdapter 隔离第三方 API。**

**先保证稳定，再增加功能。**

最终希望形成：

```text
米家 API
   ↓
统一设备模型
   ↓
设备能力抽象
   ↓
动态控制 UI
   ↓
Windows 桌面体验
```

这套架构既能够满足当前灯、风扇、空调伴侣和智能插座的控制需求，也能够在未来逐步扩展到更多米家设备，而无需大规模重构软件。