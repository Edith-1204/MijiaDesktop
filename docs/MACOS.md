# macOS 移植测试版

macOS 支持从 v1.3.0 开始提供，保留 Windows DPAPI、注册表启动项和 EXE 打包流程。

## 运行和构建

- Python 3.11–3.13；支持 macOS 14 及以上，当前提供 Apple Silicon 构建。
- 当前依赖安装获得 PySide6 6.12.0，因此本地应用最低系统版本设置为 macOS 14。
- 使用 `bash scripts/build_macos.sh` 构建，结果为 `dist/MijiaDesktop.app`。
- 构建脚本可通过 `PYTHON=/绝对路径/python3 bash scripts/build_macos.sh` 指定解释器。
- 应用自带 Python 和 Qt，运行 `.app` 无需另外安装这些依赖。
- 包采用本机架构和临时签名，尚未进行 Developer ID 签名及 Apple 公证；Intel 构建
  和旧系统兼容性尚未验收。

## 平台适配

| 功能 | macOS 实现 |
| --- | --- |
| 登录凭据 | 私有目录中的 AES-GCM 加密文件，不使用钥匙串 |
| API 认证文件 | 仅在私有临时目录中使用，正常退出和退出账号时清理 |
| 应用数据 | `~/Library/Application Support/MijiaDesktop` |
| 日志 | `~/Library/Logs/MijiaDesktop` |
| 界面设置 | Qt QSettings 的系统原生存储 |
| 登录启动 | `~/Library/LaunchAgents/io.github.Edith-1204.MijiaDesktop.plist` |
| 后台驻留 | 菜单栏图标；AppKit Accessory 策略将应用移出程序坞 |
| 完全退出 | 菜单栏“退出”或 `⌘Q` |
| 应用分发 | PyInstaller `.app`，包含 macOS `.icns` 图标 |

macOS 凭据保存在 `~/Library/Application Support/MijiaDesktop/credentials/auth.dat`，
使用 AES-GCM 加密；随机生成的本地密钥保存在同目录的 `auth.key`。目录权限为 0700，
两个文件权限为 0600，仅限当前用户访问。密钥与数据同机保存，因此本方案的访问隔离
依赖当前用户和文件权限，不提供钥匙串的系统授权隔离。

应用不包含或调用 keyring，不再访问钥匙串。退出账号会同时删除本地认证文件和密钥。
此前测试版使用钥匙串，升级前请退出旧版；若没有本地认证文件，请重新扫码登录。
Windows 的 DPAPI
`auth.dat` 不能直接复制到 Mac 解密。

登录启动设置在下次登录 macOS 时生效，不会立即拉起另一个应用进程。建议先将 `.app`
放到固定位置再启用；移动应用后重新打开一次即可更新已启用的启动项。后台启动携带
`--hidden`，菜单栏不可用时会显示主窗口，避免应用无法访问。源码启动项依赖原来的
虚拟环境和项目目录，删除或移动这些路径后应重新设置。

关闭主窗口后切换到 AppKit Accessory 策略，整个应用图标退出程序坞，因此不会显示
后台运行小圆点；通过菜单栏“打开主界面”恢复窗口时切回 Regular 策略。打包配置使用
LSUIElement，静默启动也不会短暂显示程序坞图标。若用户自己固定了程序坞快捷方式，
该快捷方式由系统保留，后台应用本身仍使用 Accessory 策略。

点击或双击菜单栏图标只打开菜单，不弹出主窗口；只有选择“打开主界面”才恢复窗口。

## 验证范围

- 自动测试覆盖原有设备模型、控制界面、账号流程和状态管理，以及新增的本地认证加密、
  篡改校验、文件权限、临时文件清理、登录启动项读写和路径迁移。
- 已验证本地认证文件读写、权限和篡改检查；原生 AppKit 策略已验证关闭窗口隐藏
  程序坞、恢复窗口显示程序坞。
- `.app` 已完成本机构建、实际启动和登录页/设置页目视检查，验证了 `⌘Q` 退出。
- Windows DPAPI 集成测试只能在 Windows 运行。
- 尚未完成米家扫码、会话续期、真实设备控制、重启登录后的启动项验收，也未在 Intel
  Mac 上测试。这些需要账号、设备或对应系统环境。

平台实现参考 [PyCryptodome 文档](https://www.pycryptodome.org/src/cipher/modern) 和
[PyInstaller spec 文档](https://pyinstaller.org/en/stable/spec-files.html)。

## HTTPS 打包修复

使用带额外 TLS 策略的 Python 发行版构建时，`ssl.py` 可能依赖同目录下的
`codex-rejected-cas.pem`。spec 会在该文件存在时一并收集到应用中，保留运行时的
证书信任策略。遗漏该文件会在 SSLContext 初始化阶段触发 FileNotFoundError，
上层 requests 将其包装成 ConnectionError，表现为二维码生成失败。

连接错误日志只记录异常类型、errno 和代码位置，不记录认证 URL、Cookie 或票据。
