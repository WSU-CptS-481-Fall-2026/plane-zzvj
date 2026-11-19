# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from copy import deepcopy

import pytest

from plane.utils.filters.converters import LegacyToRichFiltersConverter


FIRST_UUID = "11111111-1111-4111-8111-111111111111"
SECOND_UUID = "22222222-2222-4222-8222-222222222222"

INVALID_FIELD_CASES = [
    ("state", "not-a-uuid", "not-a-uuid"),
    ("state", ["not-a-uuid"], "not-a-uuid"),
    ("priority", "not-a-priority", "not-a-priority"),
    ("priority", ["not-a-priority"], "not-a-priority"),
    ("state_group", "not-a-group", "not-a-group"),
    ("state_group", ["not-a-group"], "not-a-group"),
]


@pytest.fixture
def converter():
    return LegacyToRichFiltersConverter()


@pytest.mark.unit
class TestFilterConversion:
    @pytest.mark.parametrize(
        ("legacy_field", "rich_field"),
        [
            ("state", "state_id"),
            ("labels", "label_id"),
            ("cycle", "cycle_id"),
            ("module", "module_id"),
            ("assignees", "assignee_id"),
            ("mentions", "mention_id"),
            ("created_by", "created_by_id"),
            ("project", "project_id"),
        ],
    )
    @pytest.mark.parametrize(
        ("value", "lookup", "expected_value"),
        [
            (FIRST_UUID, "exact", FIRST_UUID),
            ([FIRST_UUID, SECOND_UUID], "in", f"{FIRST_UUID},{SECOND_UUID}"),
        ],
        ids=["scalar", "list"],
    )
    def test_uuid_field_mappings(self, converter, legacy_field, rich_field, value, lookup, expected_value):
        assert converter.convert({legacy_field: value}, strict=True) == {f"{rich_field}__{lookup}": expected_value}

    @pytest.mark.parametrize(
        ("filters", "expected"),
        [
            ({"priority": "high"}, {"priority__exact": "high"}),
            ({"priority": ["high"]}, {"priority__in": "high"}),
            (
                {"priority": ["urgent", "high", "medium", "low", "none"]},
                {"priority__in": "urgent,high,medium,low,none"},
            ),
            ({"state_group": "started"}, {"state_group__exact": "started"}),
            (
                {"state_group": ["backlog", "unstarted", "started", "completed", "cancelled"]},
                {"state_group__in": "backlog,unstarted,started,completed,cancelled"},
            ),
        ],
    )
    def test_choice_fields(self, converter, filters, expected):
        assert converter.convert(filters, strict=True) == expected

    @pytest.mark.parametrize("strict", [False, True])
    @pytest.mark.parametrize("filters", [{}, {"state": None}, {"priority": []}])
    def test_empty_filters_are_omitted(self, converter, filters, strict):
        assert converter.convert(filters, strict=strict) == {}

    @pytest.mark.parametrize(("field", "value"), [(field, value) for field, value, _ in INVALID_FIELD_CASES])
    def test_permissive_mode_omits_invalid_fields(self, converter, field, value):
        assert converter.convert({field: value, "target_date": "2026-11-13"}) == {"target_date__exact": "2026-11-13"}

    @pytest.mark.parametrize(("field", "value", "invalid_value"), INVALID_FIELD_CASES)
    def test_strict_mode_reports_invalid_fields(self, converter, field, value, invalid_value):
        with pytest.raises(ValueError) as exc:
            converter.convert({field: value}, strict=True)

        assert field in str(exc.value)
        assert invalid_value in str(exc.value)

    @pytest.mark.parametrize(
        ("filters", "expected"),
        [
            ({"state": ["invalid", FIRST_UUID]}, {"state_id__in": FIRST_UUID}),
            ({"priority": ["high", "invalid", "low"]}, {"priority__in": "high,low"}),
            ({"state_group": ["invalid", "started"]}, {"state_group__in": "started"}),
        ],
    )
    def test_permissive_mode_retains_valid_list_entries(self, converter, filters, expected):
        assert converter.convert(filters) == expected

    @pytest.mark.parametrize(
        "filters",
        [
            {"state": ["invalid", FIRST_UUID]},
            {"priority": ["high", "invalid", "low"]},
            {"state_group": ["invalid", "started"]},
        ],
    )
    def test_strict_mode_rejects_partly_invalid_lists(self, converter, filters):
        with pytest.raises(ValueError, match="Invalid values") as exc:
            converter.convert(filters, strict=True)

        assert next(iter(filters)) in str(exc.value)
        assert "invalid" in str(exc.value)

    def test_permissive_mode_omits_unknown_fields(self, converter):
        assert converter.convert({"unknown": "value", "priority": "high"}) == {"priority__exact": "high"}

    def test_strict_mode_reports_errors_from_multiple_fields(self, converter):
        with pytest.raises(ValueError) as exc:
            converter.convert(
                {
                    "unknown": "value",
                    "state": "not-a-uuid",
                    "priority": ["high", "not-a-priority"],
                    "start_date": "not-a-date",
                },
                strict=True,
            )

        message = str(exc.value)
        assert message.startswith("Filter validation errors:")
        assert "Unsupported filter key: unknown" in message
        assert "Invalid value for state: not-a-uuid" in message
        assert "Invalid values for priority: ['not-a-priority']" in message
        assert "Invalid date format: not-a-date" in message

    def test_multiple_fields_are_joined_with_and(self, converter):
        assert converter.convert({"state": FIRST_UUID, "priority": ["high", "low"]}, strict=True) == {
            "and": [{"state_id__exact": FIRST_UUID}, {"priority__in": "high,low"}]
        }

    def test_conversion_preserves_input_lists_and_dates(self, converter):
        filters = {
            "state": ["invalid", FIRST_UUID, SECOND_UUID],
            "target_date": ["2026-11-30;before", "2026-11-01;after"],
        }
        original = deepcopy(filters)

        assert converter.convert(filters) == {
            "and": [
                {"state_id__in": f"{FIRST_UUID},{SECOND_UUID}"},
                {"target_date__range": "2026-11-01,2026-11-30"},
            ]
        }
        assert filters == original

    def test_failed_conversion_preserves_input(self, converter):
        filters = {"state": [FIRST_UUID, "invalid"], "priority": ["high", "low"]}
        original = deepcopy(filters)

        with pytest.raises(ValueError):
            converter.convert(filters, strict=True)

        assert filters == original
        assert converter.convert({"priority": "low"}, strict=True) == {"priority__exact": "low"}


