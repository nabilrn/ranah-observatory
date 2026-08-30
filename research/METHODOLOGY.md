# Methodology

Ranah Observatory uses a staged research workflow. Methods are selected according to the question and evidence available; no model is allowed to upgrade weak evidence into a stronger claim merely because it is statistically sophisticated.

## 1. Evidence ladder

Analyses should progress only as far as the data and design justify:

```text
observed / reconstructed evidence
            |
            v
      descriptive analysis
            |
            v
   association / correlation
            |
            v
      predictive modeling
            |
            v
quasi-causal / causal design
            |
            v
 robustness and replication
            |
            v
       policy scenario
```

A result may stop at any level. Descriptive findings are valid research results; overstating evidence is a failure.

## 2. Source audit and data qualification

Before analysis, each dataset is checked for:

- provenance and retrieval path;
- geography and boundary version;
- time coverage and frequency;
- unit and price basis where relevant;
- population or sampling universe;
- methodology and classification changes;
- missingness and suppression;
- revisions or breaks in series;
- licensing or usage constraints when known.

Observed, derived, reconstructed, model-estimated, qualitative, and scenario values must remain distinguishable.

## 3. Historical reconstruction

Historical series may require extraction from publications, archival sources, obsolete classifications, or changing administrative boundaries.

Rules:

- preserve the source-era observation before harmonization;
- document all unit, category, and geography mappings;
- never silently interpolate missing values;
- label reconstructed values explicitly;
- retain uncertainty or confidence metadata when reconstruction is material;
- do not force incomparable series into a continuous chart.

Administrative boundaries are versioned. A historical observation must use its source-era geography, an explicit crosswalk, or a separate historical-region identifier.

## 4. Descriptive analysis

Descriptive work establishes what changed before attempting to explain why.

Typical methods include:

- levels, rates, shares, distributions, and growth;
- real versus nominal comparisons;
- per-capita or population-standardized measures;
- index construction where definitions are transparent;
- structural-break and change-point exploration;
- spatial and temporal visualization;
- comparison with Indonesian distributions and pre-defined peers.

Descriptive results must not be presented as causal effects.

## 5. Peer selection and comparative analysis

Claims of underperformance require an explicit comparison set.

Peer selection may use:

- transparent rule-based matching;
- baseline characteristics fixed before the outcome period;
- distance or similarity metrics;
- PCA or clustering as exploratory tools;
- synthetic-control style weighting where a specific design justifies it.

Peer definitions, variables, time windows, and sensitivity to alternative peers must be documented. Outcome variables or post-treatment variables must not be used to manufacture convenient peers.

## 6. Predictive and expected-performance models

Predictive models estimate expected outcomes conditional on observed inputs. They do not establish causes or a literal maximum attainable future.

Permitted baseline approaches may include:

- linear or regularized regression;
- generalized additive or other interpretable models;
- tree-based models such as gradient boosting;
- quantile regression;
- frontier or efficiency methods when assumptions are explicit.

Requirements:

- compare against a simple baseline;
- separate training, validation, and testing in a way appropriate to panel/time data;
- prevent geographic and temporal leakage;
- document features and transformations;
- report uncertainty or error where feasible;
- test sensitivity to alternative specifications;
- distinguish expected performance from frontier or efficiency estimates.

Feature importance, SHAP values, or predictive gain are evidence of model behavior and association, not proof of causation.

## 7. Causal and quasi-causal analysis

Causal language is allowed only when the study has a design capable of supporting it.

Candidate approaches include:

- difference-in-differences and event studies;
- synthetic control;
- fixed-effects panel designs;
- regression discontinuity when assignment rules justify it;
- instrumental variables when a defensible instrument exists;
- double/debiased machine learning;
- causal forests for heterogeneous effects after identification assumptions are established.

Every causal study must state:

- treatment or exposure;
- outcome;
- comparison group or counterfactual;
- identification assumptions;
- pre-treatment period and covariates;
- plausible confounders;
- robustness and falsification checks;
- what would invalidate the interpretation.

A causal method name is not itself evidence that identification is credible.

## 8. Spatial and environmental analysis

Geospatial analysis must account for scale, boundary definitions, spatial dependence, and exposure.

Hazard, exposure, vulnerability, observed impact, and economic loss are separate concepts. Climate or disaster analyses must not attribute observed losses to a single driver without an appropriate design.

Raster, station, administrative, watershed, and network data should retain their native spatial reference and aggregation method before derived regional summaries are produced.

## 9. Scenario and policy analysis

Policy scenarios are conditional exercises, not forecasts or prescriptions.

Each scenario must expose:

- intervention definition;
- assumed mechanism;
- evidence supporting the mechanism;
- cost or resource assumptions where available;
- implementation horizon;
- uncertainty and major dependencies;
- resilience, distributional, and environmental considerations where relevant.

Recommendations should not be generated solely from correlation, feature importance, or one model run.

A policy recommendation should normally require either credible causal/quasi-causal evidence, replicated findings from relevant literature, or a clearly labeled scenario supported by multiple independent evidence streams.

## 10. Robustness and uncertainty

Where relevant, analyses should test sensitivity to:

- alternative comparison groups;
- different time windows;
- alternative indicator definitions;
- boundary harmonization choices;
- missing-data treatment;
- model specifications;
- influential observations;
- spatial or temporal dependence.

Uncertainty must remain visible in public outputs. Point estimates should not be presented with false precision.

## 11. Reproducibility minimum

Every material analysis should be reproducible from a documented data snapshot and code revision. At minimum retain:

- source and data snapshot/version;
- transformation code version;
- analysis or model code revision;
- parameters and configuration;
- random seed where stochastic methods are used;
- generated-at timestamp;
- model artifact or sufficient information to recreate it;
- provenance linking published claims back to their inputs.

## 12. Claim discipline

Public outputs must identify material claims as one of:

- observed data;
- derived statistic;
- reconstructed historical estimate;
- predictive/model estimate;
- causal estimate;
- qualitative evidence;
- scenario assumption.

When evidence is mixed or incomplete, the weaker justified claim takes precedence over the stronger narrative.

See `THREATS_TO_VALIDITY.md` for the project's standing validity risks and `REPRODUCIBILITY.md` for the minimum reproducibility contract.