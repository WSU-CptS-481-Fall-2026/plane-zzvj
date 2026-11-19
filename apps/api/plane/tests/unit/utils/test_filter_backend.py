# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import json
from types import SimpleNamespace
from unittest.mock import Mock

import django_filters
import pytest
from django.db.models import Q, QuerySet
from rest_framework.exceptions import ValidationError

from plane.db.models import Issue
from plane.utils.filters import BaseFilterSet, ComplexFilterBackend, IssueFilterSet

pytestmark = pytest.mark.unit


@pytest.fixture
def queryset():
    return Mock(spec=QuerySet, model=Issue)


def apply_filter(queryset, *, data=None, params=None, filterset=IssueFilterSet, **view_options):
    request = SimpleNamespace(query_params=params or {})
    view = SimpleNamespace(filterset_class=filterset, **view_options)
    return ComplexFilterBackend().filter_queryset(request, queryset, view, filter_data=data)


@pytest.mark.parametrize("as_json", [False, True])
def test_explicit_filter_takes_precedence_over_query_string(queryset, as_json):
    data = {"priority": "high"}
    result = apply_filter(queryset, data=json.dumps(data) if as_json else data, params={"filters": "bad json"})
    queryset.filter.assert_called_once_with(Q(priority__exact="high"))
    assert result is queryset.filter.return_value


@pytest.mark.parametrize("params", [{}, {"filters": ""}, {"filters": "{}"}])
def test_unset_filters_return_the_existing_queryset(queryset, params):
    assert apply_filter(queryset, params=params) is queryset
    queryset.filter.assert_not_called()


@pytest.mark.parametrize(
    ("arguments", "code", "source"),
    [
        ({"data": "{"}, "invalid_json", "'filter_data'"),
        ({"params": {"filters": "{"}}, "invalid_json", "'filter'"),
        ({"data": ["high"]}, "invalid_filter_type", "'filter_data'"),
        ({"data": 7}, "invalid_filter_type", "'filter_data'"),
        ({"data": '["high"]'}, "invalid_filter_node", "JSON object"),
    ],
)
def test_input_errors_identify_the_source(queryset, arguments, code, source):
    with pytest.raises(ValidationError) as error:
        apply_filter(queryset, **arguments)
    assert error.value.detail["code"] == code
    assert source in error.value.detail["message"]


@pytest.mark.parametrize(
    ("data", "code"),
    [
        ({"and": []}, "invalid_operator_children"),
        ({"or": {"priority": "high"}}, "invalid_operator_children"),
        ({"and": [{"priority": "high"}, 1]}, "invalid_operator_child_type"),
        ({"not": []}, "invalid_not_child"),
        ({"not": {}}, "empty_filter_object"),
        ({"and": [], "NOT": {}}, "multiple_logical_operators"),
        ({"Or": [], "priority": "high"}, "mixed_operator_and_fields"),
        ({"priority__in": []}, "empty_list_value"),
        ({"priority__in": ["high", {"priority": "low"}]}, "non_scalar_list_item"),
        ({"priority": {"value": "high"}}, "invalid_value_type"),
        ({"not": {"priority__startswith": "h"}}, "invalid_filter_field"),
        ({"PRIORITY": "high"}, "invalid_filter_field"),
    ],
)
def test_invalid_nodes_are_rejected_before_querying(queryset, data, code):
    with pytest.raises(ValidationError) as error:
        apply_filter(queryset, data=data)
    assert error.value.detail["code"] == code
    queryset.filter.assert_not_called()


def test_invalid_shape_is_reported_before_an_unknown_field(queryset):
    with pytest.raises(ValidationError) as error:
        apply_filter(queryset, data={"and": [{"unknown": "high"}, {"or": []}]})
    assert error.value.detail["code"] == "invalid_operator_children"


