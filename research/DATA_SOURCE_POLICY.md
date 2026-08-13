# Data Source Policy

## Source priority
Use the most authoritative and machine-readable source available.

1. official API or structured download;
2. official statistical table/publication;
3. official geospatial service;
4. archival government publication;
5. peer-reviewed or documented research dataset;
6. reputable secondary source for context;
7. web scraping only when a required source has no practical structured interface.

## Initial source families
- BPS and BPS West Sumatra: census, surveys, regional statistics, GRDP, labor, population, agriculture, welfare, and publications.
- Satu Data Indonesia / West Sumatra open-data portals: regional administrative and sector datasets.
- BMKG: station climate observations, rainfall, temperature, climate extremes, and climate information.
- BNPB / InaRISK: disaster events, hazard, exposure, vulnerability, risk, and West Sumatra response datasets.
- BIG / Ina-Geoportal: administrative boundaries, RBI, DEMNAS and other geospatial reference layers.
- Bank Indonesia: regional economic and financial context.
- Ministry and agency datasets where they are the primary authority for a sector.
- Satellite and remote-sensing archives where they add independent spatial evidence.

## Ingestion rule
Prefer API, CSV, XLS/XLSX, JSON, GeoJSON, WFS, or documented bulk-download endpoints. Do not scrape a rendered page when equivalent structured data are available.

## Provenance
Each dataset must record: source organization, dataset/publication title, source URL or identifier, retrieval date, time coverage, geography, format, license/usage notes when known, and transformation script/version.

## Raw data
Raw artifacts are immutable. Corrections and harmonization happen in derived layers. When large source files should not live in Git, keep a manifest with checksums and a reproducible retrieval path.

## Quality grades
- `A`: official structured data with clear metadata;
- `B`: official publication or geospatial product requiring extraction;
- `C`: documented academic/archival reconstruction;
- `D`: secondary evidence used mainly for context;
- `E`: uncertain or exploratory source that must not support strong public claims alone.

## Historical evidence
Historical sources may use obsolete geography, spelling, units, classifications, or definitions. Preserve the original representation and document every harmonization step rather than rewriting the source to fit modern categories.
