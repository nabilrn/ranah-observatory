# Milestone 48 — BNPB annual portal republication lineage

## Question

Do the official BNPB annual 2010–2017 district/city dataset pages provide an independent crosscheck for the M42 Sumatera Barat historical impact workbooks?

## Finding

No. The annual BNPB portal pages are valuable official provenance and access surfaces, but the Sumatera Barat workbook exposed by each page is the **same Google Drive source object** already frozen in M42.

For every year 2010–2017:

- the portal describes the dataset as disaster occurrence and impact data by kabupaten/kota;
- the portal declares `https://dibi.bnpb.go.id` as its source;
- the annual resource links to a Google Drive folder;
- the Sumatera Barat workbook is `stat_by_wil_13_<year>.xlsx`;
- its Google Drive file ID matches the M42 `locator_id` exactly;
- its current raw byte size matches M42 exactly; and
- a fresh SHA256 of the raw workbook matches the M42 frozen SHA256 exactly.

Result: **8/8 locator matches, 8/8 byte-size matches, 8/8 SHA256 matches.**

## Validation independence

A second website entry is not a second observation source when it resolves to the same underlying file. Counting the annual portal pages as an independent validation source would overstate the evidence base.

The correct interpretation is:

> M42 is the frozen source-native archive snapshot; the annual BNPB portal family independently confirms official provenance/discoverability, not the underlying values.

## Evidence-independence contract

The following are now frozen:

- annual portal republication may be cited as official access provenance;
- annual portal republication may **not** be counted as an independent cross-source value check;
- no canonical historical victim/damage metric is promoted from this finding;
- M43 semantic and temporal-geography restrictions remain unchanged;
- M47 national disaster-type retrospective resources remain wrong-grain for district reconciliation;
- absent historical rows remain missing, never zero-filled;
- `Menderita` remains the historical source label and is not silently renamed `Terdampak`.

## Frozen lineage table

See `data/registries/bnpb_annual_portal_republication_lineage.csv` for the eight annual dataset IDs, official folder IDs, Sumatera Barat Drive file IDs, byte sizes, and SHA256 values.

## Next gate

M49 should search for a **genuinely independent** district/city or event-level impact source covering at least part of 2010–2017. Another URL, mirror, or portal page pointing to the same annual workbook object does not satisfy that requirement.
