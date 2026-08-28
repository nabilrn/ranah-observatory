# Sumbar construction post-update OPAC detail transport boundary

## Result

The official BPS OPAC record for `Profil Perusahaan Konstruksi di Luar Pulau Jawa 2005` remains identified as `111.0614.1380`, but both verified record routes are now confirmed to be authentication-gated:

- `https://perpustakaan.bps.go.id/opac/details/111.0614.1380`
- `https://perpustakaan.bps.go.id/opac/read/111.0614.1380.pdf`

A bounded live probe requested only the verified detail locator. It resolved with HTTP 200 to `https://sso-pst.bps.go.id/login` and returned HTML rather than record metadata. The target title and record ID were absent from the returned body, and no additional public download/API locator was exposed before the SSO boundary.

Classification:

`verified_opac_detail_locator_sso_gated_before_record_metadata`

## Interpretation

This closes a specific transport hypothesis: the public detail page cannot currently be used to recover an alternate public file token or API locator without entering the BPS SSO flow.

It does **not** show that the Book II artifact is absent. The OPAC exact-title result and verified record identity remain valid. The SSO boundary is an access constraint only.

## Gate

No post-update Sumatera Barat qualification values or table definitions have been recovered, so the pre/post comparison remains unauthorized. In particular, this checkpoint does not authorize frame-change quantification, a historical bridge/backcast, attribution of the 2001-2003 construction-value revision to the 2005 directory update, or Panel v3 integration.

## Next bounded search

Further work should move away from OPAC route probing and search only official BPS text/index surfaces that may expose content from publication `05230.0610`, including BPS Deep Search/web-api surfaces or an official BPS-authored companion that reproduces the relevant post-update qualification table with sufficient semantic context.
