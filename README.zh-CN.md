# Synthetic Lab

**面向开放科学研究的持久化、物理约束合成实验室。**

[English](README.md) · [前沿实验室图谱](docs/lab-atlas.md) ·
[研究契约](docs/research-contract.md) · [架构](docs/design.md) ·
[专业求解器实验室](docs/solver-backed-laboratories.md) ·
[Agent 与 RL 接口](docs/interfaces.md) · [跨语言接口](docs/platform.md) ·
[实验数据](docs/artifacts.md) · [贡献说明](CONTRIBUTING.md)

Synthetic Lab 让人和 AI Agent 面对同一个实验现场：改变装置，等待物理状态演化，获取
有噪声、有量程、有耗时的测量，从上次状态继续，或者从过去的现场分叉比较不同干预。
实验时间、样品隐状态和随机状态都随会话持久保存。

实验室目录同时提供操作接口和机器可读的**研究契约**：它能回答哪些问题、可观测量与
隐变量是什么、哪些动作构成干预、需要保持哪些物理关系、何时失效、有哪些领域参考方法。
Python、CLI 和 MCP 共用这份实验描述。

## 运行实验

需要 Python 3.11 或更高版本。核心运行层只依赖标准库。

```sh
git clone https://github.com/EnvFoundry/Synthetic-Lab.git
cd Synthetic-Lab
python -m pip install -e .
python examples/open_research.py
python examples/optimize_reaction.py
python -m pip install -e labs/optical-metrology
python examples/coat_thin_film.py
python examples/adaptive_microscopy.py
python -m pip install -e labs/spectroscopic-bioprocess
python examples/optimize_bioprocess.py
python -m pip install -e labs/pybamm-battery
python examples/compare_pybamm_models.py
```

```python
from synthetic_lab import Lab

with Lab("runs/research.sqlite") as lab:
    experiment = lab.create("reaction", seed=13)
    experiment.act("set_temperature", setpoint={"value": 92, "unit": "degC"})
    experiment.act("wait", seconds=600, operation_id="stage-1")
    spectrum = experiment.act("read", instrument="spectrometer")
    alternative = experiment.fork()
    alternative.act("set_temperature", setpoint=320)
    print(spectrum["observations"])
```

重新打开数据库后，调用 `lab.session(saved_id)` 即可接续。同一操作标识与同一请求会返回
原结果；`expected_revision` 会拒绝基于旧现场做出的决策。每条结果记录模型标识、模拟
时间区间、规范化参数、单位、来源和可见配置。

耗时计算可以脱离提交客户端持续运行：

```sh
# 在安装了领域包的环境中创建一次。
synthetic-lab --db runs/research.sqlite create reaction --id reactor

# 客户端提交操作后即可退出。
synthetic-lab --db runs/research.sqlite submit reactor wait '{"seconds":3600}' \
  --operation-id stage-2

# 同一主机上的独立 Python 环境执行反应实验室计算。
synthetic-lab --db runs/research.sqlite worker --model reaction

# 客户端读取运行状态与最终结果。
synthetic-lab --db runs/research.sqlite operation reactor stage-2
```

提交、领取和写回结果只占用短事务；领域求解在 worker 进程中运行，不持续占用数据库
写锁。同一会话严格按提交顺序演化，不同会话可以并行。每个 worker 只需安装自己负责的
领域包和专业求解器。

大型图像、光谱、场数据和轨迹存放在实验数据库之外。操作记录只保存引用、单位、形状、
坐标轴和采集信息；客户端需要时再分块读取。连续操作与分支会共享未发生变化的大型状态。

成熟数值软件保留在独立领域包中。Synthetic Lab 负责把持久实验操作转成求解器输入，
再把选定的求解变量转成实验观测。PyBaMM 电池包是第一个实现：同一电流程序可以分别
交给 SPM、SPMe 和 DFN，而无需在本仓库重写其电化学方程。

已创建的实验保存公开动作说明。客户端提交操作、读取配置和分支实验时无需安装领域求解器；
创建实验和本地 `act` 调用需要领域包。当前 SQLite 由同一主机上的进程共用。

## 已实现的实验室

