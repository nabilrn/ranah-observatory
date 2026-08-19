# Milestone 26 — InaRISK Version & Component Binding Audit Specification

## Purpose

M26 follows the exact unresolved boundary left by M16. M16 verified official BNPB/InaRISK GIS service surfaces for flood/landslide hazard and vulnerability, but did **not** ingest raster pixels because the endpoint metadata available at that stage did not bind the data vintage and methodology tightly enough.

M26 asks a narrower question:

> Can the already verified official InaRISK service endpoints be bound to an explicit data vintage and methodology/version using their own ArcGIS REST metadata and item metadata, without inferring a dataset year from service-modification timestamps?

M26 is an evidence-qualification milestone, not a risk model.

## Locked upstream boundary

Required inputs:

- M16 spatial/climate risk manifest must be complete;
- M16 risk synthesis must remain unauthorized;
- M16 unresolved InaRISK component evidence must be preserved;
- no M16 raster values may be treated as ingested observations merely because M26 can access endpoint metadata.

## Source discovery

M26 extracts official BNPB/InaRISK ArcGIS REST service URLs from the committed M16 evidence registry and M16 documentation/manifests. It does not substitute a different GIS service after seeing metadata quality.

Only official BNPB/InaRISK service URLs already represented in M16 are eligible for this audit.

## Metadata crawl

For each discovered service M26 attempts, where supported:

1. service root `?f=pjson`;
2. service layer collection `/layers?f=pjson`;
3. every enumerated layer `/<layer_id>?f=pjson`;
4. `/info/iteminfo?f=pjson`;
5. `/info/metadata` as raw metadata when available.

Every successful payload is frozen with:

- source URL;
- HTTP status;
- content type;
- SHA-256;
- retrieval timestamp;
- response body.

Failed optional metadata surfaces are recorded rather than silently ignored.

## Vintage-binding rules

M26 distinguishes:

- `explicit_dataset_vintage_bound` — metadata contains an explicit dataset/reference vintage tied to the layer/service data itself;
- `time_enabled_not_dataset_vintage` — ArcGIS time metadata exists but does not establish the source raster vintage contract required by M16;
- `year_tokens_present_binding_unresolved` — years appear in text but cannot be shown to represent the dataset vintage;
- `no_explicit_vintage_metadata` — no usable vintage field/text is found.

The following are **not** sufficient on their own:

- service `modified` timestamps;
- HTTP `Last-Modified`;
- copyright year;
- portal publication/update date;
- a year appearing in an unrelated description.

## Methodology-binding rules

M26 distinguishes:

- `explicit_methodology_version_bound` — metadata identifies a methodology/version or exact methodology document applicable to the dataset;
- `methodology_reference_present_binding_unresolved` — methodology language/reference exists but cannot be tied unambiguously to the layer vintage;
- `no_explicit_methodology_binding`.

A generic link to the InaRISK methodology page does not automatically bind a service to a specific methodological vintage.

## Component authorization gate

An InaRISK component may become `metadata_binding_qualified_for_future_ingestion` only when both:

1. dataset vintage is explicitly bound; and
2. methodology/version applicability is explicitly bound.

Otherwise the component remains `endpoint_verified_version_binding_unresolved` or a more specific held status.

Even a metadata-qualified component is **not ingested in M26**. Pixel ingestion must be a later separate milestone with spatial alignment, nodata, aggregation, and reproducibility rules preregistered before values are inspected.

## Risk-chain boundary

M26 does not fabricate missing components. In particular:

- hazard metadata qualification does not create exposure;
- vulnerability metadata qualification does not create capacity;
- event counts do not become observed impact;
- an official composite risk index is not decomposed into missing components unless its component contract is explicitly available.

M16 risk synthesis remains blocked unless a later milestone completes the required hazard/exposure/vulnerability/capacity/impact evidence chain.

## Required outputs

1. `data/analysis/engine/inarisk_binding_v1/m26-service-discovery.csv`
2. `data/analysis/engine/inarisk_binding_v1/m26-metadata-endpoints.csv`
3. `data/analysis/engine/inarisk_binding_v1/m26-binding-assessment.csv`
4. `data/processed/bnpb/inarisk_metadata/` frozen metadata payloads
5. `data/manifests/milestone26_inarisk_version_binding.json`

## Completion gate

M26 completes when:

- every official InaRISK ArcGIS service represented in the M16 unresolved endpoint set is audited;
- successful and failed metadata surfaces are both recorded;
- vintage and methodology binding are classified independently;
- no service/update timestamp is misrepresented as a dataset vintage;
- no raster pixel is ingested;
- no composite risk score/ranking is created;
- no missing exposure/capacity/impact component is synthesized;
- focused tests pass;
- permanent CI can verify frozen metadata checksums and rebuild the assessment offline.

M26 may complete with **zero newly qualified components**. That is a legitimate negative metadata result.

## Forbidden interpretations

M26 does not authorize statements such as:

- “the ArcGIS service was updated in 2024, therefore the raster is a 2024 dataset”;
- “the official endpoint means its methodology vintage is known”;
- “hazard + vulnerability is a complete disaster-risk score”;
- “InaRISK pixels have been analyzed”;
- “a metadata-qualified component proves causal disaster impact.”
