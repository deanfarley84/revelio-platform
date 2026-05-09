"""Sanity checks on the default benchmark seed data shape."""
from app.services.seed_defaults import DEFAULT_BENCHMARKS


def test_required_columns_present():
    required = {"category", "key", "label", "value_low", "value_high",
                "value_default", "unit", "vertical"}
    for row in DEFAULT_BENCHMARKS:
        missing = required - row.keys()
        assert not missing, f"{row.get('key')} missing {missing}"


def test_default_within_range():
    for row in DEFAULT_BENCHMARKS:
        assert row["value_low"] <= row["value_default"] <= row["value_high"], \
            f"{row['key']}: default {row['value_default']} not in [{row['value_low']}, {row['value_high']}]"


def test_keys_unique_per_vertical():
    seen = set()
    for row in DEFAULT_BENCHMARKS:
        composite = (row["category"], row["key"], row["vertical"])
        assert composite not in seen, f"duplicate seed: {composite}"
        seen.add(composite)


def test_general_fallback_present():
    # AI prompt falls back to vertical='all' when no vertical-specific row matches.
    has_fallback_auth = any(
        r["category"] == "auth_rate" and r["vertical"] == "all"
        for r in DEFAULT_BENCHMARKS
    )
    assert has_fallback_auth, "missing general (vertical='all') auth rate fallback"
