# Working on Synthetic Lab

Read README.md and docs/design.md before changing the common runtime. Model equations and their operating assumptions are in docs/models.md. The long-term purpose and cross-domain requirements are in docs/charter.zh-CN.md.

Develop an experiment that someone can use to ask a scientific question. Keep objects, actions, observations, time and model versions explicit. A domain owns its scientific assumptions. The runtime owns durable operations and session history. Reuse EnvFoundry instrument, data and task interfaces where they already provide the required behavior.

Reference models currently produce simulated observations. Preserve source labels, units, raw signals and the distinction between a model's prediction and a measurement. A model fitted to real data still produces simulated readings. Describe the actual calibration data and applicable conditions when adding a calibrated device.

Keep latent parameters, random generator state and verifier answers outside agent observations. Evaluation hosts own the database and expose an episode's permitted tools. Public research tools may create and fork experiments. Python access to the database belongs to a trusted researcher.

Preserve atomic state, result and snapshot writes. A retry using the same operation identifier returns the original result. A model error leaves the previous state usable. Any model change affecting interpretation or future trajectories needs an explicit version and a decision about old sessions.

Prefer an independently packaged domain over adding dependencies to the core. Add a small test when a change can alter physics, units, resumption, isolation or tool behavior. Run the relevant examples and tests. Clearly state which observations are predicted, measured or fitted.

Use concrete language in documentation. Explain the equation, observable effect or supported workflow. New integration instructions should include a command or program that runs. Keep proposed research directions identified as proposals.
