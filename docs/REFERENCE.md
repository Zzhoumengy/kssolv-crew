# 详细技术参考（初版说明存档）

安装、目录识别和发布步骤以项目根目录的最新版 README.md 与 docs/PACKAGING.md 为准。以下保留初版架构和计算约定；其中“未提供 KSSOLV”和旧命令是 2026-10-20 的历史记录，现已支持自动查找同级 KSSOLV 目录。

这是可安装的 Python 项目库。Web Server 接收自然语言任务、Materials Project API Key、LLM API Key；CrewAI Flow 管理流程；只有化学式规范化与报告由两个 CrewAI Agent 调用 LLM。结构查询、单位转换、SCF 参数、k 路径、MATLAB 调用、结果校验都是确定性 Python/MATLAB 代码。

**当前交付不含用户的 `kssolv-3o-dev`，也不含 MATLAB。** 按下文在你本机打包该目录即可。适配器按你提供的 KSSOLV3 脚本编写；没有拿到你的软件目录，所以真实 SCF/eband 兼容性及科学数值尚待本机验证，不能声称已经完成真实材料能带实测。

## 1. 项目与流程

```text
浏览器 / REST API
  → FastAPI：创建任务、排队、状态与下载
  → CrewAI BandFlow（Manager，确定性编排）
      → Formula Agent：自然语言 → 化学式（LLM）
      → Structure：mp-api → 原始结构 JSON / 候选记录
      → Converter：pymatgen + numpy → 标准原胞 / .m / 高对称路径
      → Calculator：MATLAB Engine → KSSOLV startup → SCF → eband NSCF
      → Validator：密度有限性、各段输出、文件与图片检查
      → Report Agent：已知事实 → 中文辅助报告（LLM）
  → 本地 runs/<job-id>：状态、事件日志、输入、图、MAT、报告
```

参考图片中的 VASP 已替换为 KSSOLV。Manager、结构、计算、校验使用 Flow 中的确定性节点，不额外调用语言模型。没有接入 MCP 服务；它不是本需求运行的前提。所谓“Memory”对应可审计任务文件，不启用 CrewAI 语义记忆，避免将密钥或前次计算混入任务。

```text
kssolv-crew/
  pyproject.toml                 Python 包与命令行入口
  src/kssolv_crew/
    server.py, web/index.html    Web/API、排队、状态与下载
    workflow.py, agents.py       CrewAI Flow 与两个受限 Agent
    materials.py, convert.py     MP 查询与确定性输入生成
    engine.py, matlab/*.m        MATLAB Engine 和原脚本适配层
    bundle.py, cli.py            发布打包与启动命令
  scripts/                      安装、启动、打包脚本
  tests/                        离线测试与真实计算集成入口
  docs/                         打包、接口、验证说明
  kssolv-3o-dev/                 由你在本机放入（可放外部目录）
```

## 2. 安装与启动（Windows PowerShell）

建议使用独立的 **Python 3.12**，同时核对所装 MATLAB 对 Python 的支持。系统默认的 Python 3.14 不在本项目声明的支持范围内。

进入此 README 所在目录后：

```powershell
# 将 Python 路径替换成自己的 Python 3.12。
powershell -ExecutionPolicy Bypass -File .\scripts\setup.ps1 `
  -Python 'C:\Python312\python.exe' `
  -MatlabRoot 'C:\Program Files\MATLAB\R2025b'

# KSSOLV 可放在项目外，完整保留它的内部文件。
powershell -ExecutionPolicy Bypass -File .\scripts\start.ps1 `
  -KssolvDir 'D:\software\kssolv-3o-dev'
```

浏览器打开 <http://127.0.0.1:8000>。输入材料任务和两种密钥，建议第一步指定 `mp-149`、化学式 Si，并选择“只生成输入文件”；确认 `config.json`、`primitive.json`、`.m` 后再提交“执行 MATLAB 计算”。`prepare` 仍会调用 MP 和 LLM，不需要 MATLAB。

密钥由每次请求传入；LLM 默认模型是可通过 `--model` 或 `KSSOLV_LLM_MODEL` 配置的 `openai/gpt-4o-mini`。本项目不替你申请密钥，不会将密钥写入任务输入文件。`--model` 使用 CrewAI 的模型名称，需对应该提供商的 API 密钥。没有硬编码密钥或在进程间改写全局 API Key。

手动安装等价于：

```powershell
C:\Python312\python.exe -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e '.[dev]'
# 必须从本机 MATLAB 对应的引擎目录安装，避免安装成其他发行版引擎。
.\.venv\Scripts\python.exe -m pip install 'C:\Program Files\MATLAB\R2025b\extern\engines\python'
.\.venv\Scripts\python.exe -m kssolv_crew.cli doctor
.\.venv\Scripts\python.exe -m kssolv_crew.cli serve --kssolv-dir 'D:\software\kssolv-3o-dev'
```

Linux/macOS 可用 `PYTHON=python3.12 MATLAB_ROOT=/path/to/MATLAB sh scripts/setup.sh`，随后 `KSSOLV_ROOT=/path/to/kssolv-3o-dev sh scripts/start.sh`。MATLAB/KSSOLV 本身需要支持目标系统。

## 3. 如何打包你的 KSSOLV 文件夹

**推荐：发布 ZIP，里面放 Python 项目源码和完整 KSSOLV 目录。打包不需要先安装项目依赖。**

```powershell
# 在项目根目录执行，换成你自己的 KSSOLV 绝对路径。
powershell -ExecutionPolicy Bypass -File .\scripts\package.ps1 `
  -KssolvDir 'D:\software\kssolv-3o-dev' `
  -Output 'dist\kssolv-crew-with-kssolv.zip'
