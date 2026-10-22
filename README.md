# KSSOLV Crew 桌面版

现在可以直接在软件窗口里填写材料任务、API 密钥和参数，点击按钮运行。**不需要网站、浏览器、端口或命令输入。** 桌面版使用 Tk 原生窗口，直接启动原有 CrewAI / MATLAB 工作进程。

## 新用户先安装

其他电脑请按 [安装与首次测试教程](docs/INSTALL.md) 操作。推荐环境为 **Windows 64 位 + Python 3.12（含 Tcl/Tk）+ 已激活的 MATLAB R2025b**，并准备完整的 `kssolv-3o-dev` 文件夹和自己的两种 API 密钥。

解压完整发布包 → 双击 **install.cmd**，等到 `Installation completed` → 双击 **start.cmd**。完整步骤、常见问题和成功判断见教程；首次安装需要联网下载依赖。发布包不是免安装的独立 EXE，也不包含 MATLAB 或其许可证。

## 安装后怎么用

1. 打开 `智能体/kssolv-crew` 文件夹，双击 **start.cmd**。
2. 在桌面窗口填写 **MP API Key** 和 **LLM API Key**。
3. 输入材料任务；首次可保留示例“计算硅 Si 的能带图”和 MP ID `mp-149`。
4. 建议先选择“只生成输入文件”，点击 **开始任务**。核对结构与参数后，再选择“执行 MATLAB 计算”运行。
5. 在窗口下方切换 **报告 / 日志 / 能带图**。点击 **打开图文报告** 查看包含全部图片的 `report.html`，可单独复制分享，或用浏览器打印为 PDF。已有历史任务也支持生成，无需重新计算；原报告页是文字摘要。

MP ID 是可选的；改为其他材料时也应修改或清空原来的 mp-149。任务、模式、参数和 LLM 模型都可在窗口填写。两种 API 密钥只在当前会话内存中保留，不自动保存，关闭软件后需重新填写。

**DeepSeek 用户：LLM 模型填写 `deepseek/deepseek-flash`。** 此模式每个任务最多两次 HTTP 请求（规范化 + 报告），关闭思考模式，不自动重试；输出分别限制 192 / 600 tokens。不将 DeepSeek 密钥用于默认 OpenAI 模型。模型名依据 [DeepSeek 官方接口文档](https://api-docs.deepseek.com/zh-cn/)。

使用 MP 和 LLM 仍需要互联网；“不用网站”指不需要网页界面，并不是离线获取材料或离线调用语言模型。

## 目录保持这样即可

```text
智能体/
├── kssolv-3o-dev/       原软件，不需要移动或修改
└── kssolv-crew/
    ├── start.cmd       打开桌面版（默认入口）
    ├── install.cmd     首次安装 / 更新依赖
    ├── package.cmd     打包项目与完整 KSSOLV
    └── runs/           所有任务的输入、日志和结果
```

KSSOLV 路径会自动识别，无需手动选择。完整发布包包含该目录，源码包需自行补齐。窗口右上角的“简易教程”可查看操作步骤和当前检测路径。软件不会修改 KSSOLV 内部代码。

## 任务运行与退出

- 窗口保持响应，状态栏显示规范化、获取结构、生成输入、MATLAB 计算及报告阶段。当前窗口一次执行一个任务。
- 可点击 **停止当前任务**；已生成的文件保留。任务运行时关闭窗口会询问是否停止并退出。
- 历史任务保存在 `runs`，重新打开软件后仍可查看。异常退出的任务不自动重算，需重新提交；历史记录中未结束的状态应结合日志核对。
- 默认 `ecut=20`、`nbnd=14`、`2×2×2` 网格、每段 20 点，泛函 PBE、Gaussian 展宽。示例参数需要按材料做收敛测试。

## 换电脑 / 第一次安装

1. 安装 **Python 3.12（64 位，含 Tcl/Tk）** 和有许可证的 MATLAB。
2. 双击 **install.cmd**，等待 `Installation completed`。
3. 双击 **start.cmd**。

安装脚本优先复用项目虚拟环境、识别 MATLAB，安装对应 Engine 并检查 Tk 模块。Python 3.14 不适用于此项目。MATLAB R2025b 对应的引擎为 [MathWorks 官方发布的 25.2.2](https://pypi.org/project/matlabengine/25.2.2/)。

若自动识别不到，在项目目录 PowerShell 指定路径：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup.ps1 `
  -Python 'C:\Python312\python.exe' `
  -MatlabRoot 'C:\Program Files\MATLAB\R2025b'
```

双击没有窗口时，先运行 install.cmd；若有启动错误，可查看 `.runtime/desktop-error.log`。执行任务失败则在软件“日志”页及结果目录查看原因。

## 打包给别人

双击 **package.cmd**。`dist` 中生成包含完整 KSSOLV 的 ZIP。接收者解压后安装 Python / MATLAB，再运行 install.cmd → start.cmd。原始软件、Python 依赖与 MATLAB 仍受各自许可证和平台要求约束，ZIP 不包含 MATLAB 安装程序或许可证。

## 原网页版（可选）

原 Web/API 功能保留作兼容入口：**start-web.cmd** 启动，**stop.cmd** 停止。日常桌面使用不需要运行它们。直接关闭桌面窗口即可退出桌面版；stop.cmd 不负责关闭桌面版。

## 计算与验证范围

LLM 仅做化学式规范化和辅助报告；mp-api 获取结构，pymatgen/numpy 生成输入，MATLAB 按原计算流程执行 `scf → H.rho → options.NSCF → eband`。适配层负责输入转换、结果导出及统一能量参考。

0.2.1 已在本机完成 Si（mp-149）真实 MP / DeepSeek / MATLAB R2025b / KSSOLV 测试：SCF 6 次迭代达到阈值，10 段 NSCF 均返回有限的 14×20 能量数组，并统一到 SCF 费米参考。两次 DeepSeek 请求共输入 1180、输出 606 tokens。测试记录留在本机 runs，不装入发布包。

实际文件验证确认此版本 KSSOLV 使用行向量晶格，eband 返回数值而不自动绘图。适配层现按这些接口导出 JSON/MAT 与 PNG；SCF 收敛和参数系统收敛分开记录。物理参数的收敛性仍需具体材料验证，不会仅凭输出图就认证收敛或自动推断带隙。

[安装教程](docs/INSTALL.md) · [打包说明](docs/PACKAGING.md) · [验证记录](docs/VALIDATION.md) · [更新记录](docs/CHANGELOG.md) · [可选 Web API](docs/API.md)
