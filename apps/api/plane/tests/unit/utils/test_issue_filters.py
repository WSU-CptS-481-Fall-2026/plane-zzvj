# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from copy import deepcopy
from datetime import date
from uuid import UUID

import pytest
from freezegun import freeze_time
from rest_framework.exceptions import ValidationError

from plane.db.models import StateGroup
from plane.utils.issue_filters import filter_updated_at, issue_filters


@pytest.mark.unit
class TestStateGroupFilter:
    @pytest.mark.parametrize("group", StateGroup.values)
    @pytest.mark.parametrize("method", ["GET", "POST"])
    def test_valid_groups(self, group, method):
        value = group if method == "GET" else [group]
        assert issue_filters({"state_group": value}, method, "issue__") == {"issue__state__group__in": [group]}

    @pytest.mark.parametrize("groups", [["hello"], ["hello", "completed"], ["completed", "hello"]])
    @pytest.mark.parametrize("method", ["GET", "POST", "PATCH"])
    def test_invalid_groups_raise_a_field_error(self, groups, method):
        value = ",".join(groups) if method == "GET" else groups
        with pytest.raises(ValidationError) as exc:
            issue_filters({"state_group": value}, method)
        assert "state_group" in exc.value.detail
        assert "hello" in str(exc.value.detail)

    @pytest.mark.parametrize("value", [None, "", "null"])
    @pytest.mark.parametrize("method", ["GET", "POST"])
    def test_unset_group_is_noop(self, value, method):
        assert issue_filters({"state_group": value}, method) == {}

    def test_legacy_null_entries_and_empty_post_list(self):
        assert issue_filters({"state_group": "null,completed"}, "GET") == {"state__group__in": ["completed"]}
        assert issue_filters({"state_group": []}, "POST") == {}

    @pytest.mark.parametrize("value", ["completed", {"group": "completed"}, [None]])
    def test_non_get_requires_a_list_of_groups(self, value):
        with pytest.raises(ValidationError):
            issue_filters({"state_group": value}, "POST")


@pytest.mark.unit
class TestFilterUpdatedAt:
    """Regression test for the "Updated At" filter bug — the filter was
    applying to the `created_at` column instead of `updated_at`, so work
    items updated today but created earlier never showed up under
    `Updated At -> is -> today`. See issue #9316."""

    def test_get_method_targets_updated_at_column(self):
        issue_filter = {}
        params = {"updated_at": "2026-06-26"}
        filter_updated_at(params, issue_filter, method="GET")
        # The filter must key on updated_at, not created_at. A bare date goes through
        # date_filter's single-value branch, which appends a lookup suffix
        # (updated_at__date__contains), so match on the prefix rather than the exact key.
        assert any(key.startswith("updated_at__date") for key in issue_filter)
        assert not any("created_at" in key for key in issue_filter)

    def test_get_method_with_csv_targets_updated_at_column(self):
        issue_filter = {}
        params = {"updated_at": "2026-06-25,2026-06-26"}
        filter_updated_at(params, issue_filter, method="GET")
        assert all("updated_at" in key for key in issue_filter)
        assert not any("created_at" in key for key in issue_filter)

    def test_post_method_targets_updated_at_column(self):
        issue_filter = {}
        params = {"updated_at": ["2026-06-26"]}
        filter_updated_at(params, issue_filter, method="POST")
        assert all("updated_at" in key for key in issue_filter)
        assert not any("created_at" in key for key in issue_filter)

    def test_get_method_with_prefix_targets_updated_at_column(self):
        issue_filter = {}
        params = {"updated_at": "2026-06-26"}
        filter_updated_at(params, issue_filter, method="GET", prefix="cycle_issue__")
        keys = list(issue_filter)
        assert any("cycle_issue__updated_at" in k for k in keys)
        assert not any("created_at" in k for k in keys)

    def test_empty_get_filter_is_noop(self):
        issue_filter = {}
        params = {"updated_at": ""}
        filter_updated_at(params, issue_filter, method="GET")
        assert issue_filter == {}


FIRST_UUID = "11111111-1111-4111-8111-111111111111"
SECOND_UUID = "22222222-2222-4222-8222-222222222222"

