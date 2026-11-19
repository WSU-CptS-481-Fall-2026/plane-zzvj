# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import re
import uuid
from datetime import datetime
from typing import Any, Dict, List, Union

from dateutil.parser import parse as dateutil_parse


class LegacyToRichFiltersConverter:
    # Default mapping from legacy filter names to new rich filter field names
    DEFAULT_FIELD_MAPPINGS = {
        "state": "state_id",
        "labels": "label_id",
        "cycle": "cycle_id",
        "module": "module_id",
        "assignees": "assignee_id",
        "mentions": "mention_id",
        "created_by": "created_by_id",
        "state_group": "state_group",
        "priority": "priority",
        "project": "project_id",
        "start_date": "start_date",
        "target_date": "target_date",
    }

    # Default fields that expect UUID values
    DEFAULT_UUID_FIELDS = {
        "state_id",
        "label_id",
        "cycle_id",
        "module_id",
        "assignee_id",
        "mention_id",
        "created_by_id",
        "project_id",
    }

    # Default valid choices for choice fields
    DEFAULT_VALID_CHOICES = {
        "state_group": ["backlog", "unstarted", "started", "completed", "cancelled"],
        "priority": ["urgent", "high", "medium", "low", "none"],
    }

    # Default date fields
    DEFAULT_DATE_FIELDS = {"start_date", "target_date"}

    # Pattern for relative date strings like "2_weeks" or "3_months"
    DATE_PATTERN = re.compile(r"(\d+)_(weeks|months)$")

    def __init__(
        self,
        field_mappings: Dict[str, str] = None,
        uuid_fields: set = None,
        valid_choices: Dict[str, List[str]] = None,
        date_fields: set = None,
        extend_defaults: bool = True,
    ):
        """
        Initialize the converter with optional custom configurations.

        Args:
            field_mappings: Custom field mappings (legacy_key -> rich_field_name)
            uuid_fields: Set of field names that should be validated as UUIDs
            valid_choices: Dict of valid choices for choice fields
            date_fields: Set of field names that should be treated as dates
            extend_defaults: If True, merge with defaults; if False, replace defaults

        Examples:
            # Use defaults
            converter = LegacyToRichFiltersConverter()

            # Add custom field mapping
            converter = LegacyToRichFiltersConverter(
                field_mappings={"custom_field": "custom_field_id"}
            )

            # Override priority choices
            converter = LegacyToRichFiltersConverter(
                valid_choices={"priority": ["critical", "high", "medium", "low"]}
            )

            # Complete replacement (not extending defaults)
            converter = LegacyToRichFiltersConverter(
                field_mappings={"state": "status_id"},
                extend_defaults=False
            )
        """
        if extend_defaults:
            # Merge with defaults
            self.FIELD_MAPPINGS = {**self.DEFAULT_FIELD_MAPPINGS}
            if field_mappings:
                self.FIELD_MAPPINGS.update(field_mappings)

            self.UUID_FIELDS = {*self.DEFAULT_UUID_FIELDS}
            if uuid_fields:
                self.UUID_FIELDS.update(uuid_fields)

            self.VALID_CHOICES = {**self.DEFAULT_VALID_CHOICES}
            if valid_choices:
                self.VALID_CHOICES.update(valid_choices)

            self.DATE_FIELDS = {*self.DEFAULT_DATE_FIELDS}
            if date_fields:
                self.DATE_FIELDS.update(date_fields)
        else:
            # Replace defaults entirely
            self.FIELD_MAPPINGS = field_mappings or {}
            self.UUID_FIELDS = uuid_fields or set()
            self.VALID_CHOICES = valid_choices or {}
            self.DATE_FIELDS = date_fields or set()

    def add_field_mapping(self, legacy_key: str, rich_field_name: str) -> None:
        """Add or update a single field mapping."""
        self.FIELD_MAPPINGS[legacy_key] = rich_field_name

    def add_uuid_field(self, field_name: str) -> None:
        """Add a field that should be validated as UUID."""
        self.UUID_FIELDS.add(field_name)

    def add_choice_field(self, field_name: str, choices: List[str]) -> None:
        """Add or update valid choices for a choice field."""
        self.VALID_CHOICES[field_name] = choices

    def add_date_field(self, field_name: str) -> None:
        """Add a field that should be treated as a date field."""
        self.DATE_FIELDS.add(field_name)

    def update_mappings(
        self,
        field_mappings: Dict[str, str] = None,
        uuid_fields: set = None,
        valid_choices: Dict[str, List[str]] = None,
        date_fields: set = None,
    ) -> None:
        """
        Update multiple configurations at once.

        Args:
            field_mappings: Additional field mappings to add/update
            uuid_fields: Additional UUID fields to add
            valid_choices: Additional choice fields to add/update
            date_fields: Additional date fields to add
        """
        if field_mappings:
            self.FIELD_MAPPINGS.update(field_mappings)
        if uuid_fields:
            self.UUID_FIELDS.update(uuid_fields)
        if valid_choices:
            self.VALID_CHOICES.update(valid_choices)
        if date_fields:
            self.DATE_FIELDS.update(date_fields)

    def _validate_uuid(self, value: str) -> bool:
        """Validate if a string is a valid UUID"""
        try:
            uuid.UUID(str(value))
            return True
        except (ValueError, TypeError):
            return False

    def _validate_date(self, value: Union[str, datetime]) -> bool:
        """Validate if a value is a valid date using dateutil parser"""
        if isinstance(value, datetime):
            return True
        if isinstance(value, str):
            try:
                # Use dateutil for flexible date parsing
                dateutil_parse(value)
                return True
            except (ValueError, TypeError):
                return False
        return False

    def _validate_value(self, field: str, value: Any) -> bool:
        if field in self.UUID_FIELDS:
            return self._validate_uuid(value)
        if field in self.VALID_CHOICES:
            return value in self.VALID_CHOICES[field]
        return True

    def _date_condition(self, parts, strict):
        date = parts[0]
        if not self._validate_date(date):
            if strict:
                raise ValueError(f"Invalid date format: {date}")
            return None
        if len(parts) == 1:
            return "exact", date
        if parts[1] in ("after", "before"):
            return parts[1], date
        return None

    def _format_date_conditions(self, field, conditions):
        if len(conditions) == 1 and conditions[0][0] == "exact":
            return {f"{field}__exact": conditions[0][1]}
        if {kind for kind, _ in conditions} == {"after", "before"}:
            bounds = sorted(value for _, value in conditions)
            return {f"{field}__range": ",".join(bounds)}
        return {}

    def _convert_date_value(self, field_name: str, values: List[str], strict: bool = False) -> Dict[str, Any]:
        """Convert an exact date or two bounds. Relative expressions omit the whole field."""
        expressions = []
        for value in values:
            parts = value.split(";") if ";" in value else [value]
            if len(parts) > 1 and self.DATE_PATTERN.match(parts[0]):
                return {}
            expressions.append(parts)
        if len(expressions) > 2:
            return {}

        conditions = []
        for parts in expressions:
            condition = self._date_condition(parts, strict)
            if condition is not None:
                conditions.append(condition)
        return self._format_date_conditions(field_name, conditions)

    def _convert_list(self, key, field, values, strict):
        valid = []
        invalid = []
        for value in values:
            if self._validate_value(field, value):
                valid.append(value)
            else:
                invalid.append(value)
        if not valid:
            raise ValueError(f"No valid values found for {key}: {values}")
        if strict and invalid:
            raise ValueError(f"Invalid values for {key}: {invalid}")
        return {f"{field}__in": ",".join(str(value) for value in valid)}

    def _convert_field(self, key, value, strict):
        if key not in self.FIELD_MAPPINGS:
            raise ValueError(f"Unsupported filter key: {key}")
        field = self.FIELD_MAPPINGS[key]
        if field in self.DATE_FIELDS:
            values = value if isinstance(value, list) else [value]
            return self._convert_date_value(field, values, strict)
        if isinstance(value, list):
            return self._convert_list(key, field, value, strict)
        if not self._validate_value(field, value):
            raise ValueError(f"Invalid value for {key}: {value}")
        return {f"{field}__exact": value}

    def convert(self, legacy_filters: dict, strict: bool = False) -> Dict[str, Any]:
        """Convert saved filters, optionally reporting all field errors in input order."""
        rich_filters = {}
        errors = []
        for key, value in legacy_filters.items():
            if value is None or value == []:
                continue
            try:
                rich_filters.update(self._convert_field(key, value, strict))
            except ValueError as exc:
                if strict:
                    errors.append(str(exc))

        if errors:
            raise ValueError(f"Filter validation errors: {'; '.join(errors)}")
        if len(rich_filters) <= 1:
            return rich_filters
        return {"and": [{field: value} for field, value in rich_filters.items()]}
