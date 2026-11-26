# Synthetic Lab

**面向开放科学研究的持久化、物理约束合成实验室。**

[English](README.md) · [前沿实验室图谱](docs/lab-atlas.md) ·
[研究契约](docs/research-contract.md) · [架构](docs/design.md) ·
[Agent 与 RL 接口](docs/interfaces.md) · [跨语言接口](docs/platform.md) · [贡献说明](CONTRIBUTING.md)

Synthetic Lab 让人和 AI Agent 面对同一个实验现场：改变装置，等待物理状态演化，获取
有噪声、有量程、有耗时的测量，从上次状态继续，或者从过去的现场分叉比较不同干预。
实验时间、样品隐状态和随机状态都随会话持久保存。

实验室目录同时提供操作接口和机器可读的**研究契约**：它能回答哪些
问题、可观测量与隐变量是什么、哪些动作构成干预、需要保持哪些物理关系、何时失效、
处于什么保真层级、有哪些领域参考方法。Python、CLI 和 MCP 共用这份实验描述。

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
原结果；`expected_revision` 用于发现基于旧现场做出的决策。每条结果都记录模型版本、
模拟时间区间、规范化参数、单位、来源和可见配置。

## 已实现的实验室

| 实验室 | 可研究的问题 | 模型基础 |
|---|---|---|
| `reaction` 选择性反应 | 设计温度程序与测量节奏，在动力学、失活和热效应耦合下提高中间产物 | 连续 Arrhenius 反应、催化剂失活、集总反应器热平衡 |
| `fiber` 光纤耦合 | 寻找并跟踪漂移峰值，区分光源波动与失准，选择归零和曝光 | 高斯耦合、光源预热、漂移、有限量程探测器 |
| `thermal` 电热辨识 | 区分供热变化和接触变化，预测未参与拟合的功率或夹具条件 | 焦耳热、集总热容和热阻 |
| `battery` 电池脉冲 | 设计脉冲辨识电阻和弛豫，并满足电压与温度限制 | 电荷平衡、一阶 RC 等效电路和自发热 |
| `thin-film` 光子薄膜 | 依据宽带反射、干涉相位与温度选择沉积和退火终点 | 薄膜干涉、生长、孔隙率、粗糙度和热致密化 |
| `fluorescence-microscopy` 荧光显微 | 在漂移与光漂白过程中选择焦面、视场、通道和光子剂量 | 衍射成像、探测统计和光漂白 |
| `spectroscopic-bioreactor` 光谱生物过程 | 联合 OD、荧光、Raman 与氧读数安排进料、曝气和光诱导 | 补料培养质量平衡、Monod 生长、氧传递、报告蛋白响应和生产负担 |
| `fluid-tank` 独立包 | 辨识出口导流能力并预测未见过的流入程序 | 体积平衡和线性液阻 |

这些是带合成参数先验的参考模拟器，不是具体设备的数字孪生。研究契约和模型文档明确
写出近似、有效条件和失败条件。真正的实物孪生必须具有明确对应物、校准数据、工作范围、
不确定度和未参与拟合条件上的预测结果。[反应实验室](docs/reaction-lab.md) ·
[光学计量实验室](docs/optical-metrology.md) · [光谱生物过程](docs/spectroscopic-bioprocess.md) ·
[模型说明](docs/models.md)

[前沿实验室图谱](docs/lab-atlas.md) 给出后续建设顺序：材料合成与催化、预测生物学、
电化学能源、半导体与光子制造、科学成像、聚变、地球系统、制造装配和量子控制。新的
领域作为独立安装包接入共同的运行时与研究接口。[领域包目录](labs/README.md) 列出安装方式。

## Agent、学习与数据

Python、CLI、JSON 行协议和 MCP 共用同一持久运行层。Gymnasium 提供固定种子和预算
截断的控制环境；Verifiable Agent Gym 让隐藏答案保留在评价端；JSONL 与校准接口保留
单位、操作身份、模型版本和数据引用。

```sh
python -m pip install -e '.[rl,agent]'
synthetic-lab --db runs/agent.sqlite mcp
```

所有接口返回的实验室目录都包含动作参数和研究契约。用于评价的 Agent 只看到允许的
操作与观测，样品隐状态、随机状态和评价答案留在实验拥有者一侧。

## 仓库边界

`runtime.py` 管理原子操作、会话、快照与分支；`research.py` 管理跨领域研究契约；
`models/` 管理物理演化、仪器观测和模型范围；`integrations/` 连接 MCP、Gymnasium 与
Agent Gym；`calibration.py` 从带单位的观测建立模型配置；`labs/optical-metrology/` 提供
独立安装的薄膜与显微实验室；`labs/spectroscopic-bioprocess/` 提供补料培养与光谱观测；
`examples/` 给出完整实验；
`tests/` 检查守恒关系、极限、持久化、隔离和真实接口往返。

`spec/` 定义公共数据结构，`packages/protocol-ts/` 和 `crates/protocol/` 分别提供
TypeScript 与 Rust 实现；两者读取由 Python 实验实际生成的数据。`sql/` 给出可执行的
关系表结构，并测试它与运行时的创建、接续操作是否一致。

在 EnvFoundry 中，IOP 负责真实仪器执行，领域仓库负责专业求解器，SeedEnv 负责依赖，
Gym 负责任务与评价，数据系统消费实验轨迹。Synthetic Lab 负责模拟实验状态与观测。
当前运行时是本地 Python + SQLite，TypeScript 和 Rust 已实现数据接口；Web 工作台
和持久求解服务仍是后续平台建设内容。科学方程由各领域包维护。

MIT 许可证。