UUID_FILTERS = [
    pytest.param("state", "state__in", {}, id="state"),
    pytest.param("parent", "parent__in", {}, id="parent"),
    pytest.param("labels", "labels__in", {"label_issue__deleted_at__isnull": True}, id="labels"),
    pytest.param("assignees", "assignees__in", {"issue_assignee__deleted_at__isnull": True}, id="assignees"),
    pytest.param("mentions", "issue_mention__mention__id__in", {}, id="mentions"),
    pytest.param("created_by", "created_by__in", {}, id="created-by"),
    pytest.param("logged_by", "logged_by__in", {}, id="logged-by"),
    pytest.param("project", "project__in", {}, id="project"),
    pytest.param("cycle", "issue_cycle__cycle_id__in", {"issue_cycle__deleted_at__isnull": True}, id="cycle"),
    pytest.param("module", "issue_module__module_id__in", {"issue_module__deleted_at__isnull": True}, id="module"),
    pytest.param(
        "subscriber",
        "issue_subscribers__subscriber_id__in",
        {"issue_subscribers__deleted_at__isnull": True},
        id="subscriber",
    ),
]


@pytest.mark.unit
@pytest.mark.parametrize(("field", "lookup", "extra_filters"), UUID_FILTERS)
class TestLegacyUuidFilters:
    def test_get_parses_uuids_and_prefixes_all_conditions(self, field, lookup, extra_filters):
        expected = {**extra_filters, lookup: [UUID(FIRST_UUID), UUID(SECOND_UUID)]}

        assert issue_filters({field: f"{FIRST_UUID},{SECOND_UUID}"}, "GET", "issue__") == {
            f"issue__{key}": value for key, value in expected.items()
        }

    def test_get_discards_invalid_null_and_empty_entries(self, field, lookup, extra_filters):
        assert issue_filters({field: f"invalid,null,,{FIRST_UUID},{SECOND_UUID}"}, "GET") == {
            **extra_filters,
            lookup: [UUID(FIRST_UUID), UUID(SECOND_UUID)],
        }

    @pytest.mark.parametrize("value", ["", "null", "invalid"])
    def test_get_without_valid_ids_keeps_relationship_conditions(self, field, lookup, extra_filters, value):
        assert issue_filters({field: value}, "GET") == extra_filters

    def test_post_keeps_uuid_strings_and_prefixes_all_conditions(self, field, lookup, extra_filters):
        values = [FIRST_UUID, SECOND_UUID]
        expected = {**extra_filters, lookup: values}

        assert issue_filters({field: values}, "POST", "cycle_issue__") == {
            f"cycle_issue__{key}": value for key, value in expected.items()
        }

    @pytest.mark.parametrize("value", [None, "", [], "null"])
    def test_post_unset_values_keep_relationship_conditions(self, field, lookup, extra_filters, value):
        assert issue_filters({field: value}, "POST") == extra_filters


@pytest.mark.unit
class TestMissingRelationships:
    @pytest.mark.parametrize(
        ("field", "null_lookup", "extra_filters"),
        [
            ("parent", "parent__isnull", {}),
            ("labels", "labels__isnull", {"label_issue__deleted_at__isnull": True}),
            ("assignees", "assignees__isnull", {"issue_assignee__deleted_at__isnull": True}),
            ("created_by", "created_by__isnull", {}),
            ("logged_by", "logged_by__isnull", {}),
            ("cycle", "issue_cycle__cycle_id__isnull", {"issue_cycle__deleted_at__isnull": True}),
            ("module", "issue_module__module_id__isnull", {"issue_module__deleted_at__isnull": True}),
        ],
    )
    def test_none_selects_missing_relationships(self, field, null_lookup, extra_filters):
        expected = {**extra_filters, null_lookup: True}

        assert issue_filters({field: "None"}, "GET", "issue__") == {
            f"issue__{key}": value for key, value in expected.items()
        }

    def test_parent_can_preserve_both_none_and_a_uuid_condition(self):
        assert issue_filters({"parent": f"None,{FIRST_UUID}"}, "GET") == {
            "parent__isnull": True,
            "parent__in": [UUID(FIRST_UUID)],
        }


