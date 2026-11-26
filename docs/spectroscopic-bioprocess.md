# Spectroscopic fed-batch bioprocess laboratory

`spectroscopic-bioreactor` models a well-mixed culture observed through OD600, reporter
fluorescence, Raman spectroscopy and an oxygen optode. Feed, aeration, temperature and optical
induction are controls; biomass, substrate, product and expression remain hidden process state.

## Process dynamics

The vessel stores total biomass, substrate and product masses and liquid volume. Concentrations
are computed from those masses at the current volume. Growth follows

$$
\mu=\mu_{\max}\frac{S}{K_S+S}\frac{O}{K_O+O}
\exp\!\left[-\left(\frac{T-T_*}{w_T}\right)^2\right]\exp(-1.5b).
$$

Feed adds liquid and substrate until the working volume is reached, at which point the feed
stops. Growth and product formation consume the same finite substrate pool. There is no outflow.
The reference feed is deoxygenated, so feeding also dilutes dissolved oxygen. Temperature,
reporter expression and reversible burden have finite response times. Induction raises reporter
expression and production while burden reduces growth.

Oxygen follows $\dot O=k_La(100-O)-q_{O,X}\dot M_X/V$, with time in hours and oxygen in percent
of air saturation. Each step integrates gas transfer analytically for its realized growth demand.
Substrate and available oxygen constrain growth before masses are updated; oxygen is not repaired
by clipping an unstable Euler step. Steps are at most 20 seconds and become shorter when oxygen
turnover is fast. The model omits maintenance and product-specific oxygen costs, cell death, pH,
population heterogeneity and explicit gas-phase dynamics.

## Optical observations

| Instrument | Observable | Measurement limitation |
|---|---|---|
| OD600 | saturating optical density | high biomass compresses the response |
| fluorescence | reporter expression times biomass | expression and biomass are confounded |
| Raman | five overlapping spectral bands | substrate, product and biomass contribute together |
| oxygen optode | dissolved oxygen | uptake sources cannot be separated by oxygen alone |

Acquisitions take 0.5, 1, 5 and 0.2 seconds respectively. Culture dynamics continue during that
interval; these reference instruments sample the final state with additive noise. They do not
model acquisition-window averaging or calibrated sensor response times.

## Induction experiment

```sh
python -m pip install -e . -e labs/spectroscopic-bioprocess
python examples/optimize_bioprocess.py
```

The study grows one culture, forks it into early, delayed, pulsed and dark induction schedules,
and compares public observations. Every branch spends 14,400 seconds on production including
control commands, followed by the same 6.7 seconds of measurements.

The Raman score is $I_3-I_0/6-7I_1/24$. These weights cancel the nominal substrate and biomass
responses, leaving a product-sensitive contrast. This uses the reference spectral coefficients;
it is not blind spectral identification. Gain variation, measurement noise and low-signal clipping
still affect the score, which is not a calibrated concentration or a total-product mass.

## Package structure and scope

`contract.py` describes scientific questions and assumptions. `physics.py` owns the process
balances and integration. `bioreactor.py` owns actions and optical observations. The shared runtime
supplies persistence, branching and agent interfaces.

Model version 2 changes oxygen integration, feed dilution and capacity handling. Start new
experiments for this version; existing version-1 sessions require their original model code.
Coefficients are generic synthetic priors. A strain-specific or device-specific twin requires
measured kinetics, sensor responses and predictions checked on additional culture runs.
