# Ranah Observatory web

This directory is the replacement public-delivery layer for Ranah Observatory.
The existing `site/` remains untouched until this SvelteKit application and its
public-data contracts are validated and deployment is switched deliberately.

## Product constraints

- static-first SvelteKit output; no server runtime required for the baseline product;
- first-class Indonesian (`/id`) and English (`/en`) routes;
- dataset-centric Data Catalog;
- disaster is the first Explore vertical;
- public pages never read raw/research analysis files directly;
- every public finding must link back to an inspectable dataset/source;
- MapLibre is reserved for the public GeoJSON/PMTiles layer and should be lazy-loaded;
- large tabular artifacts should move toward Parquet/partial reads instead of giant JSON payloads.

## Development

```bash
cd web
npm install
npm run check
npm run dev
```

Production build:

```bash
npm run build
```

The build output is written to `web/build/` and is suitable for static hosting.

## Migration rule

Do not delete or overwrite `site/` until the new application has equivalent
traceability, mobile behavior, and a validated deployment path.