@pytest.mark.unit
class TestLegacyValueFilters:
    @pytest.mark.parametrize(
        ("field", "lookup", "values"),
        [
            ("estimate_point", "estimate_point__in", ["1", "3"]),
            ("priority", "priority__in", ["high", "low"]),
            ("intake_status", "issue_intake__status__in", ["0", "1"]),
            ("inbox_status", "issue_intake__status__in", ["0", "1"]),
        ],
    )
    def test_get_splits_csv_and_omits_null(self, field, lookup, values):
        query = f"{values[0]},null,{values[1]}"

        assert issue_filters({field: query}, "GET", "issue__") == {f"issue__{lookup}": values}

    @pytest.mark.parametrize("field", ["estimate_point", "priority", "intake_status", "inbox_status"])
    @pytest.mark.parametrize("value", ["", "null"])
    def test_empty_get_values_are_unset(self, field, value):
        assert issue_filters({field: value}, "GET") == {}

    @pytest.mark.parametrize(
        ("field", "value"),
        [("estimate_point", "1,"), ("priority", "high,"), ("intake_status", "0,"), ("inbox_status", "0,")],
    )
    def test_get_with_an_empty_entry_leaves_the_whole_filter_unset(self, field, value):
        assert issue_filters({field: value}, "GET") == {}

    @pytest.mark.parametrize(
        ("field", "lookup", "values"),
        [
            ("estimate_point", "estimate_point__in", [1, 3]),
            ("priority", "priority__in", ["high", "low"]),
            ("inbox_status", "issue_intake__status__in", [0, 1]),
        ],
    )
    def test_post_preserves_list_values(self, field, lookup, values):
        assert issue_filters({field: values}, "POST", "issue__") == {f"issue__{lookup}": values}

    @pytest.mark.parametrize("field", ["estimate_point", "priority", "intake_status", "inbox_status"])
    @pytest.mark.parametrize("value", [None, "", [], "null"])
    def test_unset_post_values_do_not_add_conditions(self, field, value):
        assert issue_filters({field: value}, "POST") == {}

    @pytest.mark.parametrize("method", ["POST", "PATCH"])
    def test_non_get_intake_status_uses_requested_values(self, method):
        assert issue_filters({"intake_status": [0, 1]}, method, "issue__") == {
            "issue__issue_intake__status__in": [0, 1]
        }

    def test_inbox_status_retains_precedence_when_both_names_are_supplied(self):
        assert issue_filters({"inbox_status": [1], "intake_status": [0]}, "POST") == {"issue_intake__status__in": [1]}

    def test_empty_inbox_status_keeps_intake_status(self):
        params = {"intake_status": [0], "inbox_status": []}
        assert issue_filters(params, "POST") == {"issue_intake__status__in": [0]}


@pytest.mark.unit
@pytest.mark.parametrize(
    ("field", "lookup"),
    [
        ("created_at", "created_at__date"),
        ("updated_at", "updated_at__date"),
        ("completed_at", "completed_at__date"),
        ("start_date", "start_date"),
        ("target_date", "target_date"),
    ],
)
class TestLegacyGetDates:
    def test_bare_dates_use_contains_lookup(self, field, lookup):
        assert issue_filters({field: "2026-11-13"}, "GET", "issue__") == {f"issue__{lookup}__contains": "2026-11-13"}

    def test_after_and_before_bounds_are_both_kept(self, field, lookup):
        assert issue_filters({field: "2026-11-01;after,2026-11-30;before"}, "GET", "issue__") == {
            f"issue__{lookup}__gte": "2026-11-01",
            f"issue__{lookup}__lte": "2026-11-30",
        }

    @pytest.mark.parametrize("value", ["", ",2026-11-13"])
    def test_empty_entries_leave_the_date_filter_unset(self, field, lookup, value):
        assert issue_filters({field: value}, "GET") == {}


@pytest.mark.unit
class TestLegacyPostDates:
    @pytest.mark.parametrize("field", ["created_at", "updated_at", "completed_at"])
    def test_datetime_fields_parse_date_bounds(self, field):
        assert issue_filters({field: ["2026-11-01;after", "2026-11-30;before"]}, "POST", "issue__") == {
            f"issue__{field}__date__gte": "2026-11-01",
            f"issue__{field}__date__lte": "2026-11-30",
        }

    @pytest.mark.parametrize("field", ["start_date", "target_date"])
    def test_date_fields_keep_direct_values(self, field):
        assert issue_filters({field: "2026-11-13"}, "POST", "issue__") == {f"issue__{field}": "2026-11-13"}

    @pytest.mark.parametrize("field", ["created_at", "updated_at", "completed_at", "start_date", "target_date"])
    @pytest.mark.parametrize("value", [None, [], ""])
    def test_unset_post_dates_do_not_add_conditions(self, field, value):
        assert issue_filters({field: value}, "POST") == {}


