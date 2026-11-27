# Executable experiments

The first four reference results were obtained on 24 November 2026 with Python 3.12 and the version 1
reference models. The PyBaMM and PhysiCell results were obtained on 27 November 2026. The battery
comparison used PyBaMM 26.11.0.0 and its `Chen2020` parameter set; the organoid assay used PhysiCell
1.14.2. All entries are simulated experiments. The commands regenerate their trajectories and
outputs.

| Program | Result from its fixed configuration |
|---|---|
| `python examples/open_research.py` | Thermal resistance fitted as 8.0248 K/W. The held-out 3 V setting had a temperature prediction error of +0.0164 K. Changing the clamp increased measured temperature by 2.5281 K at the same commanded supply |
| `python examples/align_fiber.py` | Observation-only search increased measured coupling from 3.9233 mW to 8.6344 mW. The final image at 1 ms exposure had zero saturated pixels |
| `python examples/battery_pulse.py` | Rested, loaded and recovered terminal voltages were 3.59390 V, 3.48835 V and 3.57593 V. The final voltage reflects both charge removed and polarization relaxation |
| `python examples/learn_control.py` | Cross-entropy policy search learned a 4.07466 V bias and 1.09392 V/K feedback gain. On five held-out seeds, mean 100-step return was −8.58596, compared with −16.43462 for constant 4 V |
| `python examples/compare_pybamm_models.py` | From 0.8 initial state of charge, a 5 A discharge for 300 s produced 3.80603 V with SPM, 3.75235 V with SPMe and 3.75331 V with DFN. After 300 s rest, the predictions were 3.95265 V, 3.95265 V and 3.95195 V. SPM differed from DFN by 52.72 mV during the pulse; SPMe differed by −0.96 mV |
| `python examples/screen_tumor_organoid.py` | Four branches of one seeded organoid response draw received concentrations 0.0, 0.6, 1.2 and 2.0 for 12 h followed by 6 h recovery. Viable fraction fell from 1.000 to 0.545 and apoptosis rose from 0.000 to 0.455, while the resistant fraction among viable cells rose from 0.228 to 0.750. The stated burden–selection–exposure objective selected concentration 1.2 rather than the largest dose |

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

The PhysiCell experiment exposes a treatment trade rather than a monotone dose rule. Higher bath
concentration increased apoptosis and reduced viable burden, but the surviving population became
progressively enriched for the high-repair phenotype. The selected concentration depends on the
explicit relative cost assigned to residual burden, resistant enrichment and exposure. It is a
mechanistic comparison within one generic response draw, not a clinical dose recommendation.