@pytest.mark.unit
class TestDateConversion:
    @pytest.mark.parametrize("field", ["start_date", "target_date"])
    @pytest.mark.parametrize("value", ["2026-11-13", ["2026-11-13"]], ids=["scalar", "list"])
    def test_single_dates_use_exact_lookup(self, converter, field, value):
        assert converter.convert({field: value}, strict=True) == {f"{field}__exact": "2026-11-13"}

    @pytest.mark.parametrize(
        ("values", "expected"),
        [
            (["2026-11-01;after", "2026-11-30;before"], "2026-11-01,2026-11-30"),
            (["2026-11-30;before", "2026-11-01;after"], "2026-11-01,2026-11-30"),
            (["2026-11-13;after", "2026-11-13;before"], "2026-11-13,2026-11-13"),
        ],
        ids=["after-before", "before-after", "same-day"],
    )
    def test_date_ranges(self, converter, values, expected):
        assert converter.convert({"target_date": values}, strict=True) == {"target_date__range": expected}

    @pytest.mark.parametrize("value", ["not-a-date", "not-a-date;after", "not-a-date;before"])
    def test_permissive_mode_omits_invalid_dates(self, converter, value):
        assert converter.convert({"start_date": value, "priority": "high"}) == {"priority__exact": "high"}

    @pytest.mark.parametrize("value", ["not-a-date", "not-a-date;after", "not-a-date;before"])
    def test_strict_mode_reports_invalid_dates(self, converter, value):
        with pytest.raises(ValueError, match="Invalid date format: not-a-date"):
            converter.convert({"start_date": value}, strict=True)

    @pytest.mark.parametrize("values", [["not-a-date", "2026-11-13"], ["2026-11-13", "not-a-date"]])
    def test_permissive_mode_keeps_a_valid_date_from_a_mixed_list(self, converter, values):
        assert converter.convert({"start_date": values}) == {"start_date__exact": "2026-11-13"}

    @pytest.mark.parametrize("strict", [False, True])
    @pytest.mark.parametrize(
        "values",
        [
            ["2_weeks;after;fromnow"],
            ["2026-11-13", "3_months;before;ago"],
            ["2026-11-01", "2026-11-13", "2026-11-30"],
            ["2026-11-01", "2026-11-30"],
            ["2026-11-01;after"],
            ["2026-11-30;before"],
            ["2026-11-01;after", "2026-11-30;after"],
            ["2026-11-01", "2026-11-30;before"],
            ["2026-11-13;on"],
        ],
        ids=[
            "relative-weeks",
            "relative-months-with-exact-date",
            "more-than-two-values",
            "two-exact-dates",
            "after-only",
            "before-only",
            "two-after-bounds",
            "exact-date-with-bound",
            "unsupported-direction",
        ],
    )
    def test_unsupported_date_expressions_are_skipped(self, converter, values, strict):
        assert converter.convert({"start_date": values, "priority": "low"}, strict=strict) == {"priority__exact": "low"}