@pytest.mark.unit
class TestRelativeDates:
    @freeze_time("2026-11-13 12:00:00+00:00")
    @pytest.mark.parametrize(
        ("value", "lookup", "expected"),
        [
            ("2_weeks;after;fromnow", "gte", date(2026, 11, 27)),
            ("2_weeks;before;fromnow", "lte", date(2026, 11, 27)),
            ("2_weeks;after;ago", "gte", date(2026, 10, 30)),
            ("2_weeks;before;ago", "lte", date(2026, 10, 30)),
            ("2_months;after;fromnow", "gte", date(2027, 1, 12)),
            ("2_months;before;fromnow", "lte", date(2027, 1, 12)),
            ("2_months;after;ago", "gte", date(2026, 9, 14)),
            ("2_months;before;ago", "lte", date(2026, 9, 14)),
            ("0_weeks;after;fromnow", "gte", date(2026, 11, 13)),
        ],
    )
    def test_relative_bounds_use_weeks_and_thirty_day_months(self, value, lookup, expected):
        assert issue_filters({"target_date": value}, "GET", "issue__") == {f"issue__target_date__{lookup}": expected}

    @pytest.mark.parametrize("value", ["2_weeks;after", "2_weeks;after;fromnow;extra"])
    def test_incomplete_or_extra_relative_date_parts_are_ignored(self, value):
        assert issue_filters({"target_date": value, "priority": "low"}, "GET") == {"priority__in": ["low"]}


@pytest.mark.unit
class TestLegacyFilterComposition:
    @pytest.mark.parametrize("method", ["GET", "POST", "PATCH"])
    def test_missing_and_unknown_fields_do_not_add_conditions(self, method):
        assert issue_filters({}, method) == {}
        assert issue_filters({"unknown": "value"}, method) == {}

    def test_state_group_csv_with_only_null_and_empty_entries_is_unset(self):
        assert issue_filters({"state_group": "null,,"}, "GET") == {}

    @pytest.mark.parametrize("method", ["GET", "POST"])
    def test_name_filter_preserves_text_and_prefix(self, method):
        assert issue_filters({"name": "Release Candidate"}, method, "issue__") == {
            "issue__name__icontains": "Release Candidate"
        }
        assert issue_filters({"name": ""}, method) == {}

    @pytest.mark.parametrize(
        ("issue_type", "groups"),
        [
            ("backlog", ["backlog"]),
            ("active", ["unstarted", "started"]),
            ("all", ["backlog", "unstarted", "started", "completed", "cancelled"]),
        ],
    )
    def test_issue_type_selects_state_groups(self, issue_type, groups):
        assert issue_filters({"type": issue_type}, "GET", "issue__") == {"issue__state__group__in": groups}

    @pytest.mark.parametrize("method", ["GET", "POST"])
    @pytest.mark.parametrize(("value", "expected"), [("false", {"issue__parent__isnull": True}), ("true", {})])
    def test_sub_issue_toggle(self, method, value, expected):
        assert issue_filters({"sub_issue": value}, method, "issue__") == expected

    @pytest.mark.parametrize("method", ["GET", "POST"])
    @pytest.mark.parametrize(
        ("value", "expected"),
        [("true", {"issue__start_date__isnull": False, "issue__target_date__isnull": False}), ("false", {})],
    )
    def test_start_target_date_toggle(self, method, value, expected):
        assert issue_filters({"start_target_date": value}, method, "issue__") == expected

    def test_get_combines_filters_without_changing_the_input(self):
        params = {
            "state": FIRST_UUID,
            "priority": "high,low",
            "labels": SECOND_UUID,
            "created_at": "2026-11-01;after",
            "name": "Release",
            "sub_issue": "false",
        }
        original = deepcopy(params)

        assert issue_filters(params, "GET", "cycle_issue__") == {
            "cycle_issue__state__in": [UUID(FIRST_UUID)],
            "cycle_issue__priority__in": ["high", "low"],
            "cycle_issue__labels__in": [UUID(SECOND_UUID)],
            "cycle_issue__label_issue__deleted_at__isnull": True,
            "cycle_issue__created_at__date__gte": "2026-11-01",
            "cycle_issue__name__icontains": "Release",
            "cycle_issue__parent__isnull": True,
        }
        assert params == original

    def test_patch_combines_filters_without_changing_the_input(self):
        params = {
            "state": [FIRST_UUID],
            "priority": ["low"],
            "created_at": ["2026-11-01;after"],
            "target_date": "2026-11-30",
            "name": "Release",
        }
        original = deepcopy(params)

        assert issue_filters(params, "PATCH", "issue__") == {
            "issue__state__in": [FIRST_UUID],
            "issue__priority__in": ["low"],
            "issue__created_at__date__gte": "2026-11-01",
            "issue__target_date": "2026-11-30",
            "issue__name__icontains": "Release",
        }
        assert params == original

    def test_calls_do_not_share_filter_conditions(self):
        first_result = issue_filters({"priority": "high"}, "GET")

        assert issue_filters({}, "GET") == {}
        assert first_result == {"priority__in": ["high"]}
