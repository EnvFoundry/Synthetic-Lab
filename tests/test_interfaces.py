import asyncio
import importlib.metadata
import json
import subprocess
import sys

import pytest

from synthetic_lab import Lab
from synthetic_lab.calibration import fit_thermal


def test_cli_continues_across_processes_and_json_protocol(tmp_path):
    prefix = [sys.executable, "-m", "synthetic_lab.cli", "--db", str(tmp_path / "cli.sqlite")]
    subprocess.run(
        prefix + ["create", "thermal", "--id", "demo", "--seed", "3"],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        prefix + ["act", "demo", "supply", '{"voltage": 4}'], check=True, capture_output=True
    )
    result = subprocess.run(prefix + ["status", "demo"], check=True, capture_output=True, text=True)
    assert json.loads(result.stdout)["configuration"]["supply_v"] == 4
    messages = "\n".join(
        ["[]", '{"id":1,"method":"act","params":{"session_id":"demo","action":"read","params":{}}}']
    )
    result = subprocess.run(
        prefix + ["serve"], input=messages + "\n", text=True, capture_output=True, check=True
    )
    replies = list(map(json.loads, result.stdout.splitlines()))
    assert replies[0]["error"]["type"] == "ValueError"
    assert replies[1]["result"]["observations"]["temperature"]["unit"] == "K"


def test_gymnasium_contract_and_episode_budget():
    pytest.importorskip("gymnasium")
    import numpy as np
    from gymnasium.utils.env_checker import check_env

    from synthetic_lab.integrations.gymnasium import ThermalControlEnv

    env = ThermalControlEnv(max_steps=4)
    check_env(env, skip_render_check=True)
    env.reset(seed=14)
    for _ in range(4):
        observation, reward, terminated, truncated, info = env.step(np.array([4], dtype=np.float32))
    assert not terminated and truncated
    assert observation.shape == (4,)
    assert "source" in info
    with pytest.raises(RuntimeError):
        env.step(np.array([4], dtype=np.float32))
    env.close()


def test_vector_environments_are_independent():
    gym = pytest.importorskip("gymnasium")
    import numpy as np

    from synthetic_lab.integrations.gymnasium import ThermalControlEnv

    env = gym.vector.SyncVectorEnv([ThermalControlEnv, ThermalControlEnv])
    observations, _ = env.reset(seed=[10, 11])
    next_observations, _, _, _, _ = env.step(np.array([[0], [5]], dtype=np.float32))
    assert next_observations.shape == observations.shape == (2, 4)
    assert next_observations[0, 2] < 0.01
    assert next_observations[1, 2] > 4.5
    env.close()


def test_installed_domain_package_uses_existing_runtime():
    pytest.importorskip("tank_lab")
    with Lab(":memory:") as lab:
        assert "fluid-tank" in {item["name"] for item in lab.catalogue()}
        tank = lab.create("fluid-tank", seed=11)
        tank.act("pump", flow={"value": 0.0001, "unit": "m3/s"})
        tank.act("wait", seconds=600)
        clone = tank.fork()
        assert tank.act("read")["observations"] == clone.act("read")["observations"]


def test_agent_gym_factory_via_entry_point():
    pytest.importorskip("agent_gym")
    from agent_gym.contracts import TaskSpec

    entry = list(
        importlib.metadata.entry_points(group="agent_gym.tasks", name="synthetic-thermal")
    )[0]
    task = entry.load()(TaskSpec("synthetic-thermal", seed=11, split="test"))
    try:
        environment = task.environment
        environment.call("connect", {"channel": "ambient"})
        environment.call("connect", {"channel": "electrical"})
        records = []
        for voltage in (0, 2, 4):
            environment.call("supply", {"voltage": voltage})
            environment.call("wait", {"seconds": 2400})
            records.append(environment.call("read", {}))
        estimate = fit_thermal(records)["thermal_resistance_k_per_w"]
        assert task.verify({"thermal_resistance_k_per_w": estimate}).passed
        assert not task.verify({"thermal_resistance_k_per_w": 100}).passed
        with pytest.raises(ValueError):
            environment.call("clamp", {"contact": "loose"})
    finally:
        environment.close()


def test_mcp_server_over_real_stdio():
    pytest.importorskip("mcp")
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    async def run():
        params = StdioServerParameters(
            command=sys.executable, args=["-m", "synthetic_lab.cli", "--db", ":memory:", "mcp"]
        )
        async with stdio_client(params) as (reader, writer):
            async with ClientSession(reader, writer) as client:
                await client.initialize()
                tools = await client.list_tools()
                assert {"operate", "fork", "history"} <= {tool.name for tool in tools.tools}
                created = await client.call_tool("create", {"model": "thermal"})
                assert not created.isError
                value = json.loads(created.content[0].text)
                result = await client.call_tool(
                    "operate",
                    {
                        "session": value["session"],
                        "action": "read",
                        "parameters": {},
                        "operation_id": "sample",
                    },
                )
                assert not result.isError
                assert "temperature" in json.loads(result.content[0].text)["observations"]

    asyncio.run(run())
