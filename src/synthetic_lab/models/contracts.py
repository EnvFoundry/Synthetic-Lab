"""Research contracts for the bundled laboratory models."""

from ..research import ResearchContract

FIBER_CONTRACT = ResearchContract(
    domains=("optics", "photonics", "scientific instrumentation"),
    phenomena=(
        "Gaussian mode coupling",
        "laser warm-up and common-mode power variation",
        "mechanical drift",
        "detector noise, offset and saturation",
    ),
    questions=(
        "How quickly can an unknown coupling maximum be found and tracked?",
        "Can reference measurements distinguish source variation from alignment loss?",
        "Which zeroing and exposure schedule gives the most informative measurements?",
    ),
    observables={
        "coupled_power": {
            "unit": "W",
            "description": "Power after the drifting fiber-coupling transfer function.",
        },
        "reference_power": {
            "unit": "W",
            "description": "Source power before fiber coupling.",
        },
        "image": {
            "unit": "count",
            "description": "A clipped 16 by 16 camera image of the output face.",
        },
    },
    latent_variables={
        "coupling_center": {
            "unit": "rad",
            "description": "Time-dependent angular position of peak coupling.",
        },
        "source_phase": {
            "unit": "rad",
            "description": "Phase of the shared source-power fluctuation.",
        },
        "detector_offset": {
            "unit": "W",
            "description": "Power-meter dark offset before zeroing.",
        },
    },
    interventions=("laser", "mirror", "shutter", "exposure", "zero"),
    invariants=(
        "Open-shutter coupled power never exceeds 85 percent of source power.",
        "Reference and coupled detectors share the same source fluctuation.",
        "Camera counts remain within the 12-bit range.",
    ),
    failure_conditions=(
        "The meter saturates or the camera clips at its finite range.",
        "The coupling maximum can drift outside the mirror range.",
        "Zeroing is invalid while the shutter is open.",
    ),
    validity_conditions=(
        "Single Gaussian angular coupling peak.",
        "Linear drift over the duration of an experiment.",
        "A first-order laser power response and additive detector noise.",
    ),
    limitations=(
        "No polarization, coherent interference, wavelength dependence or backlash.",
        "Camera response and beam shape are synthetic rather than device calibrated.",
        "Long experiments can move the peak outside the mirror range.",
    ),
    fidelity="analytical",
    action_semantics={
        "laser": {
            "kind": "control",
            "description": (
                "Set laser power; the emitted power approaches it with warm-up dynamics."
            ),
        },
        "mirror": {
            "kind": "control",
            "description": "Set two angular alignment coordinates.",
        },
        "shutter": {
            "kind": "configure",
            "description": "Open or block the optical path.",
        },
        "exposure": {
            "kind": "configure",
            "description": "Set the camera integration time.",
        },
        "read": {
            "kind": "measurement",
            "description": "Acquire one selected detector channel.",
        },
        "zero": {
            "kind": "configure",
            "description": "Estimate and retain the power-meter offset with the shutter closed.",
        },
        "wait": {
            "kind": "wait",
            "description": "Advance warm-up, drift and source variation without observing.",
        },
    },
    reference_methods=(
        "coarse-to-fine raster search",
        "normalized coupled-to-reference power",
        "online peak tracking",
        "held-out drift prediction",
    ),
    physical_counterpart="A free-space-to-fiber alignment bench",
)

