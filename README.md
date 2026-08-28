# Mijia Desktop

Mijia Desktop（米家桌面控制中心）是面向 Windows 11 的开源米家设备控制应用。

项目当前按《Mijia Desktop 项目计划书 V1.0》分阶段开发。Phase 0 提供可运行的
PySide6 工程骨架；登录、设备访问和统一设备模型将在后续阶段实现。

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

## License

GPL-3.0-or-later。详见 [LICENSE](LICENSE)。

