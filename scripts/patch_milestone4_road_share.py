#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

TARGET = Path(__file__).resolve().parent / "materialize_bps_milestone4_batch1.py"


def replace_once(text: str, old: str, new: str) -> str:
    if old in text:
        return text.replace(old, new, 1)
    if new in text:
        return text
    raise ValueError(f"expected materializer patch anchor not found: {old[:100]!r}")


def main() -> int:
    text = TARGET.read_text(encoding="utf-8")

    text = replace_once(
        text,
        "EXPECTED_BATCH_OBSERVATIONS = 417",
        "EXPECTED_BATCH_OBSERVATIONS = 415",
    )
    text = replace_once(
        text,
        "def transformed_value(config: dict[str, str], rows_by_turvar: dict[str, dict[str, str]]) -> tuple[Decimal, str]:",
        "def transformed_value(config: dict[str, str], rows_by_turvar: dict[str, dict[str, str]]) -> tuple[Decimal | None, str]:",
    )
    text = replace_once(
        text,
        '''        denominator = sum((part for _, part in parts), Decimal("0"))
        if denominator <= 0:
            raise ValueError(f"{config['series_id']}: non-positive road-length denominator")
        value = (numerator / denominator * Decimal("100")).quantize(Decimal("0.000001"))
        detail = (
            f"numerator={selected}:{decimal_text(numerator)}; denominator_components="
            + "|".join(f"{tid}:{decimal_text(part)}" for tid, part in parts)
        )''',
        '''        denominator = sum((part for _, part in parts), Decimal("0"))
        detail = (
            f"numerator={selected}:{decimal_text(numerator)}; denominator_components="
            + "|".join(f"{tid}:{decimal_text(part)}" for tid, part in parts)
        )
        if denominator < 0:
            raise ValueError(f"{config['series_id']}: negative road-length denominator")
        if denominator == 0:
            return None, detail + "; undefined_zero_denominator=true"
        value = (numerator / denominator * Decimal("100")).quantize(Decimal("0.000001"))''',
    )
    text = replace_once(
        text,
        '''        produced = 0
        for code in sorted(actual_codes):
            geography_id = geo[code]
            value, transform_detail = transformed_value(config, grouped[code])
            observation_id = stable_id(''',
        '''        produced = 0
        undefined_codes: list[str] = []
        for code in sorted(actual_codes):
            geography_id = geo[code]
            value, transform_detail = transformed_value(config, grouped[code])
            if value is None:
                undefined_codes.append(code)
                continue
            observation_id = stable_id(''',
    )
    text = replace_once(
        text,
        '''        if produced != expected_count:
            raise ValueError(f"{config['series_id']}: produced {produced} rows instead of {expected_count}")
        series_summary.append({''',
        '''        expected_produced = expected_count
        if config["series_id"] == "m4_road_good_2024":
            expected_undefined = {"1374", "1375"}
            if set(undefined_codes) != expected_undefined:
                raise ValueError(
                    f"{config['series_id']}: undefined geography set drifted: {sorted(undefined_codes)}"
                )
            expected_produced = 17
        elif undefined_codes:
            raise ValueError(
                f"{config['series_id']}: unexpected undefined geography values: {sorted(undefined_codes)}"
            )
        if produced != expected_produced:
            raise ValueError(
                f"{config['series_id']}: produced {produced} rows instead of {expected_produced}"
            )
        series_summary.append({''',
    )
    text = replace_once(
        text,
        '''            "missing_current_geographies": sorted(EXPECTED_CODES - actual_codes),
        })''',
        '''            "missing_current_geographies": sorted(EXPECTED_CODES - actual_codes),
            "undefined_current_geographies": sorted(undefined_codes),
        })''',
    )

    TARGET.write_text(text, encoding="utf-8")
    print("milestone4 road-share materializer semantics hardened")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
