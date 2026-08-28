# Mijia Desktop

Mijia Desktop（米家桌面控制中心）是面向 Windows 11 的开源米家设备控制应用。

项目当前按《Mijia Desktop 项目计划书 V1.0》分阶段开发。Phase 0 提供可运行的
PySide6 工程骨架；Phase 1 提供经 `MijiaAdapter` 隔离的命令行访问链路；Phase 2
建立统一设备模型；Phase 3–8 已完成设备总览、通用/专用控制、状态管理、收藏与托盘，
以及完整设置页面。目前正在进行 Phase 9 Windows 打包与本机验收。

## 环境要求

- Windows 11 64 位
- Python 3.11–3.13（推荐 Python 3.12）

## 开发环境

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

启动应用：

```powershell
python -m app.main
```

运行测试：

```powershell
pytest
```

认证数据、二维码和运行日志均已从 Git 排除。任何 Token、Cookie 或认证数据都不得
提交到仓库。

## Phase 1 PoC

扫码登录时会在进程私有临时目录中生成二维码，应用退出时自动删除。认证数据使用
Windows DPAPI 加密后保存，明文只存在于进程私有临时目录。

```powershell
python scripts/mijia_poc.py login
python scripts/mijia_poc.py list
python scripts/mijia_poc.py spec --model xiaomi.light.ceil02
python scripts/mijia_poc.py get --did DEVICE_DID --siid 2 --piid 1
python scripts/mijia_poc.py set --did DEVICE_DID --siid 2 --piid 1 --value true --yes
python scripts/mijia_poc.py action --did DEVICE_DID --siid 2 --aiid 1 --yes
```

所有写入和 Action 命令都要求显式提供 `--yes`。UI 和脚本不得直接调用 mijiaAPI，
设备访问统一经过 `MijiaAdapter`。

## Phase 2 Device Model

`DeviceManager` 将 mijiaAPI 字典转换为统一的 `BaseDevice`，并根据 MIoT 规格生成
`DeviceCapability` 与 `DeviceAction`。设备类型采用 Capability 与设备族线索综合判断，
无法获取规格或无法识别的设备仍会以 `OTHER` 模型保留。

只读验证真实设备模型转换：

```powershell
python scripts/device_model_poc.py
```

## Phase 3 Main Window

主窗口包含侧边导航、全部设备页面、设备名称/型号搜索、响应式设备卡片、在线状态、
主要开关状态和快速开关。设备同步和控制均通过 `Worker` 在线程池中执行，Qt 主线程
只负责界面更新。

启动主窗口：

```powershell
python -m app.main
```

## Phase 4 Generic Device UI

设备卡片可进入详情页。通用控件工厂会根据 `DeviceCapability` 自动生成 Boolean、
带范围 Number、普通 Number、Enum 和 ReadOnly 控件，并根据 `DeviceAction` 生成
Action 按钮，因此未知设备无需专用界面也能展示和控制大部分 MIoT 能力。

属性写入和 Action 执行统一经 `DeviceManager` 调度到后台线程；失败时控件会恢复到
上一次确认的值。需要参数的 Action 当前只展示为禁用状态，避免无参数误调用。

## Phase 5 Specialized Device UI

灯、智能插座、风扇和空调会根据统一设备类型显示专用的“常用控制”页签，控件仍然
完全由 Capability 决定，不依赖具体设备型号；设备不支持的能力会自动隐藏。详情页
同时保留“全部属性”“Actions”和“设备信息”，确保专用界面不会降低设备兼容性。

四类专用控件及通用控件发出的操作都统一进入 `DeviceManager`，并由后台 `Worker`
执行。UI 模块不直接访问 mijiaAPI。

## Phase 6 StateManager

`StateManager` 使用刷新锁和状态缓存统一维护设备状态，通过 `DeviceManager` 将所有
可读属性按批次查询。刷新失败会自动重试一次并保留上一次缓存，成功后向 UI 发送
状态快照。

应用默认每 30 秒批量刷新一次设备主状态，设备页支持手动刷新；打开详情页时刷新
该设备全部属性，属性写入后只刷新对应属性，Action 成功后立即刷新对应设备。失败
属性会被隔离，不影响同批其他状态。定时器和 UI 只负责调度，网络查询始终由
`Worker` 执行。

## Phase 7 Favorites and Tray

设备卡片可收藏或取消收藏，收藏状态保存在用户配置目录的 SQLite 数据库中。收藏页
只展示收藏设备，并与全部设备页、状态缓存和托盘菜单保持同步。

Windows 系统托盘提供打开主界面、刷新设备、退出，以及具有可写 `on` 能力的收藏
设备快速开关。点击窗口关闭按钮时应用隐藏到通知区域；只有托盘“退出”会结束进程。

启动同步采用两阶段加载：设备列表获取后立即显示，缺失的 MIoT 控制规格在后台补全
并写入本地缓存。后续启动直接复用规格缓存，避免每次逐型号等待云端查询。

## Phase 8 Settings

设置页支持跟随 Windows、浅色和深色主题，5/10/30/60/120 秒或手动状态刷新，
开机自动运行、高级模式、重新登录与退出账号。设置通过 `QSettings` 持久化，开机启动
使用当前用户的 Windows Run 注册项，不需要管理员权限。

高级模式会在设备详情中显示独立的 `MIoT Debug` 页签，其中包含 DID、Model、
SIID/PIID/AIID、Property、Action 和原始 metadata；关闭高级模式时这些开发字段不会
出现在普通设备信息页。

## Phase 9 Packaging

建议使用标准 Python 3.12 创建独立的打包环境，避免开发工具注入的 DLL 搜索路径
影响 Qt 依赖解析：

```powershell
py -3.12 -m venv .venv-packaging
.venv-packaging\Scripts\python.exe -m pip install -e ".[packaging]"
powershell -ExecutionPolicy Bypass -File scripts\build.ps1
```

构建产物位于 `dist\MijiaDesktop-0.1.0-alpha.exe`。该程序为无控制台窗口的单文件
EXE，包含 PySide6、mijiaAPI、Windows DPAPI 依赖、应用样式资源和版本信息。

## License

GPL-3.0-or-later。详见 [LICENSE](LICENSE)。
