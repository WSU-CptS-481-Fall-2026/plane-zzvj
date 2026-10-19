# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import pytest
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