```

得到：

```text
dist/kssolv-crew-with-kssolv.zip
└── kssolv-crew/
    ├── README.md、pyproject.toml、src/、scripts/、tests/、docs/
    ├── BUNDLE-MANIFEST.json
    └── kssolv-3o-dev/       ← 你提供的整个目录
```

**接收者解压后**，进入 `kssolv-crew`，安装 Python 和 MATLAB，再执行 `scripts/setup.ps1`，最后直接运行 `scripts/start.ps1`；无需指定 KSSOLV 路径，默认使用同级 `kssolv-3o-dev`。

目录名称必须恰为 `kssolv-3o-dev`。打包器不读取或修改其 MATLAB 代码、不检查接口，也不运行它；它只遍历文件、计算 SHA-256、压缩。支持大文件 ZIP64。保留普通文件及空目录，拒绝符号链接；目标 ZIP 必须位于 KSSOLV 目录之外且不能覆盖已有 ZIP。用户目录中的所有普通文件都会进入包，因此发布前自行确认内容和再分发授权。MATLAB 安装目录、运行时与许可证不属于该文件夹打包范围。

Python wheel、源码分发包以及更详细步骤见 [打包说明](docs/PACKAGING.md)。wheel 默认只含 Python 包、Web 页面和 MATLAB 适配器，体积大的 KSSOLV 使用相邻目录分发；不是单文件免安装 EXE，也不需要编译 KSSOLV。

## 4. MATLAB 计算约定

适配器 `src/kssolv_crew/matlab/run_kssolv_job.m` 中的关键顺序来自你的脚本：

```matlab
if exist('KSSOLV3.prj', 'file')
    openProject('KSSOLV3.prj');
else
    KSSOLV.startup();