@pytest.mark.unit
class TestConverterConfiguration:
    def test_constructor_extends_default_configuration(self):
        converter = LegacyToRichFiltersConverter(
            field_mappings={"owner": "owner_id", "urgency": "severity", "due": "deadline"},
            uuid_fields={"owner_id"},
            valid_choices={"severity": ["critical"]},
            date_fields={"deadline"},
        )

        assert converter.convert(
            {
                "owner": FIRST_UUID,
                "urgency": "critical",
                "due": ["2026-11-01;after", "2026-11-30;before"],
                "priority": "low",
            },
            strict=True,
        ) == {
            "and": [
                {"owner_id__exact": FIRST_UUID},
                {"severity__exact": "critical"},
                {"deadline__range": "2026-11-01,2026-11-30"},
                {"priority__exact": "low"},
            ]
        }

        with pytest.raises(ValueError) as exc:
            converter.convert({"owner": "invalid-owner", "urgency": "invalid-urgency"}, strict=True)
        assert "Invalid value for owner: invalid-owner" in str(exc.value)
        assert "Invalid value for urgency: invalid-urgency" in str(exc.value)

    def test_constructor_replaces_defaults(self):
        converter = LegacyToRichFiltersConverter(field_mappings={"state": "status"}, extend_defaults=False)

        assert converter.convert({"state": "ready"}, strict=True) == {"status__exact": "ready"}
        assert converter.convert({"priority": "high"}) == {}
        with pytest.raises(ValueError, match="Unsupported filter key: priority"):
            converter.convert({"priority": "high"}, strict=True)

    def test_empty_replacement_configuration_has_no_default_fields(self):
        converter = LegacyToRichFiltersConverter(extend_defaults=False)

        assert converter.convert({"state": FIRST_UUID, "priority": "high"}) == {}

    def test_choice_override_does_not_change_other_instances(self, converter):
        custom = LegacyToRichFiltersConverter(valid_choices={"priority": ["critical"]})

        assert custom.convert({"priority": "critical"}, strict=True) == {"priority__exact": "critical"}
        with pytest.raises(ValueError, match="Invalid value for priority: urgent"):
            custom.convert({"priority": "urgent"}, strict=True)
        assert converter.convert({"priority": "urgent"}, strict=True) == {"priority__exact": "urgent"}
        assert LegacyToRichFiltersConverter().convert({"priority": "critical"}) == {}

    def test_fields_can_be_added_individually(self, converter):
        converter.add_field_mapping("owner", "owner_id")
        converter.add_uuid_field("owner_id")
        converter.add_field_mapping("urgency", "severity")
        converter.add_choice_field("severity", ["critical"])
        converter.add_field_mapping("due", "deadline")
        converter.add_date_field("deadline")

        assert converter.convert(
            {"owner": [FIRST_UUID], "urgency": "critical", "due": ["2026-11-01;after", "2026-11-30;before"]},
            strict=True,
        ) == {
            "and": [
                {"owner_id__in": FIRST_UUID},
                {"severity__exact": "critical"},
                {"deadline__range": "2026-11-01,2026-11-30"},
            ]
        }
        with pytest.raises(ValueError) as exc:
            converter.convert({"owner": "invalid-owner", "urgency": "invalid-urgency"}, strict=True)
        assert "invalid-owner" in str(exc.value)
        assert "invalid-urgency" in str(exc.value)

    def test_bulk_update_adds_validators_and_retains_existing_mappings(self, converter):
        converter.update_mappings(
            field_mappings={"owner": "owner_id", "urgency": "severity", "due": "deadline"},
            uuid_fields={"owner_id"},
            valid_choices={"severity": ["critical"]},
            date_fields={"deadline"},
        )
        converter.update_mappings()

        assert converter.convert(
            {"owner": [FIRST_UUID, "invalid-owner"], "urgency": "critical", "due": "2026-11-13", "priority": "low"}
        ) == {
            "and": [
                {"owner_id__in": FIRST_UUID},
                {"severity__exact": "critical"},
                {"deadline__exact": "2026-11-13"},
                {"priority__exact": "low"},
            ]
        }
        with pytest.raises(ValueError) as exc:
            converter.convert({"urgency": "invalid-urgency", "due": "not-a-date"}, strict=True)
        assert "invalid-urgency" in str(exc.value)
        assert "Invalid date format: not-a-date" in str(exc.value)

    @pytest.mark.parametrize("value", [0, False, ""])
    def test_unconstrained_custom_fields_preserve_falsy_values(self, value):
        converter = LegacyToRichFiltersConverter(field_mappings={"custom": "custom_value"}, extend_defaults=False)

        assert converter.convert({"custom": value}, strict=True) == {"custom_value__exact": value}
