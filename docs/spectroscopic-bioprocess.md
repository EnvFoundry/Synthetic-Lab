# Spectroscopic fed-batch bioprocess laboratory

The `spectroscopic-bioreactor` laboratory represents a well-mixed fed-batch culture whose
internal biomass, substrate, product and expression state must be inferred from optical process
measurements. It is intended for experiment design around induction timing, feed, oxygen transfer
and complementary spectroscopy.

## Process state

The vessel tracks total biomass, substrate and product mass together with liquid volume. Biomass
growth uses substrate, dissolved oxygen, temperature and a reversible production burden:

[
mu = mu_{max}
rac{S}{K_S+S}
rac{O}{K_O+O}
f_T(T) f_b.
]

Feed adds both liquid volume and concentrated substrate. Growth and product formation consume the
same substrate pool. There is no liquid outflow. A single dissolved-oxygen state follows transfer
toward air saturation and biomass-dependent uptake.

Optical induction has a finite reporter response time. Strong induction raises production but also
raises a reversible burden that reduces growth, creating a genuine timing trade between building
biomass and entering a production state.

## Optical measurements

| Instrument | Observable | Main scientific role |
|---|---|---|
| OD600 | saturating optical density | fast biomass-sensitive process signal |
| fluorescence | reporter fluorescence | expression-sensitive signal coupled to biomass |
| Raman | five overlapping spectral bands | joint sensitivity to substrate, product and biomass |
| oxygen optode | dissolved oxygen | oxygen-transfer and demand state |

No single instrument identifies the complete culture state. OD compresses at high biomass,
fluorescence mixes biomass with expression, and Raman bands overlap. Combining signals over time
is therefore materially more informative than repeatedly reading one channel.

## Executable study

`examples/optimize_bioprocess.py` grows one culture for two hours, branches from that common state
and compares early, delayed, pulsed and dark optical induction schedules. Every branch has the same
nominal production duration. The comparison uses OD, fluorescence, dissolved oxygen and a
product-sensitive Raman contrast rather than hidden product concentration.

The bundled coefficients are generic. A strain- or reactor-specific package can replace the
kinetics and optical response while retaining the same persistent experiment interface.
