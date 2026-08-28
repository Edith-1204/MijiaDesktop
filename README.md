# Mijia Desktop

Mijia Desktop（米家桌面控制中心）是面向 Windows 11 的开源米家设备控制应用。

项目当前按《Mijia Desktop 项目计划书 V1.0》分阶段开发。Phase 0 提供可运行的
PySide6 工程骨架；Phase 1 提供经 `MijiaAdapter` 隔离的命令行访问链路。

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

扫码登录时会在 `data/runtime/` 中短暂生成本地二维码，登录结束或失败后自动删除。
认证数据使用 Windows DPAPI 加密后保存，明文只存在于进程私有临时目录。

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

## License

GPL-3.0-or-later。详见 [LICENSE](LICENSE)。
