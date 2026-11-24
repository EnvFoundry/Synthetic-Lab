# Contributing

A useful contribution makes an experiment possible, improves a physical prediction, or helps another researcher reproduce an experiment.

For a new domain, start with the [independent tank package](examples/tank-package). Specify the research question, measurable signals, physical actions, units, time costs, and equations and data behind the model. Include an experiment that changes a condition and produces an interpretable observation. Explain the operating range and how an independent measurement could challenge the model.

The package entry point is `synthetic_lab.models`. The core discovers the package after installation and process restart. Domain dependencies stay in that distribution. Test a resumed measurement and a branch, as well as a physical relation. A proposed real-instrument adapter should name the IOP operation it delegates to and its behavior after an uncertain outcome.

For a bug, report the model version, operation sequence, expected observation and obtained observation. Include a short reproduction with a seed or a shareable trajectory. Remove private device credentials and unpublished sample information from shared records.

```sh
python -m pip install -e '.[test,rl,agent]'
python -m pip install -e examples/tank-package
ruff check src examples tests
pytest -q
python -m build
```

The Verifiable Agent Gym integration test runs when its `agent_gym` package is installed. CI also installs a pinned upstream revision. The MCP test starts a real stdio server and client. The Gymnasium tests run the environment checker and a vector environment.
