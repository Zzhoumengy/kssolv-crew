# Windows 安装与首次测试

本软件在桌面窗口中运行，不需要打开网站或手动启动网页服务。按下面步骤安装后，即可使用本机 MATLAB 和 KSSOLV 计算。

## 1. 准备环境

| 需要准备 | 说明 |
| --- | --- |
| Windows 64 位 | 当前安装脚本面向 Windows；其他系统尚未验证。 |
| Python 3.12，64 位 | 推荐使用包含 Tcl/Tk 的标准安装程序；安装时保留 pip、Tcl/Tk 和 Python Launcher，建议勾选加入 PATH。不要用 Python 3.14。 |
| MATLAB R2025b | 这是已完成真实计算验证的版本。需完整安装并激活许可证；仅 MATLAB Runtime 不够。先手动打开 MATLAB，确认可以使用，再关闭即可。 |
| 完整的 kssolv-3o-dev | 使用随完整发布包提供的文件夹，或自行放入相应位置；不要只复制部分文件或再套一层同名目录。 |
| 两种 API 密钥 | 自己的 Materials Project API Key，以及与所选模型对应的 LLM API Key。DeepSeek 用户需有可用额度。 |
| 网络连接 | 安装时下载 Python 依赖；使用时获取材料结构和调用语言模型。MATLAB 许可证也可能有联网或许可服务器要求。 |

安装脚本接受 Python 3.11–3.13，但还需匹配具体 MATLAB 版本的 Python 支持范围。为减少差异，首次安装建议直接使用上表组合。其他 MATLAB 版本未完成本项目端到端验证。

## 2. 解压软件

将完整发布 ZIP **全部解压**到可写的本地文件夹，例如 `D:\KSSOLV-Agent`。不要在 ZIP 预览窗口内直接运行，也不要放进 `Program Files`。

完整包解压后应类似：

```text
D:\KSSOLV-Agent\kssolv-crew\
├── install.cmd
├── start.cmd
├── package.cmd
├── pyproject.toml
├── src\
├── scripts\
├── docs\
└── kssolv-3o-dev\
```

源码包不含 KSSOLV，需要自行补齐。也支持将 `kssolv-3o-dev` 与 `kssolv-crew` 放在同一个父文件夹下。软件自动检测，无需在窗口选择路径；右上角“简易教程”可查看步骤和检测路径。缺失时请补齐目录或重新解压完整发布包。

不要复制他人电脑的 `.venv`，不要随包分发 API 密钥。已有旧版本的用户应使用维护后的源码重新打包；早先的 0.2.0 ZIP 不包含 0.2.1 的真实计算修复。

## 3. 首次安装

双击 **install.cmd**，保持安装窗口打开，等待出现：

```text
Installation completed. Double-click start.cmd to open the desktop app. No browser is required.
```

脚本会创建本机专用的 `.venv`，安装项目依赖、MATLAB Engine，并检查 Tk 和运行环境。R2025b 使用 `matlabengine==25.2.2`。下载速度取决于网络，只有看到完成信息才表示安装成功；安装成功不等于已完成一次 MATLAB 计算。

如果没有自动找到 Python 或 MATLAB，在 `kssolv-crew` 文件夹内打开 PowerShell，按实际安装位置修改以下路径后执行：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup.ps1 `
  -Python 'C:\Python312\python.exe' `
  -MatlabRoot 'C:\Program Files\MATLAB\R2025b'