@pytest.mark.parametrize("filterset", [None, SimpleNamespace(base_filters={})])
def test_view_needs_declared_filters(queryset, filterset):
    with pytest.raises(ValidationError) as error:
        apply_filter(queryset, data={"priority": "high"}, filterset=filterset)
    assert error.value.detail["code"] == "filtering_not_enabled"


def test_configured_filterset_must_build_a_query(queryset):
    class PlainFilters(django_filters.FilterSet):
        class Meta:
            model = Issue
            fields = ["priority"]

    with pytest.raises(ValidationError) as error:
        apply_filter(queryset, data={"priority": "high"}, filterset=PlainFilters)
    assert error.value.detail["code"] == "missing_build_combined_q"


def test_view_specific_field_alias_can_be_validated_and_applied(queryset):
    class StatusBackend(ComplexFilterBackend):
        def _transform_field_name_for_validation(self, field_name):
            return "state_group" if field_name == "status" else field_name

        def _preprocess_leaf_conditions(self, leaf_conditions, view, queryset):
            return {self._transform_field_name_for_validation(key): value for key, value in leaf_conditions.items()}

    view = SimpleNamespace(filterset_class=IssueFilterSet)
    StatusBackend().filter_queryset(None, queryset, view, filter_data={"not": {"status": "started"}})
    queryset.filter.assert_called_once_with(~Q(state__group__exact="started"))


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        ({"is_draft": False}, Q(is_draft__exact=False)),
        ({"target_date": None}, Q(target_date__exact=None)),
        ({"state_group__in": ["started", "backlog"]}, Q(state__group__in=["started", "backlog"])),
        ({"state_group__in": "started,backlog"}, Q(state__group__in=["started", "backlog"])),
    ],
)
def test_filterset_receives_typed_scalars_and_csv_values(queryset, data, expected):
    apply_filter(queryset, data=data)
    queryset.filter.assert_called_once_with(expected)


def test_repeated_values_reach_a_non_csv_multiple_choice_field(queryset):
    class Priorities(BaseFilterSet):
        priorities = django_filters.MultipleChoiceFilter(
            choices=[("high", "High"), ("low", "Low")], method="by_priorities"
        )

        class Meta:
            model = Issue
            fields = []

        def by_priorities(self, queryset, name, value):
            return Q(priority__in=value)

    apply_filter(queryset, data={"priorities": ["low", "high"]}, filterset=Priorities)
    queryset.filter.assert_called_once_with(Q(priority__in=["low", "high"]))


@pytest.mark.parametrize(
    ("data", "field", "message"),
    [
        ({"state_group": ["started"]}, "state_group", "Expected a single value."),
        ({"state_group__in": ["started", "unknown"]}, "state_group__in", "unknown"),
    ],
)
def test_invalid_choices_report_the_field(queryset, data, field, message):
    with pytest.raises(ValidationError) as error:
        apply_filter(queryset, data=data)
    assert error.value.detail["code"] == "invalid_filterset"
    assert message in str(error.value.detail["errors"][field])


@pytest.mark.parametrize(
    ("view_options", "limit"),
    [
        ({}, 5),
        ({"complex_filter_max_depth": 1}, 1),
        ({"complex_filter_max_depth": "3"}, 3),
        ({"complex_filter_max_depth": 0}, 5),
        ({"complex_filter_max_depth": -1}, 5),
        ({"complex_filter_max_depth": "bad"}, 5),
        ({"complex_filter_max_depth": None}, 5),
    ],
)
def test_depth_counts_the_root_and_rejects_the_next_level(queryset, view_options, limit):
    node = {"priority": "low"}
    for _ in range(1, limit):
        node = {"not": node}
    apply_filter(queryset, data=node, **view_options)
    queryset.filter.assert_called_once()
    with pytest.raises(ValidationError) as error:
        apply_filter(queryset, data={"not": node}, **view_options)
    assert error.value.detail["code"] == "max_depth_exceeded"
    assert f"max {limit}" in error.value.detail["message"]
