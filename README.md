# KSSOLV Crew 安装教程

通过桌面窗口输入材料任务，调用 Materials Project 获取结构，并使用本机 MATLAB 与 KSSOLV 计算能带。

## 1. 准备环境

- Windows 64 位。
- Python 3.12（64 位，安装时保留 pip、Tcl/Tk，建议勾选加入 PATH）。不要使用 Python 3.14。
- 已安装并激活的完整 MATLAB；已验证版本为 R2025b，不能仅安装 MATLAB Runtime。
- 完整的 `kssolv-3o-dev` 文件夹。
- 自己的 Materials Project API 密钥，以及对应模型的 LLM API 密钥。
- 可用网络，用于安装依赖、获取结构和调用语言模型。

## 2. 下载并解压

在 GitHub 仓库点击 **Code → Download ZIP**，然后全部解压到可写的本地目录。GitHub 自动生成的源码 ZIP 不含同级的 KSSOLV，请自行补齐；若下载的是维护者提供的完整发布包，则已包含 KSSOLV。

推荐目录结构：

```text
kssolv-crew/                 解压后的项目目录，名称可不同
├── install.cmd
├── start.cmd
├── pyproject.toml
├── scripts/
├── src/
└── kssolv-3o-dev/           完整 KSSOLV 文件夹
```

也支持将 `kssolv-3o-dev` 放在项目的同级目录。软件自动检测，无需选择路径。不要在 ZIP 预览中运行，也不要复制他人电脑的 `.venv`。

## 3. 安装并启动

1. 先手动打开 MATLAB，确认许可证正常可用，再关闭。
2. 在项目目录双击 **install.cmd**，等待出现 **Installation completed**。
3. 双击 **start.cmd** 打开桌面软件。

安装脚本会创建本机 `.venv`，安装 Python 依赖和 MATLAB Engine。R2025b 使用 Engine 25.2.2。首次下载可能需要等待；只有出现完成提示才代表安装成功。

若找不到 Python 或 MATLAB，在项目目录打开 PowerShell，按实际位置修改路径后执行：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup.ps1 `
  -Python 'C:\Python312\python.exe' `
  -MatlabRoot 'C:\Program Files\MATLAB\R2025b'
```

## 4. 首次计算

1. 填写自己的 **MP API Key** 和 **LLM API Key**。
2. 使用 DeepSeek 时，模型填写 **`deepseek/deepseek-flash`**，也支持简写 `deepseek`。不要将 DeepSeek 密钥配默认 OpenAI 模型。
3. 材料任务填写“计算硅 Si 的能带图”，MP ID 填 **`mp-149`**。
4. 保留示例参数：`ecut=20`、`nbnd=14`、SCF 网格 `2 2 2`、每段 k 点 `20`。
5. 选择 **执行 MATLAB 计算**，点击 **开始任务**，保持窗口打开，等待完成。“只生成输入文件”模式不运行 MATLAB。
6. 点击 **打开图文报告** 查看全部图片；`report.html` 可单独分享，也能通过浏览器打印为 PDF。

MATLAB 在后台运行，看不到主窗口是正常的。任务记录及结果保存在项目 `runs` 目录；历史报告无需重新计算即可打开。软件右上角有 **简易教程**。

更换材料时，请同步修改或清空 MP ID。密钥不会自动保存，关闭软件后需重新输入。DeepSeek 每个任务最多两次请求，重新提交会再次请求。

## 5. 常见问题

| 问题 | 处理方法 |
| --- | --- |
| 没有启动窗口 | 先确认 install.cmd 成功，检查 `.runtime/desktop-error.log`。 |
| 未检测到 KSSOLV | 将完整 `kssolv-3o-dev` 放入项目目录或项目同级；避免套两层同名目录。 |
| API 认证失败 | 检查密钥、模型和额度是否匹配。 |
| MATLAB 计算失败 | 检查许可证、Engine 版本、KSSOLV 与伪势文件，查看任务目录中的 MATLAB 日志。 |
| 安装下载失败 | 检查网络或代理后重新运行 install.cmd。 |
| 需要停止计算 | 点击“停止当前任务”；退出软件直接关闭窗口。 |

本项目已在 MATLAB R2025b 上完成 Si 的真实 SCF/NSCF 测试，其他 MATLAB 版本尚未完成端到端验证。默认参数用于首次测试，正式研究需自行检查截断能、k 网格和带数等收敛性。`completed_unverified` 表示流程完成但物理参数系统收敛尚未认证，不代表流程失败。