THERMAL_CONTRACT = ResearchContract(
    domains=("heat transfer", "system identification", "scientific instrumentation"),
    phenomena=(
        "Joule heating",
        "lumped thermal storage",
        "thermal contact resistance",
        "sensor offset and channel selection",
    ),
    questions=(
        "Can electrical and thermal measurements identify heat-transfer resistance?",
        "Can a loose contact be distinguished from a change in heater power?",
        "Does a model fitted at several power levels predict a held-out level?",
    ),
    observables={
        "temperature": {
            "unit": "K",
            "description": "Sample temperature including a specimen-specific sensor offset.",
        },
        "ambient": {
            "unit": "K",
            "description": "Optional ambient-temperature channel.",
        },
        "electrical": {
            "unit": "V,A",
            "description": "Optional voltage and current channels for actual heating power.",
        },
    },
    latent_variables={
        "thermal_resistance": {
            "unit": "K/W",
            "description": "Specimen heat-transfer resistance.",
        },
        "heater_resistance": {
            "unit": "ohm",
            "description": "Specimen electrical resistance.",
        },
        "supply_gain": {
            "unit": None,
            "description": "Difference between commanded and actual supply voltage.",
        },
    },
    interventions=("supply", "clamp", "connect"),
    invariants=(
        "Electrical energy equals stored heat plus heat transferred to ambient.",
        "Temperature is continuous when contact conditions change.",
        "The same specimen parameters persist across all actions and branches.",
    ),
    failure_conditions=(
        "The available experiment time is too short to approach a useful thermal state.",
        "Missing electrical or ambient channels make competing explanations inseparable.",
        "The one-body model can fail under spatially distributed heating.",
    ),
    validity_conditions=(
        "Uniform sample temperature and constant heat capacity.",
        "Linear heat transfer to a constant ambient temperature.",
        "Constant electrical resistance and negligible measurement loading.",
    ),
    limitations=(
        "No spatial diffusion, radiation or temperature-dependent resistance.",
        "Contact is represented by one fixed resistance multiplier.",
        "Synthetic coefficients require device-specific calibration for prediction.",
    ),
    fidelity="analytical",
    action_semantics={
        "supply": {"kind": "control", "description": "Set heater voltage."},
        "clamp": {
            "kind": "intervention",
            "description": "Change the thermal contact condition.",
        },
        "connect": {
            "kind": "configure",
            "description": "Attach an additional measurement channel.",
        },
        "read": {"kind": "measurement", "description": "Read every connected channel."},
        "wait": {
            "kind": "wait",
            "description": "Advance thermal dynamics without observing.",
        },
    },
    reference_methods=(
        "steady-state regression",
        "transient time-constant fitting",
        "energy-balance residuals",
        "held-out power prediction",
    ),
    physical_counterpart="A resistive heater, clamp and attachable metrology",
)

BATTERY_CONTRACT = ResearchContract(
    domains=("electrochemistry", "energy storage", "system identification"),
    phenomena=(
        "charge balance",
        "ohmic and polarization voltage",
        "relaxation",
        "self-heating and protection",
    ),
    questions=(
        "Which pulse sequence identifies resistance and relaxation with least test time?",
        "Can early pulse data predict voltage recovery under a held-out schedule?",
        "How do thermal and voltage limits constrain usable power?",
    ),
    observables={
        "voltage": {
            "unit": "V",
            "description": "Terminal voltage under the current load and polarization state.",
        },
        "current": {
            "unit": "A",
            "description": "Measured applied current; positive current discharges the cell.",
        },
        "temperature": {"unit": "K", "description": "Lumped cell temperature."},
    },
    latent_variables={
        "state_of_charge": {
            "unit": None,
            "description": "Remaining charge normalized by specimen capacity.",
        },
        "polarization_voltage": {
            "unit": "V",
            "description": "One-RC dynamic voltage state.",
        },
        "specimen_parameters": {
            "unit": None,
            "description": "Capacity and resistance variation fixed for one cell.",
        },
    },
    interventions=("load",),
    invariants=(
        "Integrated current changes stored charge by the same amount.",
        "State of charge remains between empty and full bounds.",
        "Protection removes load while retaining electrochemical and thermal state.",
    ),
    failure_conditions=(
        "Voltage, temperature or charge bounds latch cell protection.",
        "An uninformative pulse schedule cannot identify resistance and relaxation separately.",
        "The equivalent circuit fails when omitted aging or diffusion dominates.",
    ),
    validity_conditions=(
        "One-RC equivalent circuit with a synthetic open-circuit voltage curve.",
        "Lumped temperature and constant circuit parameters.",
        "Integration intervals are short relative to unmodelled electrochemical dynamics.",
    ),
    limitations=(
        "No chemistry-specific hysteresis, diffusion, aging or lifetime prediction.",
        "Protection-event timing is resolved to the integration step.",
        "Synthetic parameters are not operating guidance for a physical cell.",
    ),
    fidelity="reduced-order",
    action_semantics={
        "load": {"kind": "control", "description": "Set charge or discharge current."},
        "wait": {
            "kind": "wait",
            "description": "Advance charge, polarization and temperature without observing.",
        },
        "read": {
            "kind": "measurement",
            "description": "Measure terminal voltage, current and temperature.",
        },
    },
    reference_methods=(
        "pulse-resistance estimation",
        "exponential relaxation fitting",
        "equivalent-circuit parameter estimation",
        "held-out current-profile prediction",
    ),
    physical_counterpart="A battery cycler with voltage and temperature sensing",
)