| 实验室 | 可研究的问题 | 模型基础 |
|---|---|---|
| `reaction` 选择性反应 | 设计温度程序与测量节奏，在动力学、失活和热效应耦合下提高中间产物 | 连续 Arrhenius 反应、催化剂失活、集总反应器热平衡 |
| `fiber` 光纤耦合 | 寻找并跟踪漂移峰值，区分光源波动与失准，选择归零和曝光 | 高斯耦合、光源预热、漂移、有限量程探测器 |
| `thermal` 电热辨识 | 区分供热变化和接触变化，预测未参与拟合的功率或夹具条件 | 焦耳热、集总热容和热阻 |
| `battery` 电池脉冲 | 设计脉冲辨识电阻和弛豫，并满足电压与温度限制 | 电荷平衡、一阶 RC 等效电路和自发热 |
| `pybamm-battery-spm` | 低成本探索大量电流程序，并和更完整的模型比较 | PyBaMM 单粒子模型与集总热模型 |
| `pybamm-battery-spme` | 研究电解液输运何时会改变电压与实验决策 | PyBaMM 含电解液单粒子模型与集总热模型 |
| `pybamm-battery-dfn` | 在同一电流程序下计算多孔电极输运 | PyBaMM Doyle–Fuller–Newman 模型与集总热模型 |
| `thin-film` 光子薄膜 | 依据宽带反射、干涉相位与温度选择沉积和退火终点 | 薄膜干涉、生长、孔隙率、粗糙度和热致密化 |
| `fluorescence-microscopy` 荧光显微 | 在漂移与光漂白过程中选择焦面、视场、通道和光子剂量 | 衍射成像、探测统计和光漂白 |
| `spectroscopic-bioreactor` 光谱生物过程 | 联合 OD、荧光、Raman 与氧读数安排进料、曝气和光诱导 | 补料培养质量平衡、Monod 生长、氧传递、报告蛋白响应和生产负担 |
| `fluid-tank` 独立包 | 辨识出口导流能力并预测未见过的流入程序 | 体积平衡和线性液阻 |

内置模型和降阶领域包采用合成参数先验。PyBaMM 包调用成熟求解器与参数库，但通用的
`Chen2020` 配置仍然不是某个具体电芯的数字孪生。具体实物孪生还需要明确对应物、实测
数据、工作范围，以及未参与拟合条件上的预测结果。[反应实验室](docs/reaction-lab.md) ·
[光学计量实验室](docs/optical-metrology.md) · [光谱生物过程](docs/spectroscopic-bioprocess.md) ·
[PyBaMM 电池实验室](labs/pybamm-battery/README.md) · [模型说明](docs/models.md)

[前沿实验室图谱](docs/lab-atlas.md) 给出后续建设顺序：材料合成与催化、预测生物学、
电化学能源、半导体与光子制造、科学成像、聚变、地球系统、制造装配和量子控制。新的
领域作为独立安装包接入共同的运行时与研究接口。[领域包目录](labs/README.md) 列出安装方式。

## Agent、学习与数据

| 接口 | 用途 |
|---|---|
| Python、CLI、JSON 行协议 | 发现、创建、提交、执行、接续、分支、读取历史和导出 |
| 领域 worker | 在独立依赖环境中运行耗时操作 |
| MCP stdio | 向 Agent 暴露同一组持久操作和排队操作 |
| Gymnasium | 固定种子与明确动作预算的控制环境 |
| Verifiable Agent Gym | 隐藏答案保留在评价端的任务 |
| 外部实验数据 | 将大型图像、光谱、场数据和轨迹存放在 SQLite 之外 |
| JSONL 与校准 | 带单位的轨迹和模型来源信息 |

```sh
python -m pip install -e '.[rl,agent]'
synthetic-lab --db runs/agent.sqlite mcp
```

所有接口返回的实验室目录都包含动作参数和研究契约。用于评价的 Agent 只看到允许的
操作与观测，样品隐状态、随机状态和评价答案留在实验拥有者一侧。

## 仓库边界

| 路径 | 职责 |
|---|---|
| `src/synthetic_lab/runtime.py` | 会话、有序操作队列、短事务、快照、分支和流式导出 |
| `src/synthetic_lab/worker.py` | 领域 worker 与可续租的操作领取 |
| `src/synthetic_lab/artifacts.py` | 大型状态与观测的流式存储 |
| `src/synthetic_lab/research.py` | 跨领域研究契约 |
| `src/synthetic_lab/models/` | 参考物理、仪器观测和模型范围 |
| `src/synthetic_lab/integrations/` | MCP、Gymnasium 与 Agent Gym 接口 |
| `labs/pybamm-battery/` | PyBaMM 驱动的 SPM、SPMe 与 DFN 电池实验室 |
| `labs/optical-metrology/` | 薄膜制造与荧光显微实验室 |
| `labs/spectroscopic-bioprocess/` | 补料培养与光谱过程实验室 |
| `spec/`、`packages/protocol-ts/`、`crates/protocol/` | 公共数据结构及 TypeScript、Rust 实现 |
| `sql/` | 会话、操作、worker 领取、快照和实验数据元信息 |
| `examples/` | 可直接运行的完整实验 |

在 EnvFoundry 中，IOP 负责真实仪器执行，领域仓库负责专业求解器，SeedEnv 负责依赖，
Gym 负责任务与评价，数据系统消费实验轨迹。Synthetic Lab 负责模拟实验状态与观测。
当前 worker 生命周期由 Python 实现；公共 SQL 与数据接口允许后续 Rust 服务和 TypeScript
工作台沿用同一操作语义，不复制科学方程。

MIT 许可证。