```

KSSOLV 位于其他位置时，安装前可在同一个 PowerShell 窗口指定：

```powershell
$env:KSSOLV_ROOT = 'D:\software\kssolv-3o-dev'
.\install.cmd
```

这个设置仅作用于当前 PowerShell 会话；从该会话运行 `.\start.cmd` 时软件也能继承此路径。日常双击启动建议采用前述自动识别的目录结构，无需设置环境变量。

## 4. 打开软件并做首次真实测试

1. 双击 **start.cmd**，出现桌面窗口。
2. 填写自己的 **MP API Key** 和 **LLM API Key**。密钥不会自动保存，关闭后需重新输入。
3. DeepSeek 用户将 LLM 模型改为 **`deepseek/deepseek-flash`**，不要保留默认 OpenAI 模型。
4. 材料任务填写“计算硅 Si 的能带图”，MP ID 填 **`mp-149`**。
5. 首次保留参数：`ecut=20`、`nbnd=14`、网格 `2×2×2`、每段 `20` 点，PBE、Gaussian 展宽。
6. 模式选择 **执行 MATLAB 计算**，点击 **开始任务**，保持窗口打开，等待结果。只生成输入文件模式不会执行 SCF 或 NSCF。
7. 查看 **报告 / 日志 / 能带图**；点击 **打开图文报告** 可打开包含全部图片的独立 HTML 文件，也可从 **打开结果目录** 找到 `report.html`。图片已嵌入该文件，单独复制它即可分享；用浏览器打印可保存为 PDF。历史任务也可通过该按钮生成图文报告，无需重新计算。

MATLAB Engine 在后台以 `-nodesktop -nosplash` 启动 MATLAB，因此看不到 MATLAB 主窗口是正常的。每段计算期间日志可能暂时没有新增内容；总耗时取决于电脑性能和材料规模。

DeepSeek 模式每个任务最多两次 HTTP 请求，用于化学式规范化和报告，不自动重试；重新提交任务仍会重新请求。首次测试不必反复运行。更换材料时，请同步修改或清空 MP ID，避免继续使用 Si 的 `mp-149`。

## 5. 如何判断测试完成

任务结果位于项目 `runs\任务编号\`。真实计算应具有 MATLAB 日志、SCF 信息、能带数值文件和 PNG 图，而不仅是输入文件：

- `matlab.log`、`engine_console.log`：MATLAB 计算输出。
- `scf_info.json`：SCF 是否收敛及迭代信息。
- `band_data_*.json`、`plot_data_*.mat`：各段能带数值。
- `band_*.png`：能带图片；`report.md`：报告。

已验证的 Si 示例在本机 MATLAB R2025b 上完成了 SCF 6 次迭代和 10 段 NSCF；其他电脑的耗时、迭代次数和数值可能有所不同。本机测试额外生成的 `band_overview.png` 并非每次普通任务必有，逐段 PNG 即为正常输出。

状态中的 `completed_unverified` 表示流程已完成但尚未认证物理参数的系统收敛；不要将其直接理解为计算失败。应同时查看报告、`scf_info.json` 和日志。默认参数用于安装测试，正式研究仍需检查截断能、k 网格、空带数等收敛性；不应仅凭图片判断带隙。

## 6. 常见问题

| 问题 | 处理方法 |
| --- | --- |
| 提示找不到 Python，或版本不支持 | 安装标准 64 位 Python 3.12，或用上面的 `-Python` 指定路径；若项目原有 `.venv` 版本错误，将其改名备份后重新安装。 |
| 提示找不到 KSSOLV | 按第 2 步放好完整目录；检查是否多了一层文件夹。 |
| 找不到 MATLAB / Engine 安装失败 | 确认安装并激活了完整 MATLAB，再指定 `-MatlabRoot`；确认 Python 与 MATLAB 版本兼容。 |
| 下载依赖失败 | 检查网络或代理后重新运行 install.cmd。不要在日志或截图里附带密钥。 |
| 双击 start.cmd 没有窗口 | 先确认 install.cmd 成功；查看项目 `.runtime\desktop-error.log`。 |
| API 认证失败或额度不足 | 检查对应密钥、额度和模型名称，DeepSeek 密钥配 DeepSeek 模型。 |
| MATLAB 阶段失败 | 查看任务目录的 MATLAB 日志，检查许可证、KSSOLV 路径和伪势文件是否完整；不要仅重试语言模型。 |
| 想退出或停止 | 使用“停止当前任务”按钮；正常退出关闭桌面窗口。stop.cmd 只用于可选网页版。 |

## 7. 发给其他用户

维护者在当前项目中双击 **package.cmd**，将 `dist` 新生成、带时间戳的完整 ZIP 交给接收者，并附上本教程。不要直接发送旧的 0.2.0 压缩包或整份含个人运行数据的工作目录。接收者仍需自行安装 Python、MATLAB 并使用自己的密钥。

完整包包含 KSSOLV，但不包含 MATLAB 安装程序、许可证、本机虚拟环境和历史测试结果。打包不会替接收者验证其许可证、网络或驱动环境。详细步骤见 [打包说明](PACKAGING.md)，已验证范围见 [验证记录](VALIDATION.md)。
