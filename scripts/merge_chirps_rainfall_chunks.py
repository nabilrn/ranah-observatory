from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

OBSERVATIONS = "chirps-v3-annual-rainfall-current-boundaries.csv"
DIAGNOSTICS = "chirps-v3-annual-zonal-diagnostics.csv"
SOURCE_ARTIFACTS = "chirps-v3-annual-source-artifacts.csv"
PROVENANCE = "chirps-v3-rainfall-provenance.csv"
MANIFEST = "chirps-v3-rainfall-panel.manifest.json"
GEOMETRY = "big_sumbar_boundaries_june_2026.source.geojson"

OBSERVATION_FIELDS = [
    "observation_id",
    "indicator_id",
    "geography_id",
    "time_start",
    "time_end",
    "frequency",
    "value_numeric",
    "unit",
    "claim_type",
    "provenance_id",
    "suppressed",
    "comparable",
    "methodology_version",
    "price_basis",
    "notes",
]
DIAGNOSTIC_FIELDS = [
    "geography_id",
    "canonical_name",
    "source_permendagri_code",
    "year",
    "annual_rainfall_mm",
    "valid_area_fraction",
    "valid_weight_area_m2",
    "polygon_weight_area_m2",
    "valid_pixel_intersections",
    "total_pixel_intersections",
    "source_url",
    "source_sha256",
    "source_bytes",
]
SOURCE_FIELDS = ["year", "source_url", "retrieved_at", "bytes", "sha256"]
PROVENANCE_FIELDS = [
    "provenance_id",
    "source_id",
    "artifact_locator",
    "retrieved_at",
    "source_release",
    "checksum_sha256",
    "parser_revision",
    "transform_revision",
    "extraction_method",
    "notes",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [
            {key: (value or "").strip() for key, value in row.items()}
            for row in csv.DictReader(handle)
        ]


def write_csv(path: Path, fieldnames: list[str], rows: Iterable[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def deterministic_id(prefix: str, *parts: str) -> str:
    payload = "|".join(parts).encode("utf-8")
    return f"{prefix}_{hashlib.sha256(payload).hexdigest()[:24]}"


def discover_chunks(root: Path) -> list[Path]:
    manifests = sorted(root.rglob(MANIFEST))
    if not manifests:
        raise ValueError(f"no CHIRPS chunk manifests found under {root}")
    return [path.parent for path in manifests]


def load_chunk(chunk_dir: Path) -> dict[str, Any]:
    required = [OBSERVATIONS, DIAGNOSTICS, SOURCE_ARTIFACTS, PROVENANCE, MANIFEST, GEOMETRY]
    missing = [name for name in required if not (chunk_dir / name).is_file()]
    if missing:
        raise ValueError(f"chunk {chunk_dir} missing files: {missing}")
    manifest = json.loads((chunk_dir / MANIFEST).read_text(encoding="utf-8"))
    years = manifest.get("years", {})
    return {
        "dir": chunk_dir,
        "manifest": manifest,
        "start": int(years["start"]),
        "end": int(years["end"]),
        "observations": read_csv(chunk_dir / OBSERVATIONS),
        "diagnostics": read_csv(chunk_dir / DIAGNOSTICS),
        "sources": read_csv(chunk_dir / SOURCE_ARTIFACTS),
        "provenance": read_csv(chunk_dir / PROVENANCE),
        "geometry_sha256": sha256_file(chunk_dir / GEOMETRY),
    }


def assert_same(label: str, values: list[Any]) -> Any:
    if not values:
        raise ValueError(f"no values supplied for {label}")
    first = values[0]
    if any(value != first for value in values[1:]):
        raise ValueError(f"chunk contract mismatch for {label}: {values}")
    return first


def merge_chunks(chunks_root: Path, output_dir: Path, start_year: int, end_year: int) -> dict[str, Any]:
    chunks = [load_chunk(path) for path in discover_chunks(chunks_root)]
    chunks.sort(key=lambda item: (item["start"], item["end"]))

    expected_years = set(range(start_year, end_year + 1))
    covered_years: list[int] = []
    for chunk in chunks:
        if chunk["start"] > chunk["end"]:
            raise ValueError(f"invalid chunk range {chunk['start']}-{chunk['end']}")
        covered_years.extend(range(chunk["start"], chunk["end"] + 1))
    if len(covered_years) != len(set(covered_years)):
        raise ValueError("chunk year ranges overlap")
    if set(covered_years) != expected_years:
        missing = sorted(expected_years - set(covered_years))
        unexpected = sorted(set(covered_years) - expected_years)
        raise ValueError(f"chunk year coverage mismatch; missing={missing} unexpected={unexpected}")

    geometry_sha = assert_same(
        "BIG raw GeoJSON SHA-256",
        [chunk["geometry_sha256"] for chunk in chunks],
    )
    indicator = assert_same(
        "indicator_id",
        [chunk["manifest"].get("indicator_id") for chunk in chunks],
    )
    claim_type = assert_same(
        "claim_type",
        [chunk["manifest"].get("claim_type") for chunk in chunks],
    )
    unit = assert_same("unit", [chunk["manifest"].get("unit") for chunk in chunks])
    geography_contract = assert_same(
        "geography contract",
        [
            {
                key: value
                for key, value in chunk["manifest"].get("geography", {}).items()
                if key != "raw_geojson_sha256"
            }
            for chunk in chunks
        ],
    )
    if any(
        chunk["manifest"].get("geography", {}).get("raw_geojson_sha256") != geometry_sha
        for chunk in chunks
    ):
        raise ValueError("chunk manifest geometry checksum does not match chunk geometry file")
    chirps_contract = assert_same(
        "CHIRPS static contract",
        [
            {
                key: value
                for key, value in chunk["manifest"].get("chirps", {}).items()
                if key != "annual_raster_count"
            }
            for chunk in chunks
        ],
    )
    method = assert_same(
        "method contract",
        [chunk["manifest"].get("method") for chunk in chunks],
    )
    equivalence = assert_same(
        "cross-granularity validation contract",
        [chunk["manifest"].get("cross_granularity_validation") for chunk in chunks],
    )
    negative_guards = assert_same(
        "negative semantic guards",
        [chunk["manifest"].get("negative_guards") for chunk in chunks],
    )

    observations: list[dict[str, str]] = []
    diagnostics: list[dict[str, str]] = []
    sources: list[dict[str, str]] = []
    for chunk in chunks:
        observations.extend(chunk["observations"])
        diagnostics.extend(chunk["diagnostics"])
        sources.extend(chunk["sources"])

    source_years = [int(row["year"]) for row in sources]
    if len(source_years) != len(set(source_years)) or set(source_years) != expected_years:
        raise ValueError("merged source-artifact years are not unique and complete")
    sources.sort(key=lambda row: int(row["year"]))

    observation_keys = [(row["geography_id"], int(row["time_start"][:4])) for row in observations]
    diagnostic_keys = [(row["geography_id"], int(row["year"])) for row in diagnostics]
    expected_row_count = 19 * len(expected_years)
    if len(observations) != expected_row_count or len(set(observation_keys)) != expected_row_count:
        raise ValueError(
            f"merged observations must contain {expected_row_count} unique geography-year rows"
        )
    if len(diagnostics) != expected_row_count or len(set(diagnostic_keys)) != expected_row_count:
        raise ValueError(
            f"merged diagnostics must contain {expected_row_count} unique geography-year rows"
        )

    source_release = assert_same(
        "provenance source release",
        [row["source_release"] for chunk in chunks for row in chunk["provenance"]],
    )
    source_id = assert_same(
        "provenance source id",
        [row["source_id"] for chunk in chunks for row in chunk["provenance"]],
    )
    artifact_locator = assert_same(
        "provenance artifact locator",
        [row["artifact_locator"] for chunk in chunks for row in chunk["provenance"]],
    )
    parser_revision = assert_same(
        "provenance parser revision",
        [row["parser_revision"] for chunk in chunks for row in chunk["provenance"]],
    )
    transform_revision = assert_same(
        "provenance transform revision",
        [row["transform_revision"] for chunk in chunks for row in chunk["provenance"]],
    )
    extraction_method = assert_same(
        "provenance extraction method",
        [row["extraction_method"] for chunk in chunks for row in chunk["provenance"]],
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    geometry_path = output_dir / GEOMETRY
    shutil.copyfile(chunks[0]["dir"] / GEOMETRY, geometry_path)
    observations_path = output_dir / OBSERVATIONS
    diagnostics_path = output_dir / DIAGNOSTICS
    sources_path = output_dir / SOURCE_ARTIFACTS
    provenance_path = output_dir / PROVENANCE
    manifest_path = output_dir / MANIFEST

    provenance_id = deterministic_id(
        "chirpsprov",
        source_release,
        f"{start_year}-{end_year}",
        str(geography_contract.get("source_edition", "")),
        transform_revision,
    )
    for row in observations:
        row["provenance_id"] = provenance_id
    observations.sort(key=lambda row: (row["geography_id"], int(row["time_start"][:4])))
    diagnostics.sort(key=lambda row: (row["geography_id"], int(row["year"])))

    write_csv(observations_path, OBSERVATION_FIELDS, observations)
    write_csv(diagnostics_path, DIAGNOSTIC_FIELDS, diagnostics)
    write_csv(sources_path, SOURCE_FIELDS, sources)

    generated_at = datetime.now(timezone.utc).isoformat()
    provenance_row = {
        "provenance_id": provenance_id,
        "source_id": source_id,
        "artifact_locator": artifact_locator,
        "retrieved_at": generated_at,
        "source_release": source_release,
        "checksum_sha256": sha256_file(sources_path),
        "parser_revision": parser_revision,
        "transform_revision": transform_revision,
        "extraction_method": extraction_method,
        "notes": (
            f"Merged {len(chunks)} independently validated sequential annual-download chunks covering "
            f"{start_year}-{end_year}; all chunks used identical BIG geometry SHA-256 {geometry_sha}, "
            "CHIRPS grid/method contracts, and semantic guards. Source-level TIFF checksums are "
            "retained in the merged annual source-artifact manifest."
        ),
    }
    write_csv(provenance_path, PROVENANCE_FIELDS, [provenance_row])

    rainfall_values = [float(row["value_numeric"]) for row in observations]
    coverage_values = [float(row["valid_area_fraction"]) for row in diagnostics]
    manifest = {
        "generated_at": generated_at,
        "panel_version": 2,
        "indicator_id": indicator,
        "claim_type": claim_type,
        "unit": unit,
        "years": {
            "start": start_year,
            "end": end_year,
            "count": len(expected_years),
        },
        "geography": {
            **geography_contract,
            "raw_geojson_sha256": geometry_sha,
        },
        "chirps": {
            **chirps_contract,
            "annual_raster_count": len(expected_years),
        },
        "method": method,
        "cross_granularity_validation": equivalence,
        "quality": {
            "observation_count": len(observations),
            "annual_diagnostic_count": len(diagnostics),
            "source_artifact_count": len(sources),
            "minimum_valid_area_fraction": min(coverage_values),
            "maximum_valid_area_fraction": max(coverage_values),
            "minimum_annual_rainfall_mm": min(rainfall_values),
            "maximum_annual_rainfall_mm": max(rainfall_values),
        },
        "outputs": {},
        "negative_guards": negative_guards,
        "chunk_merge": {
            "chunk_count": len(chunks),
            "chunk_ranges": [f"{chunk['start']}-{chunk['end']}" for chunk in chunks],
            "identical_geometry_sha256_required": True,
            "overlap_forbidden": True,
            "full_year_coverage_required": True,
        },
        "big_live_probe": None,
    }
    for path in (observations_path, diagnostics_path, sources_path, provenance_path):
        manifest["outputs"][path.name] = {
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Merge validated CHIRPS annual rainfall chunks")
    parser.add_argument("--chunks-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--start-year", type=int, required=True)
    parser.add_argument("--end-year", type=int, required=True)
    args = parser.parse_args()
    manifest = merge_chunks(
        chunks_root=args.chunks_root,
        output_dir=args.output_dir,
        start_year=args.start_year,
        end_year=args.end_year,
    )
    print(json.dumps(manifest["quality"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
