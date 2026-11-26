# Optical metrology laboratories

This independently installable domain package contributes two Synthetic Lab models:

- `thin-film`: deposition, annealing, broadband reflectometry, phase interferometry and pyrometry;
- `fluorescence-microscopy`: focus, stage motion, spectral channels, exposure, photon dose, drift,
  camera imaging and integrated fluorescence.

Install the Synthetic Lab core first, then this package:

```sh
python -m pip install -e .
python -m pip install -e labs/optical-metrology
synthetic-lab --db runs/optical.sqlite list
```

The package depends only on the core Python interface. Its models expose the same persistent
sessions, branches, catalogue contract, CLI, MCP and data export as built-in laboratories.

```sh
python examples/coat_thin_film.py
python examples/adaptive_microscopy.py
```

The models are transparent reduced-order environments for experiment design. Their coefficients
are generic. A device-specific package should replace them with measured optical response,
instrument geometry, process conditions and predictions on specimens or settings not used to
configure the model.
