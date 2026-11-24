# First executable experiments

These results were obtained on 24 November 2026 with Python 3.12 and the version 1 reference models. They describe simulated experiments. The commands regenerate the trajectories and results in `runs/`.

| Program | Result from its fixed seeds |
|---|---|
| `python examples/open_research.py` | Thermal resistance fitted as 8.0248 K/W. The held-out 3 V setting had a temperature prediction error of +0.0164 K. Changing the clamp increased measured temperature by 2.5281 K at the same commanded supply |
| `python examples/align_fiber.py` | Observation-only search increased measured coupling from 3.9233 mW to 8.6344 mW. The final image at 1 ms exposure had zero saturated pixels |
| `python examples/battery_pulse.py` | Rested, loaded and recovered terminal voltages were 3.59390 V, 3.48835 V and 3.57593 V. The final voltage reflects both charge removed and polarization relaxation |
| `python examples/learn_control.py` | Cross-entropy policy search learned a 4.07466 V bias and 1.09392 V/K feedback gain. On five held-out seeds, mean 100-step return was −8.58596, compared with −16.43462 for constant 4 V |

The learned policy clips voltage to [0, 5] V. Training used seeds 10 and 11. Test seeds were 101 through 105. Higher return means a smaller combined temperature-tracking and voltage penalty under the defined task. The reference experiment uses five test specimens, so comparisons concern this small synthetic population.

The thermal fit includes a thermometer offset and uses electrical readback to estimate power. Its held-out observation is separate from its three fitting points. This tests an experimental program against an analytic model. An empirical result needs a device and corresponding measurements under independent conditions.
