# 打包：推荐直接双击 package.cmd

当前目录 `智能体/kssolv-3o-dev` 会被自动找到。双击项目中的 **package.cmd**，在 `dist` 得到 `kssolv-crew-with-kssolv-年月日-时分秒.zip`。每次用新名称，避免覆盖已有发布包。

```text
发布包.zip
└── kssolv-crew/
    ├── install.cmd、start.cmd、start-web.cmd、stop.cmd、package.cmd
    ├── src/、scripts/、docs/、tests/
    ├── README.md、pyproject.toml、requirements*.txt
    ├── BUNDLE-MANIFEST.json
    └── kssolv-3o-dev/        完整的 KSSOLV 软件目录
```

接收者按 [安装与首次测试教程](INSTALL.md) 准备 Python 3.12（64 位、含 Tcl/Tk）和已激活的 MATLAB（已验证 R2025b），全部解压后双击 `install.cmd`，看到 `Installation completed` 后再双击 `start.cmd`。完整包不需要手工移动 KSSOLV。不要复制 `.venv` 到另一台电脑；虚拟环境由安装脚本重新创建。接收者使用自己的 API 密钥。

分发维护后的版本时请重新运行 package.cmd，使用新生成的带时间戳 ZIP；旧的 0.2.0 发布包不含 0.2.1 真实计算修复。请勿将整个开发目录（含个人配置或运行数据）直接发给别人。

start.cmd 默认打开原生桌面版，不使用浏览器或本机 HTTP 服务；关闭窗口退出，有运行中的任务会要求确认。可选网页版使用 start-web.cmd / stop.cmd。发布包不含 `.runtime` 中的服务令牌、PID 和日志。

## 可选命令

在项目根目录打开 PowerShell：

```powershell
# 指定输出名称，仍会自动识别 KSSOLV。
powershell -ExecutionPolicy Bypass -File .\scripts\package.ps1 `
  -Output 'dist\my-release.zip'

# 软件在其他位置时手动指定。
powershell -ExecutionPolicy Bypass -File .\scripts\package.ps1 `
  -KssolvDir 'D:\software\kssolv-3o-dev'

# 只打包项目，不包含 KSSOLV。
powershell -ExecutionPolicy Bypass -File .\scripts\package.ps1 -SourceOnly
```

支持同级目录和项目内部目录；显式 `-KssolvDir` / `KSSOLV_ROOT` 优先。原 KSSOLV 目录不被修改，文件全量压缩，SHA-256 记录在清单中。支持 ZIP64 和普通空目录，不支持符号链接。原目录需保持稳定，不要同时更新软件。发布前确认自己提供的软件内容可分发。

## 需要标准 Python 安装包时

```powershell
.\.venv\Scripts\python.exe -m pip install build
.\.venv\Scripts\python.exe -m build
```

wheel / sdist 放在 `dist`；wheel 只含 Python 包、Web 页面和 MATLAB 适配器，KSSOLV 用上面的 ZIP 分发。MATLAB 本身和许可证始终需要接收者自行安装。

完整依赖由 `pyproject.toml` 声明；`requirements-lock.txt` 是原 Windows / Python 3.12 验证环境的快照。MATLAB Engine 由安装脚本按本机 MATLAB 另行安装，不固定进跨机器依赖清单。
