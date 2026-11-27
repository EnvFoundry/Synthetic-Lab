"""Scientific scope of the solid-tumor CAR-T spheroid laboratory."""

from synthetic_lab.research import ResearchContract


def contract():
    return ResearchContract(
        domains=(
            "solid-tumor cellular immunotherapy",
            "CAR-T receptor kinetics",
            "three-dimensional tumor spheroids",
        ),
        phenomena=(
            "CAR-T chemotaxis and spatial infiltration",
            "antigen-dependent attachment and cytotoxicity",
            "contact- and hypoxia-driven T-cell exhaustion",
            "functional recovery between tumor-cell engagements",
            "pre-existing antigen heterogeneity",
            "contact-induced antigen loss and immune escape",
        ),
        questions=(
            "How does receptor dwell time trade per-contact killing against infiltration and functional preservation?",
            "When does a high-affinity slow-off design trap CAR-T cells near the tumor rim and accelerate exhaustion?",
            "How strongly do antigen-negative subclones and contact-induced antigen loss limit durable tumor control?",
            "Which endpoint measurements separate poor infiltration, exhaustion and antigen escape?",
        ),
        observables={
            "antigen_low_viable_cells": {
                "unit": "count",
                "description": "Absolute surviving tumor count at or below the CAR recognition threshold.",
            },
            "infusion_radius": {
                "unit": "um",
                "description": "Tumor radial extent at infusion; fixed reference for infiltration endpoints.",
            },
            "tumor_viable_cells": {
                "unit": "count",
                "description": "Absolute number of viable tumor cells at the endpoint; matched branches can normalize this to the untreated burden.",
            },
            "tumor_viable_fraction": {
                "unit": None,
                "description": "Fraction of final tumor cells not in a PhysiCell death program; this is not a substitute for residual burden when dead cells have been removed.",
            },
            "antigen_low_viable_fraction": {
                "unit": None,
                "description": "Fraction of viable tumor cells at or below the CAR recognition threshold.",
            },
            "mean_viable_antigen": {
                "unit": None,
                "description": "Mean CAR-target antigen level among viable tumor cells.",
            },
            "infiltrating_fraction": {
                "unit": None,
                "description": "Fraction of remaining CAR-T cells inside the tumor radius measured at infusion.",
            },
            "mean_infiltration_depth": {
                "unit": "um",
                "description": "Mean depth of infiltrating CAR-T cells from the fixed infusion-time boundary.",
            },
            "exhausted_fraction": {
                "unit": None,
                "description": "Fraction of CAR-T cells whose exhaustion state exceeds 0.7.",
            },
            "mean_exhaustion": {
                "unit": None,
                "description": "Mean continuous CAR-T exhaustion state on [0, 1].",
            },
            "total_contacts": {
                "unit": "count",
                "description": "Cumulative successful CAR-T/tumor attachment events.",
            },
            "total_kills": {
                "unit": "count",
                "description": "Cumulative tumor apoptosis events triggered by CAR-T cells.",
            },
            "cell_map": {
                "unit": None,
                "description": "Cell-resolved type, position, oxygen, antigen, exhaustion, engagement and event counts.",
            },
        },
        latent_variables={
            "tumor_antigen_draw": {
                "unit": None,
                "description": "Seeded cell-level antigen distribution shared by all branches from one untreated spheroid.",
            },
            "car_t_functional_state": {
                "unit": None,
                "description": "Continuous exhaustion state accumulated during engagement and hypoxia and recovered while disengaged.",
            },
            "oxygen_field": {
                "unit": "mmHg",
                "description": "BioFVM oxygen field coupled to tumor and immune-cell physiology.",
            },
        },
        interventions=("infuse",),
        invariants=(
            "Forks made before infusion retain the same hidden patient-response draw and PhysiCell seed.",
            "A session represents one spheroid co-culture well and accepts at most one CAR-T infusion protocol.",
            "Receptor dwell time changes detachment kinetics without directly changing the intrinsic kill-rate parameter.",
            "Antigen-negative tumor cells cannot be attached or killed through the modeled CAR interaction.",
            "The committed infusion protocol is replayed unchanged whenever the external solver is invoked.",
        ),
        validity_conditions=(
            "A three-dimensional avascular spheroid is adequate for the comparative question.",
            "The modeled antigen, binding, killing, exhaustion and recovery rates span the in-vitro system being studied.",
            "CAR-T delivery as a shell surrounding the spheroid is a suitable representation of the co-culture assay.",
        ),
        limitations=(
            "The package is not calibrated to a named tumor, patient, antigen or CAR construct.",
            "It omits vasculature, fibroblasts, macrophages, cytokine toxicity and systemic pharmacokinetics.",
            "Receptor kinetics are represented through attachment and detachment hazards rather than molecular binding states.",
            "Exhaustion is a reduced continuous state rather than a transcriptional or epigenetic network.",
            "Antigen loss is a contact-dependent phenomenological rate and does not model a named molecular pathway.",
            "The solver reconstructs the co-culture from the committed protocol rather than serializing internal PhysiCell state.",
        ),
        failure_conditions=(
            "The PhysiCell executable or generated configuration is unavailable.",
            "The external solver fails, times out or returns non-finite endpoint values.",
            "A conclusion depends on omitted immune, stromal, vascular or systemic compartments.",
        ),
        fidelity="hybrid",
        action_semantics={
            "infuse": {
                "kind": "intervention",
                "description": "Pre-grow one seeded spheroid, introduce a CAR-T shell and execute the complete co-culture.",
            },
            "read": {
                "kind": "measurement",
                "description": "Read a selected endpoint panel from the completed co-culture without rerunning the solver.",
            },
            "snapshot": {
                "kind": "measurement",
                "description": "Return the final cell-resolved tumor and CAR-T map for spatial analysis.",
            },
        },
        reference_methods=(
            "three-dimensional tumor-spheroid CAR-T co-culture",
            "live/dead fluorescence imaging",
            "spatial immune-infiltration imaging",
            "flow-cytometric antigen and exhaustion profiling",
            "time-lapse immune-cell tracking",
            "PhysiCell agent-based multicellular simulation",
            "BioFVM reaction-diffusion simulation",
        ),
        physical_counterpart=(
            "A three-dimensional tumor spheroid surrounded by engineered T cells and read by imaging and endpoint cytometry"
        ),
        metadata={
            "solver_backend": "PhysiCell 1.14.2 with BioFVM",
            "upstream_project": "MathCancer/PhysiCell",
            "upstream_tag": "1.14.2",
            "upstream_model": "cancer-immune-sample",
            "geometry": "three-dimensional avascular spheroid",
            "observation_model": "cell-resolved solver state summarized as tumor-control, escape, infiltration and exhaustion endpoints",
            "exhaustion_model": "contact- and hypoxia-driven accumulation with disengaged recovery",
            "antigen_model": "seeded heterogeneous expression with contact-induced downregulation",
        },
    )
