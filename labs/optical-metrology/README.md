# Optical metrology laboratories

This independently installable package contributes two laboratories and two Verifiable Agent Gym
task families.

| Laboratory | Controls | Measurements | Scientific problem |
|---|---|---|---|
| `thin-film` | deposition rate, shutter, substrate temperature and time | broadband reflectance, interferometric phase and pyrometry | infer and control a film-growth endpoint under uncertain deposition rate |
| `fluorescence-microscopy` | stage, focus, channel, illumination and exposure | camera image and field-integrated fluorescence | localize structure while drift and photon dose change later observations |

Install the core and this package:

```sh
python -m pip install -e .
python -m pip install -e labs/optical-metrology
synthetic-lab --db runs/optical.sqlite list
python examples/coat_thin_film.py
python examples/adaptive_microscopy.py
```

The models use the same persistent sessions, branches, research contracts, CLI, MCP and data export
as built-in laboratories. Their coefficients are generic reduced-order parameters. A
specific-device package can replace the optical response and process coefficients while retaining
the same experiment interface.

## Agent tasks

Install Verifiable Agent Gym in the task host, then list the registered families:

```sh
python -m pip install -e ../Verifiable-Agent-Gym
agent-gym list
```

### `synthetic-thin-film-endpoint`

The specimen starts with zero film thickness. Its actual growth rate and optical parameters vary by
task instance. The prompt supplies a target broadband spectrum and target phase at 632.8 nm. The
agent commands deposition, shutter state and waiting intervals, and chooses optical measurements.
Completion requires a closed shutter and a final phase and spectrum within the endpoint tolerances.

Interferometric phase guides fine deposition. Broadband reflectance separates endpoints that would
be ambiguous from one wavelength alone. The bundled targets lie before the first phase wrap so the
entry task measures feedback endpoint control; later families can add multilayers and wrapped phase.

### `synthetic-microscopy-focus`

The specimen plane is hidden and varies by task instance. The agent selects focus, illumination and
exposure, then observes camera images. The submitted focus must lie within 0.40 um of the specimen
plane while accumulated illumination dose stays below the instance budget.

Each image consumes fluorescence through the same photobleaching model used by the laboratory. A
high-dose sweep may locate focus but fail the dose objective. The bundled reference policy uses a
low-dose axial scan and image sharpness.

Both task families expose only public instrument operations. Their verifiers read hidden simulated
state from the task-owned experiment after the agent finishes.
