# BMKG Open Data Operational Feeds

## Question

What does the official `data.bmkg.go.id` portal add to Ranah Observatory, and which research claims can these feeds support?

## Qualification decision

BMKG Data Terbuka provides credential-free machine-readable operational feeds that are useful for live and prospective context. They do **not** replace historical observed station climate data.

Qualified roles:

- weather forecast → `prospective_forecast_only`;
- weather nowcast/CAP → `active_nowcast_alert_feed`;
- earthquake open data → `latest_event_feed_not_historical_archive`.

These roles must remain separate from the longitudinal observed-climate panel.

## Weather forecast API

Official documentation:

`https://data.bmkg.go.id/prakiraan-cuaca/`

Endpoint shape:

`https://api.bmkg.go.id/publik/prakiraan-cuaca?adm4={kode_wilayah_tingkat_iv}`

BMKG documents the product as:

- JSON;
- forecasts for all villages/kelurahan in Indonesia;
- three-day forecast horizon;
- eight forecast records per day at three-hour intervals;
- updated twice daily;
- location addressed with level-IV administrative (`adm4`) codes;
- maximum 60 requests per minute per IP.

Useful fields include forecast UTC/local datetime, temperature, humidity, weather description, wind speed/direction, total cloud cover, visibility, and `analysis_date`.

### Research role

The forecast is prospective model output. It can support a future operational web layer, for example current weather-risk context around a kabupaten/kota or an active disaster, but it must never be re-labelled as:

- `annual_rainfall`;
- `extreme_rainfall_days`;
- `mean_temperature`;
- or another historical observed climate indicator.

The probe uses `adm4=13.71.01.1001` only as a stable request example for API-shape verification. The forecast probe does not establish a canonical geography crosswalk.

## Weather nowcast / Common Alerting Protocol

Official documentation:

`https://data.bmkg.go.id/peringatan-dini-cuaca/`

National active-feed endpoint:

`https://www.bmkg.go.id/alerts/nowcast/id`

Detail endpoint shape:

`https://www.bmkg.go.id/alerts/nowcast/id/{kode_detail_cap}_alert.xml`

BMKG documents the product as:

- XML;
- Common Alerting Protocol (CAP);
- active weather warnings across Indonesia down to district/kecamatan level;
- RSS for the active province-level list;
- CAP XML for detailed affected areas;
- updated continuously;
- maximum 60 requests per minute per IP.

CAP carries event, effective time, expiry time, narrative description, and affected-area polygons.

### Research role

This is a high-value operational hazard feed. It can eventually power a live hazard layer and provide explicit spatial/temporal context around severe weather.

However, the active feed is not by itself a historical event archive. Historical analysis would require Ranah Observatory to snapshot immutable CAP documents over time and define rules for:

- alert updates and replacements;
- cancellations;
- duplicate/repeated warnings;
- alert identifiers;
- effective and expiry windows;
- spatial overlap;
- conversion from warning episodes to any derived event metric.

No CAP warning count should be treated as a BNPB disaster-event count. A warning is a meteorological hazard communication object, while BNPB records disaster events and impacts under a different administrative process.

## Earthquake open data

Official documentation:

`https://data.bmkg.go.id/gempabumi/`

Example JSON endpoint:

`https://data.bmkg.go.id/DataMKG/TEWS/autogempa.json`

The open page exposes machine-readable latest/recent earthquake products, including the latest earthquake and rolling lists for M5.0+ and felt earthquakes, with event fields such as datetime, magnitude, depth, coordinates, nearest region, tsunami potential, felt information, and shakemap references.

### Research role

The feed is useful for operational context and recent-event display. It is not classified as a complete historical earthquake archive because the public contract exposes latest and rolling recent lists rather than a full longitudinal event catalogue.

Any future historical seismic study must use a source explicitly carrying the complete intended time range and stable event semantics.

## Relation to existing BMKG sources

### Satu Peta MKG rainfall WMS

The previously reviewed rainfall/rainy-day WMS is accessible but exposes no ArcGIS `timeInfo` and no WMS `TIME` dimension. It remains map/context evidence rather than a reproducible historical rainfall panel.

See `docs/BMKG_HAZARD_ACQUISITION.md`.

### BMKG Data Online

BMKG Data Online remains the preferred BMKG observed-station lane for daily climate observations such as rainfall (`RR`) when acquisition is reproducible. Its authenticated workflow is intentionally treated separately from the open operational feeds.

Open forecast and nowcast data do not solve the historical station-observation requirement.

## Probe and reproducibility

Repository probe:

`scripts/probe_bmkg_open_data.py`

Offline semantic tests:

`tests/test_bmkg_open_data_probe.py`

Hosted-runner workflow:

`.github/workflows/bmkg-open-data-probe.yml`

The probe records transport metadata and SHA-256 hashes while intentionally avoiding raw feed bodies in the durable manifest. The GitHub Actions run tests endpoint accessibility and response shape against the official services.

A live probe can succeed even when Sumatera Barat has no active CAP alert. The national RSS feed is the hard operational check; Sumatera Barat CAP detail is inspected only when an active matching item exists.

## Canonical guardrail

The BMKG open operational feeds may enter an operational/context layer, but none is promoted into the canonical longitudinal climate indicators by this qualification.

In particular:

- forecast values remain forecast values;
- CAP alerts remain warnings;
- recent earthquake feeds remain recent-event products;
- BNPB disaster events remain separate administrative event observations;
- BMKG observed-station climate remains a separate evidence class.

BMKG requires attribution when its open data are displayed in an application or system. Any future Ranah Observatory interface using these feeds must visibly identify BMKG as the source.

## Next historical climate lane

The remaining climate gap is the long historical rainfall/temperature baseline. The next research deliverable should evaluate dated gridded/reanalysis climate products as explicitly labelled model/reanalysis evidence and use BMKG station observations for validation where obtainable. Availability of an alternative gridded source must not change its claim type into `observed`.
