# Synthetic Lab

**面向长期自主科研的物理合成实验室。**

[English](README.md) · [模型与适用范围](docs/models.md) · [项目宗旨与建设标准](docs/charter.zh-CN.md) · [Agent 与 RL 接口](docs/interfaces.md) · [发展方向](docs/roadmap.md)

研究者和 AI Agent 可以提出问题、选择仪器、改变实验条件、获得原始读数，并从同一个实验现场持续研究。供电后的温度会继续演化，电池保留电荷与极化历史，光纤耦合峰随实验时间漂移。每次操作的状态和结果一起保存，进程退出后可以接续，也可以从过去的某个模拟现场分出不同实验路线。

项目长期建设跨学科的实验环境。物理模型、真实测量和领域知识共同决定实验的适用范围。领域团队独立贡献装置、求解器和校准数据，人和 Agent 用同一组操作做开放研究、训练和比较。

## 运行第一项实验

需要 Python 3.11 或更高版本。核心运行层使用 Python 标准库。

```sh
git clone https://github.com/EnvFoundry/Synthetic-Lab.git
cd Synthetic-Lab
python -m pip install -e .
python examples/open_research.py
```

这项实验给发热电阻接入电压、电流和环境温度测量，在三个功率点估计热阻，再预测一个未参与拟合的功率点。随后从相同现场建立两条路线，比较松动夹具前后的温度。实验记录放在 `runs/`。

```python
from synthetic_lab import Lab

with Lab("runs/research.sqlite") as lab:
    experiment = lab.create("thermal", seed=31)
    experiment.act("connect", channel="electrical")
    experiment.act("supply", voltage={"value": 4000, "unit": "mV"})
    experiment.act("wait", seconds=600, operation_id="settle-1")
    print(experiment.act("read")["observations"])
    print(experiment.id)
```

下次打开同一个数据库，调用 `lab.session(saved_id)` 即可继续。重复使用同一个操作标识会得到原结果。两个客户端根据同一版本制定操作时，可用 `expected_revision` 检查现场是否已发生变化。

## 已实现的实验室

| 实验室 | 能操作和研究的内容 |
|---|---|
| `fiber` 光纤耦合 | 光源预热、二维调镜、关快门、功率计归零、参考功率、相机曝光。包含共同光源波动、漂移、噪声和饱和 |
| `thermal` 电热测量 | 调整供电、增加电测或环境温度通道、换夹具接触条件。研究热容、传热、功率和温度偏移 |
| `battery` 电池测试 | 选择充放电电流与静置时间，观察电压恢复、发热和保护状态 |
| `fluid-tank` 独立示例包 | 调整流入量、测量液位、辨识出口导流能力。安装后自动发现，沿用保存、恢复和分支接口 |

这四套模型目前依据解析关系、数值实现和合成参数先验。具体仪器的实测校准仍需逐台建立。电池模型已覆盖脉冲响应、极化与热过程，寿命预测需要后续增加老化机制与数据。每套模型的方程、噪声、操作耗时和近似写在模型说明中。[模型说明](docs/models.md)

## Agent、强化学习与评测

Python、CLI、JSON 行协议与 MCP 都调用同一个运行层。Gymnasium 提供热控制环境，支持固定种子、独立并行实例及预算截断。Verifiable Agent Gym 可以发现 `synthetic-thermal` 任务，让 Agent 自己安排测量来估计热阻。

```sh
python -m pip install -e '.[rl,agent]'
synthetic-lab --db runs/agent.sqlite mcp
# 另开终端运行策略学习示例
python examples/learn_control.py
```

策略学习示例用交叉熵方法优化反馈策略，在两个训练试样上学习，再用五个独立种子比较恒定供电策略。策略参数、种子与逐个试样的回报保存在 `runs/learned-control.json`。这是一项可复做的学习实验，其结果来自上述模拟器。[接口及接入方法](docs/interfaces.md)

## 结构与协作

`runtime.py` 管理实验会话、事务、操作结果与分支。`models/` 管理物理演化和仪器读数。`integrations/` 连接 Agent、RL 与任务框架。`calibration.py` 从带单位的观测拟合参数。`examples/` 提供完整实验，`tests/` 检查物理关系、恢复、并发和接口。

EnvFoundry 中，IOP 继续承担真实仪器操作与调度，Optics–Photonics AI Lab 提供专业光学计算，SeedEnv 准备依赖。Synthetic Lab 负责模拟现场与观测。Gym 定义任务，Data Engineering 和 AI Evaluation 负责后续数据与比较。本版的运行形式是本地 Python 和 SQLite，Agent 可在远程主机通过 stdio 接入。多用户云服务、实物数字孪生和跨装置样品转移列在后续开发目标中。[开发路线](docs/roadmap.md)

MIT 许可证。欢迎贡献可操作、可复做、能回答具体问题的领域实验室。[贡献说明](CONTRIBUTING.md)
