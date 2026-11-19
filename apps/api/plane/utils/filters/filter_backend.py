# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import json
from operator import and_, or_

from django.db.models import Q
from django.http import QueryDict
from django_filters.filters import BaseCSVFilter, ChoiceFilter
from django_filters.utils import translate_validation
from rest_framework import filters
from rest_framework.exceptions import ValidationError as DRFValidationError

from plane.utils.exception_logger import log_exception


def _invalid(code, message, **details):
    return DRFValidationError({"message": message, "code": code, **details})


class ComplexFilterBackend(filters.BaseFilterBackend):
    """Filter a queryset using a JSON expression. See plane/utils/filters/README.md."""

    filter_param = "filters"
    default_max_depth = 5

    def filter_queryset(self, request, queryset, view, filter_data=None):
        """An explicit filter takes precedence over the filters query parameter."""
        try:
            if filter_data is None:
                raw = request.query_params.get(self.filter_param)
                if not raw:
                    return queryset
                filter_data = self._normalize_filter_data(raw, "filter")
            else:
                filter_data = self._normalize_filter_data(filter_data, "filter_data")
            return self._apply_json_filter(queryset, filter_data, view)
        except DRFValidationError:
            raise
        except Exception as exc:
            log_exception(exc)
            raise

    def _normalize_filter_data(self, raw_filter, source_label):
        if isinstance(raw_filter, dict):
            return raw_filter
        if not isinstance(raw_filter, str):
            raise _invalid("invalid_filter_type", f"'{source_label}' must be a dict or a JSON string.")
        try:
            return json.loads(raw_filter)
        except json.JSONDecodeError:
            raise _invalid("invalid_json", f"Invalid JSON for '{source_label}'. Expected a valid JSON object.")

    def _apply_json_filter(self, queryset, filter_data, view):
        if not filter_data:
            return queryset

        fields = []
        tree = self._validate_structure(filter_data, self._get_max_depth(view), 1, fields)
        self._validate_fields(fields, view)
        combined = self._evaluate_node(tree, view, queryset)
        return queryset if combined is None else queryset.filter(combined)

    def _get_max_depth(self, view):
        value = getattr(view, "complex_filter_max_depth", self.default_max_depth)
        try:
            depth = int(value)
        except Exception:
            return self.default_max_depth
        return depth if depth > 0 else self.default_max_depth

    def _validate_structure(self, node, max_depth, current_depth, fields):
        """Collect leaf keys and normalize logical operators without mutating the input."""
        if current_depth > max_depth:
            raise _invalid(
                "max_depth_exceeded", f"Filter nesting is too deep (max {max_depth}); found depth {current_depth}"
            )
        if not isinstance(node, dict):
            raise _invalid("invalid_filter_node", "Each filter node must be a JSON object")
        if not node:
            raise _invalid("empty_filter_object", "Filter objects must not be empty")

        key = self._operator_key(node)
        if key is None:
            for field, value in node.items():
                self._validate_value(field, value)
            fields.extend(node)
            return node

        op = key.lower()
        value = node[key]
        if op == "not":
            if not isinstance(value, dict):
                raise _invalid("invalid_not_child", "'not' must be a single JSON object")
            return {op: self._validate_structure(value, max_depth, current_depth + 1, fields)}

        return {
            op: [
                self._validate_structure(child, max_depth, current_depth + 1, fields)
                for child in self._operator_children(op, value)
            ]
        }

    def _operator_key(self, node):
        keys = [key for key in node if isinstance(key, str) and key.lower() in ("and", "or", "not")]
        if not keys:
            return None
        if len(keys) > 1:
            raise _invalid(
                "multiple_logical_operators",
                "A filter object cannot contain multiple logical operators at the same level",
            )
        key = keys[0]
        if len(node) != 1:
            raise _invalid(
                "mixed_operator_and_fields", f"Cannot mix logical operator '{key}' with field keys at the same level"
            )
        return key

    def _operator_children(self, op, value):
        if not isinstance(value, list) or not value:
            raise _invalid("invalid_operator_children", f"'{op}' must be a non-empty list of filter objects")
        for child in value:
            if not isinstance(child, dict):
                raise _invalid("invalid_operator_child_type", f"All children of '{op}' must be JSON objects")
            yield child

    def _validate_value(self, key, value):
        if self._is_scalar(value):
            return
        if not isinstance(value, (list, tuple)):
            raise _invalid("invalid_value_type", f"Value for '{key}' must be a scalar, null, or list/tuple of scalars")
        if not value:
            raise _invalid("empty_list_value", f"List value for '{key}' must not be empty")
        if any(not self._is_scalar(item) for item in value):
            raise _invalid("non_scalar_list_item", f"List value for '{key}' must contain only scalar items")

    def _is_scalar(self, value):
        return value is None or isinstance(value, (str, int, float, bool))

    def _validate_fields(self, fields, view):
        filterset_class = getattr(view, "filterset_class", None)
        if not filterset_class or not filterset_class.base_filters:
            raise _invalid(
                "filtering_not_enabled", "Filtering is not enabled for this endpoint (missing filterset_class)"
            )
        for key in fields:
            field = self._transform_field_name_for_validation(key)
            if field not in filterset_class.base_filters:
                raise _invalid("invalid_filter_field", f"Filtering on field '{field}' is not allowed")

    def _transform_field_name_for_validation(self, field_name):
        """Hook for subclasses that expose aliases for declared filters."""
        return field_name

    def _evaluate_node(self, node, view, queryset):
        key, value = next(iter(node.items()))
        if key == "not":
            child = self._evaluate_node(value, view, queryset)
            return ~child if child is not None else None
        if key in ("and", "or"):
            combine = and_ if key == "and" else or_
            combined = Q()
            for child in value:
                condition = self._evaluate_node(child, view, queryset)
                if condition is not None:
                    combined = combine(combined, condition)
            return combined
        return self._build_leaf_q(node, view, queryset)

    def _preprocess_leaf_conditions(self, leaf_conditions, view, queryset):
        """Hook for subclasses that translate field names or values before binding."""
        return leaf_conditions

    def _build_leaf_q(self, leaf_conditions, view, queryset):
        conditions = self._preprocess_leaf_conditions(leaf_conditions, view, queryset)
        filterset_class = view.filterset_class
        data = self._query_data(conditions, filterset_class)
        filterset = filterset_class(data=data, queryset=queryset)
        if not filterset.is_valid():
            raise _invalid(
                "invalid_filterset", "Invalid filter parameters", errors=translate_validation(filterset.errors).detail
            )
        if not hasattr(filterset, "build_combined_q"):
            raise _invalid(
                "missing_build_combined_q", "FilterSet must have build_combined_q method for complex filtering"
            )
        return filterset.build_combined_q()

    def _query_data(self, conditions, filterset_class):
        data = QueryDict(mutable=True)
        for key, value in conditions.items():
            if not isinstance(value, list):
                data[key] = "" if value is None else str(value)
                continue
            field = filterset_class.base_filters.get(key)
            if isinstance(field, BaseCSVFilter):
                data[key] = ",".join(str(item) for item in value)
            elif isinstance(field, ChoiceFilter):
                raise _invalid(
                    "invalid_filterset", "Invalid filter parameters", errors={key: ["Expected a single value."]}
                )
            else:
                data.setlist(key, [str(item) for item in value])
        data._mutable = False
        return data