REACTION_CONTRACT = ResearchContract(
    domains=("chemistry", "catalysis", "materials synthesis"),
    phenomena=(
        "Arrhenius kinetics",
        "consecutive reactions",
        "catalyst deactivation",
        "reaction heat and thermal control",
        "instrument-dependent information",
    ),
    questions=(
        "Which temperature programme maximizes intermediate B before it converts to C?",
        "Which measurements distinguish primary kinetics from catalyst deactivation?",
        "How much selectivity is lost when faster conversion raises temperature and deactivation?",
        "Can a model fitted on one schedule predict a held-out temperature schedule?",
    ),
    observables={
        "temperature": {
            "unit": "K",
            "description": "Noisy reactor temperature from a fast thermometer.",
        },
        "absorbance": {
            "unit": "absorbance",
            "description": "Three-channel mixed spectrum of A, B and C.",
        },
        "concentrations": {
            "unit": "mol/L",
            "description": "Species-resolved chromatographic concentrations after a slower read.",
        },
    },
    latent_variables={
        "species_state": {
            "unit": "mol/L",
            "description": "True A, B and C concentrations that govern future reaction rates.",
        },
        "catalyst_activity": {
            "unit": None,
            "description": "Remaining active catalyst fraction.",
        },
        "kinetic_scales": {
            "unit": None,
            "description": "Specimen-specific rate and deactivation multipliers.",
        },
    },
    interventions=("set_temperature",),
    invariants=(
        "The closed reaction conserves A+B+C concentration.",
        "All species concentrations and catalyst activity remain nonnegative.",
        "The same latent state drives every instrument reading.",
    ),
    failure_conditions=(
        "The shutdown temperature trips thermal protection.",
        "Catalyst deactivation removes the remaining useful reaction rate.",
        "Overlong high-temperature schedules convert the desired intermediate to C.",
    ),
    validity_conditions=(
        "Well-mixed constant-volume batch reactor.",
        "Two irreversible first-order steps A to B to C.",
        "Arrhenius parameters and heat-transfer coefficients are constant within one specimen.",
        "The thermal jacket is represented by bounded proportional heating and cooling.",
    ),
    limitations=(
        "No mass-transfer limitation, reversible chemistry, phase change or spatial gradients.",
        "Synthetic spectra and parameter priors are not a calibrated chemical system.",
        "A real synthesis claim requires compound-specific chemistry and held-out measurements.",
    ),
    fidelity="reduced-order",
    action_semantics={
        "set_temperature": {
            "kind": "control",
            "description": "Change the jacket target; the reactor responds dynamically.",
        },
        "read": {
            "kind": "measurement",
            "description": "Choose a fast ambiguous or slow species-resolved instrument.",
        },
        "wait": {
            "kind": "wait",
            "description": "Advance reaction, deactivation and thermal dynamics without observing.",
        },
    },
    reference_methods=(
        "Arrhenius regression from multiple temperature schedules",
        "profile likelihood for kinetic identifiability",
        "model-predictive temperature scheduling",
        "held-out schedule prediction",
    ),
    physical_counterpart="A jacketed batch reactor with spectroscopy and chromatography",
    metadata={"primary_objective": "intermediate selectivity under finite experiment time"},
)

CONTRACTS = {
    "fiber": FIBER_CONTRACT,
    "thermal": THERMAL_CONTRACT,
    "battery": BATTERY_CONTRACT,
    "reaction": REACTION_CONTRACT,
}
