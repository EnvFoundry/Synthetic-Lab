# Contributing

A useful contribution makes a consequential experiment possible, improves a physical
prediction, or lets another researcher reproduce and challenge a result.

For a new domain, start with the independently packaged tank example and the
[research contract](docs/research-contract.md). Specify the scientific questions, measurable
signals, hidden variables, physical actions, units, time costs, governing equations, invariants,
validity range and failure conditions. Include an executable experiment that changes a condition
and makes a prediction on a branch or held-out setting.

The package entry point is `synthetic_lab.models`. The core discovers the package after
installation and process restart. Domain dependencies stay in that distribution. A maintained
model should expose `research = ResearchContract(...)`; catalogue discovery validates that every
action has a semantic role. Test a resumed measurement, a branch and at least one physical
relation. A real-instrument adapter should name the IOP operation it delegates to and define its
behavior after an uncertain outcome.

Calibration and assessment must use distinct observations. Record device or specimen identity,
conditions, units, model version and data reference. Report errors in physical units over the
claimed operating range. Keep failed held-out predictions when they establish a real limit.

For a bug, report the model version, operation sequence, expected observation and obtained
observation. Include a short reproduction with a seed or shareable trajectory. Remove private
device credentials and unpublished sample information from shared records.

```sh
python -m pip install -e '.[test,rl,agent]'
python -m pip install -e examples/tank-package
python -m pip install -e labs/optical-metrology
ruff check src labs examples scripts tests
ruff format --check src labs examples scripts tests
pytest -q
python examples/optimize_reaction.py
python -m build
```

The Verifiable Agent Gym integration test runs when its package is installed. CI installs a
pinned upstream revision, starts a real MCP stdio server and client, checks Gymnasium environments
and executes the reference experiments.

For protocol changes, also run the live cross-language examples in [spec/README.md](spec/README.md).
