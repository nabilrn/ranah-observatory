from __future__ import annotations

import csv
from pathlib import Path


def existing_canonical_collisions(
    processed_root: Path,
    output_dir: Path,
) -> tuple[set[str], set[tuple[str, str, str, str]]]:
    """Return canonical observation IDs and semantic keys outside ``output_dir``.

    Both paths are normalized before comparison so callers may pass relative or
    absolute output directories without accidentally scanning their own prior
    materialization as an external collision.
    """
    processed_root = processed_root.resolve()
    output_dir = output_dir.resolve()
    observation_ids: set[str] = set()
    semantic_keys: set[tuple[str, str, str, str]] = set()

    for path in processed_root.rglob("*.csv"):
        resolved_path = path.resolve()
        if output_dir == resolved_path.parent or output_dir in resolved_path.parents:
            continue
        try:
            with resolved_path.open("r", encoding="utf-8", newline="") as handle:
                reader = csv.DictReader(handle)
                fields = set(reader.fieldnames or [])
                if not {"observation_id", "indicator_id", "geography_id", "time_start"}.issubset(fields):
                    continue
                for row in reader:
                    observation_id = (row.get("observation_id") or "").strip()
                    if observation_id:
                        observation_ids.add(observation_id)
                    semantic_key = (
                        (row.get("indicator_id") or "").strip(),
                        (row.get("geography_id") or "").strip(),
                        (row.get("time_start") or "").strip(),
                        (row.get("time_end") or "").strip(),
                    )
                    if all(semantic_key[:3]):
                        semantic_keys.add(semantic_key)
        except (OSError, UnicodeDecodeError, csv.Error):
            continue

    return observation_ids, semantic_keys
