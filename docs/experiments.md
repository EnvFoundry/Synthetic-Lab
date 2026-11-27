# Executable experiments

The first four reference results were obtained on 24 November 2026 with Python 3.12 and the version 1
reference models. The PyBaMM comparison was obtained on 27 November 2026 with PyBaMM 26.11.0.0 and
its `Chen2020` parameter set. The photonic-cavity comparison was obtained on 27 November 2026 with
PyMeep 1.35.1. All entries are simulated experiments. The commands regenerate their trajectories and
outputs. The PhysiCell model-2 results were run on 28 November 2026 with PhysiCell 1.14.2.

| Program | Result from its fixed configuration |
|---|---|
| `python examples/open_research.py` | Thermal resistance fitted as 8.0248 K/W. The held-out 3 V setting had a temperature prediction error of +0.0164 K. Changing the clamp increased measured temperature by 2.5281 K at the same commanded supply |
| `python examples/align_fiber.py` | Observation-only search increased measured coupling from 3.9233 mW to 8.6344 mW. The final image at 1 ms exposure had zero saturated pixels |
| `python examples/battery_pulse.py` | Rested, loaded and recovered terminal voltages were 3.59390 V, 3.48835 V and 3.57593 V. The final voltage reflects both charge removed and polarization relaxation |
| `python examples/learn_control.py` | Cross-entropy policy search learned a 4.07466 V bias and 1.09392 V/K feedback gain. On five held-out seeds, mean 100-step return was −8.58596, compared with −16.43462 for constant 4 V |
| `python examples/compare_pybamm_models.py` | From 0.8 initial state of charge, a 5 A discharge for 300 s produced 3.80603 V with SPM, 3.75235 V with SPMe and 3.75331 V with DFN. After 300 s rest, the predictions were 3.95265 V, 3.95265 V and 3.95195 V. SPM differed from DFN by 52.72 mV during the pulse; SPMe differed by −0.96 mV |
| `python examples/measure_photonic_cavity.py` | Three cavities with commanded defect spacings 1.25, 1.40 and 1.55 μm all placed their strongest sampled resonance at 5.37634 μm, inside the 5.35 ± 0.20 μm target band. Their normalized spectral contrasts were 0.62021, 0.40788 and 0.33083, so the 1.25 μm design was selected. The corresponding peak transmissions were 0.63223, 0.41718 and 0.33518 |
| `python examples/screen_tumor_organoid.py` | Model 2, seed 2027, one thread: concentrations 0.0, 0.6, 1.2 and 2.0 for 12 h followed by 6 h recovery left 74, 37, 27 and 20 viable cells. Resistant survivor fractions were 0.284, 0.405, 0.444 and 0.800. The illustrative burden–selection–exposure objective selected 1.2 |
| `python examples/compare_car_t_kinetics.py` | Model 2, seed 2029, one thread: after 18 h, untreated, 5 min, 20 min and 90 min dwell branches contained 289, 80, 86 and 85 live tumor cells. CAR-triggered deaths were 153, 148 and 155; contacts were 966, 427 and 259. The illustrative weighted objective selected 5 min. [Definitions and full results](car-t-spheroid.md) |

The learned thermal policy clips voltage to [0, 5] V. Training used seeds 10 and 11. Test seeds were
101 through 105. Higher return means a smaller combined temperature-tracking and voltage penalty
under the defined task. The reference experiment uses five test specimens, so comparisons concern
this small synthetic population.

The thermal fit includes a thermometer offset and uses electrical readback to estimate power. Its
held-out observation is separate from its three fitting points. This tests an experimental program
against an analytic model. An empirical result needs a device and corresponding measurements under
independent conditions.

The PyBaMM result demonstrates why a fidelity ladder belongs inside one experimental surface. At this
protocol, electrolyte transport accounts for most of the SPM-to-DFN voltage difference, while SPMe
and DFN agree closely on terminal voltage. Agreement at one pulse does not establish equivalence on
higher currents, lower state of charge, temperature changes or longer cycling; those conditions are
new experiments rather than assumptions.

The Meep result uses one seeded fabrication draw, a two-dimensional lossless dielectric, 8 pixels per
micrometre, 21 frequency samples and a straight-waveguide flux reference. The sampled wavelength grid
did not resolve a spacing-dependent resonance shift for these three candidates, while the normalized
spectral contrast changed by almost a factor of two. The experiment therefore selects the design by
contrast inside a target wavelength band rather than claiming that the three resonances are identical.
A finer spectral sweep, higher spatial resolution, three-dimensional slab model and measured material
response are separate experiments.

The organoid comparison uses absolute live counts relative to its matched untreated well. Dead-cell
clearance changes the denominator of viable fraction, so that fraction cannot measure tumor burden.
The explicit objective weights reflect a research preference within one synthetic response draw.

CAR-T model 2 replaces the earlier event counts and infiltration results. A kill requires a live-to-dead
transition, and infiltration uses the actual infusion-time tumor radius. The single reported draw
does not establish a monotonic relation between dwell time and infiltration.
