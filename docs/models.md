# Reference models

All bundled parameter values are synthetic design choices. They support reproducible experiments and interface development. Each model can be replaced by a better solver or a measured profile while retaining the experiment interface. Noise parameters describe simulated sensor noise; total measurement uncertainty also depends on model and calibration errors.

## Electrothermal bench

The heater has electrical resistance R, heat capacity C and thermal resistance Rth. Its actual supply voltage is the commanded voltage times a fixed specimen-specific gain. For a constant setting, electrical power is P = V²/R and the temperature follows

$$
C\frac{dT}{dt}=P-\frac{T-T_a}{R_{\rm th}},\qquad
T(t+\Delta t)=T_a+PR_{\rm th}+[T(t)-T_a-PR_{\rm th}]e^{-\Delta t/(CR_{\rm th})}.
$$

Default nominal values are R = 20 ohm, C = 12 J/K, Rth = 10 K/W and Ta = 295.15 K. Across synthetic specimens, electrical and thermal resistance vary by up to 20 percent. Supply gain varies by up to 4 percent. Setting `variation=0` fixes these values. The loose clamp multiplies thermal resistance by 1.6, preserving temperature at the instant of the change. Temperature offset is a fixed draw within ±0.15 K.

The public supply spans 0–5 V. Commands cost 0.02 s, clamp changes cost 2 s and attaching a new measurement channel costs 1 s. A read costs 0.2 s and samples at its end. Initially only the sample thermometer is attached. `connect` can add ambient temperature and the electrical meter. Noise standard deviations are 0.03 K, 1 mV and 0.1 mA by default.

The model assumes a uniform sample temperature, constant resistance, constant ambient temperature, negligible measurement loading and linear heat transfer. Its tests compare exact equilibrium, partition-independent evolution and electrical energy against heat storage plus heat lost. `fit_thermal` uses settled measurements and includes an intercept to account for a thermometer offset. Time-resolved diffusion, radiative loss or temperature-dependent resistance require additional physics.

## Fiber coupling bench

The laser responds to a requested power Pset with time constant tau, nominally 15 s. A shared source variation multiplies power by 1 + 0.015 sin(t/23 + phase). The initial coupling center is drawn independently on each axis from ±1.5 mrad and drifts at 0.2 μrad/s in x and −0.1 μrad/s in y. The coupling surrogate is

$$
P_{\rm fiber}=0.85P_{\rm laser}\exp\left[-\frac{(x-x_0(t))^2+(y-y_0(t))^2}{2\sigma^2}\right],
\qquad \sigma=0.8\ {\rm mrad}.
$$

This width is a synthetic angular acceptance parameter. Converting it to a particular lens, fiber mode and optical layout requires a calibrated optical model. The reference detector sees source variation before the fiber coupling. Closing the shutter zeros both optical signals. The power meter has a fixed 10–50 μW offset, 10 μW additive Gaussian noise and an upper range of 20 mW. `zero` estimates the offset with the shutter closed; that estimate persists with the scene.

Power readings integrate over 0.05 s and camera images over the configured exposure, using eight midpoint samples. This resolves the short detector window relative to the laser's slow dynamics. Mirror motions cost 0.1 s and shutter commands cost 0.02 s. A camera returns a fixed 16×16 image of the fiber output with 12-bit clipping. Its count model includes a Gaussian approximation to photon noise and a small read-noise term. Pixel counts are instrument units with a synthetic response coefficient, and the image requires camera calibration for quantitative photometry.

This model supports coupling alignment, reference selection, zeroing and exposure experiments. Polarization, coherent interference, spectral propagation and mechanical backlash require additional mechanisms. The simulator's continuing drift is linear, so the coupling maximum may eventually leave the mirror range during very long experiments.

## Battery pulse bench

Positive current discharges the cell. A one-RC equivalent circuit evolves remaining charge q and polarization voltage vp. With a constant current and relaxation time tau,

$$
\dot q=-I,\qquad
v_p(t+\Delta t)=IR_1+[v_p(t)-IR_1]e^{-\Delta t/\tau},\qquad
V=U(q/Q)-IR_0-v_p.
$$

The synthetic open-circuit curve is U(z) = 3 + 1.2z + 0.04 tanh(8(z−0.5)) V. Nominal capacity is 2.5 Ah, R0 = 0.06 ohm, R1 = 0.03 ohm and tau = 45 s. Initial state of charge lies between 45 and 75 percent. Capacity and R0 vary by up to 15 percent. Voltage noise is 1 mV, current noise 0.5 mA and temperature noise 0.03 K.

Heat generation uses I²R0 + vp²/R1. A lumped thermal model uses 120 J/K heat capacity, 8 K/W thermal resistance and 295.15 K ambient temperature. Integration uses steps of at most one second with exact charge and RC updates and midpoint polarization heating. Splitting arbitrary durations can change the thermal discretization error. Charge bounds shorten a step so that extracted charge and throughput remain consistent.

The supply permits −2 to +2 A. A command costs 0.02 s and a read 0.05 s. Protection latches when a sampled voltage crosses 2.7 or 4.25 V, temperature exceeds 323.15 K, or charge reaches a bound. It switches the current to zero and retains the cell's state. Voltage and thermal event timing have at most one integration step of resolution. The constants are simulation settings, not operating instructions for a physical battery.

The model supports pulse testing and relaxation analysis. Chemical aging, hysteresis, spatial diffusion and chemistry-specific voltage curves need empirical models and independent data. It supplies no cell-lifetime prediction.

## Independent fluid tank

Install `examples/tank-package` to add `fluid-tank`. A uniform tank with area A has inflow Qin, level h and a linear laminar outlet conductance k. Its balance is A dh/dt = Qin − kh and is integrated analytically under constant inflow. The state tracks accumulated inflow and outflow volumes.

Default area is 0.05 m² and nominal conductance is 0.0004 m²/s with ±10 percent specimen variation. A level reading has 0.5 mm Gaussian noise. Inflow spans 0 to 0.0002 m³/s. Reads and pump settings each take 0.1 s. The linear outlet represents a resistive laminar connection over its assumed operating range. An open orifice would require a different flow law.

## Adding empirical support

Record the device identity, experiment date, calibration conditions, measured channels and units. Fit on one part of the observations and compare predictions on independent conditions relevant to the intended use. Preserve measured data and fitted-model results as distinct records. State the tolerance in physical units and the observation uncertainty. A profile should describe its operating range and data reference, including failed predictions that restrict that range.

Useful background includes the [JCGM measurement uncertainty guide](https://www.bipm.org/en/doi/10.59161/jcgm100-2008e), [FMI co-simulation specification](https://fmi-standard.org/docs/3.0.2/) and the [National Academies report on digital twins](https://www.nationalacademies.org/read/26894/chapter/10).
