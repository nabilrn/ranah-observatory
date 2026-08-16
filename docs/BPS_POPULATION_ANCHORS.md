# BPS Population Anchor Qualification

## Objective

This phase audits one bounded demography question:

> Which BPS census/SUPAS population anchors can be preserved safely, and are any new `population_total` or `population_growth` rows ready for canonical promotion?

The source family is BPS WebAPI variable `484`:

`[Hasil Sensus dan SUPAS] Jumlah Penduduk Menurut Jenis Kelamin dan Kabupaten/Kota di Sumatera Barat`

The BPS metadata distinguishes:

- census years: 1971, 1980, 1990, 2000, 2010, 2020;
- SUPAS years: 1995, 2005, 2015.

Only the total-sex category (`turvar=34`, `Laki-Laki + Perempuan`) is in scope.

This milestone does **not** create an annual population series and does **not** derive population growth.

## Evidence used

The audited source profile comes from successful GitHub Actions run `31894824526`, which harvested all nine requested anchors through the credentialed BPS WebAPI workflow.

Artifact:

`bps-census-supas-var-484`

Artifact digest:

`sha256:a0ca1710a649d42e78ef290860c7d48715e7deec2f2789f11d90257733ef7c68`

The audited normalized harvest contains 468 all-sex-category rows across male, female, and total-sex dimensions. The bounded demography audit uses only **156 total-sex rows**.

The historical qualification state is retained in:

- `data/manifests/bps_population_anchor_audit.json`;
- `data/registries/bps_population_anchor_qualification.csv`.

CI re-harvests the source family and validates the semantic profile rather than trusting the old artifact indefinitely.

## Anchor inventory

| Year | Source type | Total-sex rows | Decision |
|---|---|---:|---|
| 1971 | Census | 15 | source-era evidence; historical boundary lineage required |
| 1980 | Census | 15 | source-era evidence; historical boundary lineage required |
| 1990 | Census | 15 | source-era evidence; historical boundary lineage required |
| 1995 | SUPAS | 15 | **held: source key/metadata alignment anomaly** |
| 2000 | Census | 16 | source-era evidence; historical boundary lineage required |
| 2005 | SUPAS | 20 | full current code set present; boundary/reference-date qualification still required |
| 2010 | Census | 20 | full current code set present; boundary/reference-date qualification still required |
| 2015 | SUPAS | 20 | full current code set present; boundary/reference-date qualification still required |
| 2020 | Census | 20 | already canonical through the BPS expansion |

The row-count changes are research-relevant. They reflect changing source geography footprints and must not be hidden by padding absent historical jurisdictions with zero or by copying current geography IDs backward.

## 1995 source-integrity anomaly

The 1995 response cannot safely be interpreted using the current `vervar` metadata labels.

The audited total-sex key set is:

`1301, 1303, 1304, 1305, 1306, 1307, 1308, 1309, 1310, 1372, 1373, 1374, 1375, 1376, 1377`

Compared with the surrounding source-era profile:

- `1300` is absent;
- `1302` is absent;
- `1371` is absent;
- `1301`, `1310`, and `1377` appear instead.

The values exhibit a sequence consistent with a shifted source-key interpretation, but **positional inference is not accepted as provenance**. The pipeline therefore records:

`hold_key_label_alignment_anomaly`

and explicitly sets:

`automatic_positional_remap_allowed=false`.

If BPS later corrects the source profile, the live CI gate will fail and require a new review rather than silently retaining the old anomaly assumption.

## Boundary semantics

### 1971–1990

The source exposes 15 total-sex rows: province plus 14 source-era local units. They are not treated as the current 19 kabupaten/kota.

The existing historical reconstruction already demonstrates the correct principle for 1971: attach historical evidence to source-era geography unless boundary lineage has been reconstructed explicitly.

### 2000

The source exposes 16 total-sex rows. Kepulauan Mentawai appears, while later-created current jurisdictions are absent. The local rows therefore remain source-era evidence rather than current-boundary observations.

### 2005–2015

The source exposes all 20 province + current local codes. This is useful but is not, by itself, sufficient proof that every source value is definitionally equivalent to the current canonical boundary frame.

This phase therefore records the code-set completeness while withholding canonical promotion until boundary continuity and reference-date semantics are qualified deliberately.

### 2020

SP2020 is already handled by the structural-economic BPS expansion:

- 20 canonical observations;
- total-sex category only;
- `claim_type=observed`;
- September 2020 reference bounds;
- current geography mapping already qualified.

The live anchor validator cross-checks all 20 re-harvested 2020 values against those existing canonical observations. This phase does not create duplicates.

## Why `population_growth` remains blocked

The canonical `population_growth` indicator must be derived only from definitionally compatible population observations.

This phase does not yet have a reviewed pair of anchors for which all of the following are simultaneously established:

1. source integrity is clean;
2. geography/boundary semantics are compatible;
3. exact reference dates or a defensible interval convention are qualified;
4. census versus SUPAS methodology is retained rather than hidden;
5. the denominator/source universe is compatible.

Accordingly:

- new `population_total` rows promoted by this phase: **0**;
- `population_growth` rows derived by this phase: **0**;
- growth status: `blocked_pending_compatible_anchor_pairs`.

This is a positive research result: it prevents a visually smooth but methodologically false long-run demographic series.

## CI contract

`.github/workflows/bps-population-anchor-audit.yml` performs two levels of validation.

### Offline

- validate the nine-row qualification registry;
- require 1995 to remain held;
- require 2020 to remain linked to the existing canonical SP2020 series;
- require population growth to remain blocked.

### Credentialed live BPS check

Using the repository `BPS_API_KEY`, CI re-harvests all nine var-484 periods and requires:

- exactly 156 total-sex rows;
- the expected code footprint for each period;
- positive numeric population values in `Jiwa`;
- the audited 1995 anomalous code profile to remain explicit;
- all 20 live SP2020 values to match the existing canonical BPS expansion exactly;
- zero new canonical promotion from this audit.

A source-profile change is therefore a review event, not an automatic rewrite.

## Deliberately not included

This phase does not:

- repair the 1995 anomaly by guessed code shifting;
- interpolate missing historical jurisdictions;
- map historical local rows to June-2026/current boundaries;
- concatenate census and SUPAS anchors as a homogeneous annual panel;
- infer exact historical reference dates from general knowledge;
- derive population growth;
- touch urban population share or migration.

## Next bounded demography task

Once this audit is merged, the next micro-milestone is to decide whether a **single compatible population-growth pair** can be qualified. The first candidate should be selected conservatively from the clean anchor family, with boundary and reference-period evidence reviewed before any growth formula is applied.