end
pseudopotential.PpType('default');
crystal = feval(cfg.structure_function);
crystal.ecut = cfg.parameters.ecut;
crystal.autokpts = [reshape(cfg.parameters.mesh,1,[]) 0 0 0];
crystal.nbnd = cfg.parameters.nbnd;
crystal.smear = cfg.parameters.smear;
crystal.funct = cfg.parameters.functional;
[crystal, H] = scf(crystal);
NSCFOptions = options.NSCF();
NSCFOptions.rho0 = H.rho;
NSCFOptions.verbose = "on";
eband(crystal, NSCFOptions, kPoints);
```

附加代码只负责路径、日志、文件输出和有限性校验。不会改用 KSSOLV2 的 `plotband` 或其他计算软件。原测试类中的 `GACE`、`HT` 没有实际参与计算，因此这里没有添加额外开关。

- 默认值保持示例的 `ecut=20`、`autokpts=[2 2 2 0 0 0]`、`nbnd=14`、`smear='gaussian'`、`funct='PBE'`；每段 20 点。它们不是所有材料都可用的参数。`nbnd` 必须足够容纳赝势价电子和所需空带；程序不猜测赝势价电子数。ecut 沿用用户版本的原生单位，必须在该版本上核实。
- MP 默认按 `energy_above_hull` 最低、再按 ID 字符串排序选择结构；全部候选 ID 保存到 `selection.json`。若关心指定晶相，请提供 `material_id`。指定 ID 还会校验化学式是否匹配。
- MP 原始 `Structure.as_dict()` 保存到 `structure.json`。pymatgen 生成标准原胞，**该原胞和 k 路径使用相同坐标基**；转换后写 `primitive.json`。numpy 将晶格和原子位置从 Å 转成 Bohr。按 KSSOLV 约定 `C` 的列是晶格向量，`xyz` 每行是笛卡尔原子坐标；不把分数坐标直接写入 xyz。
- `.m` 文件按结构内容哈希命名并检查已有内容，不覆盖不同文件。运行目录通过 `addpath` 引入，因此无需往第三方 `example/structure` 写文件。若要手动归档到你的示例结构目录，可以复制生成的 `.m`；本适配器仍按函数名调用，不依赖其包命名空间。
- 多条不连续 k 路径拆成独立边，每边调用一次 `eband`，SCF 只运行一次，各边保存独立 PNG/FIG/MAT。图中边端点由 `config.json` 对照；避免把不相连的高对称点接成错误线段。当前未实现拼成单张连续总图。
- 当前仅支持有序、非磁性、非 SOC 的常规晶体流程；不处理部分占位、磁矩、自旋极化、DFT+U、混合泛函与 SOC。结构最多 200 原子，主要为本机研究原型；不会把 MP 的 VASP 输入参数当成 KSSOLV 参数。

## 5. 状态、日志与结果

状态：`queued → starting → normalizing → fetching_structure → preparing → calculating → reporting → completed_unverified`。仅准备输入以 `prepared` 结束；异常为 `failed`，超过默认 7200 秒为 `timed_out`，重启/关闭中断为 `interrupted`。报告 LLM 失败时保留确定性事实报告；化学式规范化失败则任务失败。

结果文件：`status.json`、`events.jsonl`、`selection.json`、`structure.json`、`primitive.json`、结构 `.m`、`config.json`、`facts.json`、`report.md`；真实计算另有 `matlab.log`、`engine_console.log`、`scf_state.mat`、每段能带 PNG/FIG、`plot_data_*.mat`、`engine_result.json`。MAT 中的 curves 是图对象数据，可能含参考线，不作为经过标定的能量本征值数据；不据此自动计算带隙。

每个任务用单独子进程执行，密钥通过 stdin 传入、不放命令行或磁盘。服务器默认只监听本机，单进程串行使用 MATLAB、内存队列最多 16 个任务。任务访问令牌仅创建时返回一次，读取状态和下载需 `Authorization: Bearer <token>`，磁盘只保存令牌哈希。前端令牌只在内存保存；刷新页面后需用之前保存的 API 返回值访问任务。API 详见 [接口说明](docs/API.md)。

任务日志只记录阶段与受控错误信息；远程异常原文不写入，以免泄露密钥。MATLAB 错误查 `engine_console.log`；MP/LLM 异常按阶段及异常类型排查。未启用 CrewAI tracing/telemetry 或长期记忆，子进程输出被丢弃。LLM 只接收任务文本/事实，MP Key 只用于 MP 客户端。请勿在自然语言任务中粘贴密钥。

CrewAI 自身的内部存储被定向到该任务的 `.crew` 子目录，不使用共享 AppData 数据库；Web 下载不暴露此子目录。

运行时使用一个服务器进程；不要开多个 worker 共享 runs。队列与密钥不跨重启恢复，重启后提交新任务。超时/退出会终止任务进程树；极端情况下 MATLAB 作为独立进程脱离进程树，需手动检查残留 MATLAB 实例。该原型不提供公网账户登录、全局认证、分布式队列和任务取消；如需远程共享，应在前面部署带认证和 HTTPS 的服务。

## 6. 测试与实际验证范围

```powershell
.\.venv\Scripts\python.exe -m pytest -q
# 真实 KSSOLV 集成测试：需要自己提供该目录、引擎与赝势。
$env:KSSOLV_ROOT = 'D:\software\kssolv-3o-dev'
$env:RUN_KSSOLV_INTEGRATION = '1'
.\.venv\Scripts\python.exe -m pytest -m integration -v
```

离线测试覆盖转换、单位和晶胞关系、结构缓存、MP 选择策略（模拟服务）、真实 CrewAI Flow 编排（替代 LLM/计算）、API 状态与鉴权、敏感数据不落盘、输出校验与完整目录打包。不调用实际外部 API，不将模拟结果视为物理计算。

本次 Windows / Python 3.12.14 实测：**18 项通过，1 项真实集成测试跳过**；wheel、sdist 已成功构建。`requirements-lock.txt` 保存本次 Windows 环境的依赖快照，换系统或 Python 版本时应重新解析依赖。

**必须在你的环境验证**：KSSOLV3 初始化、Crystal 构造、C/xyz 坐标约定、赝势可用性和泛函匹配、SCF 收敛、eband 的五列 cell 输入及图形行为、能量单位/费米能、nbnd 和截断能/网格收敛。适配器没有假定 `scf` 附加收敛返回字段，因此明确记录 `convergence_verified=false`。真实计算返回也只标 `completed_unverified`；不虚构带隙，不把输出存在当作科学收敛。

更多验证记录见 [验证范围](docs/VALIDATION.md)。

## 7. 参考接口文档

- [CrewAI Flow 官方文档](https://docs.crewai.com/en/concepts/flows)：Flow、start、listen 和 Crew 编排。
- [Materials Project 查询示例](https://docs.materialsproject.org/downloading-data/using-the-api/examples)：MPRester 和结构查询。
- [pymatgen symmetry](https://pymatgen.org/pymatgen.symmetry.html)：标准原胞与 Setyawan–Curtarolo 路径。
- [MathWorks Python 版本兼容表](https://www.mathworks.com/support/requirements/python-compatibility.html)、[Engine 安装](https://www.mathworks.com/help/matlab/matlab_external/install-the-matlab-engine-for-python.html)：须与本机 MATLAB 发行版匹配。

KSSOLV3 SCF/NSCF 的依据是用户给定脚本，而非公开 KSSOLV2 示例。Python 项目目前为研究原型；KSSOLV、赝势和 MATLAB 的许可由各自授权决定。
