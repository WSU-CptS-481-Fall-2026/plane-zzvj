# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import re
import uuid
from datetime import timedelta

from django.utils import timezone
from rest_framework.exceptions import ValidationError
from rest_framework.fields import ChoiceField, ListField

from plane.db.models.state import StateGroup

# The date from pattern
pattern = re.compile(r"\d+_(weeks|months)$")


# check the valid uuids
def filter_valid_uuids(uuid_list):
    valid_uuids = []
    for uuid_str in uuid_list:
        try:
            uuid_obj = uuid.UUID(uuid_str)
            valid_uuids.append(uuid_obj)
        except ValueError:
            # ignore the invalid uuids
            pass
    return valid_uuids


def string_date_filter(issue_filter, duration, subsequent, term, date_filter, offset):
    if term == "weeks":
        delta = timedelta(weeks=duration)
    elif term == "months":
        delta = timedelta(days=30 * duration)
    else:
        return

    lookup = "gte" if subsequent == "after" else "lte"
    if offset != "fromnow":
        delta = -delta
    issue_filter[f"{date_filter}__{lookup}"] = timezone.now().date() + delta


def date_filter(issue_filter, date_term, queries):
    """Add the lookup for each bare, absolute, or relative date expression."""
    for query in queries:
        parts = query.split(";")
        value = parts[0]
        if len(parts) == 1:
            issue_filter[f"{date_term}__contains"] = value
        elif pattern.match(value):
            if len(parts) == 3:
                duration, term = value.split("_")
                string_date_filter(issue_filter, int(duration), parts[1], term, date_term, parts[2])
        else:
            lookup = "gte" if "after" in parts else "lte"
            issue_filter[f"{date_term}__{lookup}"] = value


def _csv_values(raw):
    return [item for item in raw.split(",") if item != "null"]


def _has_list_value(value):
    return bool(value) and len(value) > 0 and value != "null"


def _filter_ids(params, issue_filter, method, prefix, field, lookup, *, allow_none=False, relation=None):
    key = f"{prefix}{lookup}"
    value = params.get(field)
    if method == "GET":
        items = _csv_values(value)
        if allow_none and "None" in items:
            issue_filter[f"{key}__isnull"] = True
        value = filter_valid_uuids(items)
    if _has_list_value(value):
        issue_filter[f"{key}__in"] = value
    if relation:
        issue_filter[f"{prefix}{relation}__deleted_at__isnull"] = True
    return issue_filter


def _filter_values(params, issue_filter, method, prefix, field, lookup):
    value = params.get(field)
    if method == "GET":
        value = _csv_values(value)
        if "" in value:
            return issue_filter
    if _has_list_value(value):
        issue_filter[f"{prefix}{lookup}__in"] = value
    return issue_filter


def _filter_date_field(params, issue_filter, method, prefix, field, *, timestamp=False):
    value = params.get(field)
    lookup = f"{prefix}{field}__date" if timestamp else f"{prefix}{field}"
    if method == "GET":
        queries = value.split(",")
        if "" not in queries:
            date_filter(issue_filter, lookup, queries)
    elif value and len(value):
        if timestamp:
            date_filter(issue_filter, lookup, value)
        else:
            issue_filter[lookup] = value
    return issue_filter


def filter_state(params, issue_filter, method, prefix=""):
    return _filter_ids(params, issue_filter, method, prefix, "state", "state")


def filter_state_group(params, issue_filter, method, prefix=""):
    state_group = params.get("state_group")
    if not state_group or state_group == "null":
        return issue_filter

    if method == "GET":
        state_group = [item for item in _csv_values(state_group) if item]

    try:
        state_group = ListField(child=ChoiceField(choices=StateGroup.choices)).run_validation(state_group)
    except ValidationError as exc:
        raise ValidationError({"state_group": exc.detail}) from exc

    if state_group:
        issue_filter[f"{prefix}state__group__in"] = state_group
    return issue_filter


def filter_estimate_point(params, issue_filter, method, prefix=""):
    return _filter_values(params, issue_filter, method, prefix, "estimate_point", "estimate_point")


def filter_priority(params, issue_filter, method, prefix=""):
    return _filter_values(params, issue_filter, method, prefix, "priority", "priority")


def filter_parent(params, issue_filter, method, prefix=""):
    return _filter_ids(params, issue_filter, method, prefix, "parent", "parent", allow_none=True)


def filter_labels(params, issue_filter, method, prefix=""):
    return _filter_ids(
        params, issue_filter, method, prefix, "labels", "labels", allow_none=True, relation="label_issue"
    )


def filter_assignees(params, issue_filter, method, prefix=""):
    return _filter_ids(
        params, issue_filter, method, prefix, "assignees", "assignees", allow_none=True, relation="issue_assignee"
    )


def filter_mentions(params, issue_filter, method, prefix=""):
    return _filter_ids(params, issue_filter, method, prefix, "mentions", "issue_mention__mention__id")


def filter_created_by(params, issue_filter, method, prefix=""):
    return _filter_ids(params, issue_filter, method, prefix, "created_by", "created_by", allow_none=True)


def filter_name(params, issue_filter, method, prefix=""):
    if params.get("name", "") != "":
        issue_filter[f"{prefix}name__icontains"] = params.get("name")
    return issue_filter


def filter_created_at(params, issue_filter, method, prefix=""):
    return _filter_date_field(params, issue_filter, method, prefix, "created_at", timestamp=True)


def filter_updated_at(params, issue_filter, method, prefix=""):
    return _filter_date_field(params, issue_filter, method, prefix, "updated_at", timestamp=True)


def filter_start_date(params, issue_filter, method, prefix=""):
    return _filter_date_field(params, issue_filter, method, prefix, "start_date")


def filter_target_date(params, issue_filter, method, prefix=""):
    return _filter_date_field(params, issue_filter, method, prefix, "target_date")


def filter_completed_at(params, issue_filter, method, prefix=""):
    return _filter_date_field(params, issue_filter, method, prefix, "completed_at", timestamp=True)


def filter_issue_state_type(params, issue_filter, method, prefix=""):
    type = params.get("type", "all")
    group = ["backlog", "unstarted", "started", "completed", "cancelled"]
    if type == "backlog":
        group = ["backlog"]
    if type == "active":
        group = ["unstarted", "started"]

    issue_filter[f"{prefix}state__group__in"] = group
    return issue_filter


def filter_project(params, issue_filter, method, prefix=""):
    return _filter_ids(params, issue_filter, method, prefix, "project", "project")


def filter_cycle(params, issue_filter, method, prefix=""):
    return _filter_ids(
        params, issue_filter, method, prefix, "cycle", "issue_cycle__cycle_id", allow_none=True, relation="issue_cycle"
    )


def filter_module(params, issue_filter, method, prefix=""):
    return _filter_ids(
        params,
        issue_filter,
        method,
        prefix,
        "module",
        "issue_module__module_id",
        allow_none=True,
        relation="issue_module",
    )


def filter_intake_status(params, issue_filter, method, prefix=""):
    return _filter_values(params, issue_filter, method, prefix, "intake_status", "issue_intake__status")


def filter_inbox_status(params, issue_filter, method, prefix=""):
    return _filter_values(params, issue_filter, method, prefix, "inbox_status", "issue_intake__status")


def filter_sub_issue_toggle(params, issue_filter, method, prefix=""):
    if params.get("sub_issue", "false") == "false":
        issue_filter[f"{prefix}parent__isnull"] = True
    return issue_filter


def filter_subscribed_issues(params, issue_filter, method, prefix=""):
    return _filter_ids(
        params,
        issue_filter,
        method,
        prefix,
        "subscriber",
        "issue_subscribers__subscriber_id",
        relation="issue_subscribers",
    )


def filter_start_target_date_issues(params, issue_filter, method, prefix=""):
    start_target_date = params.get("start_target_date", "false")
    if start_target_date == "true":
        issue_filter[f"{prefix}target_date__isnull"] = False
        issue_filter[f"{prefix}start_date__isnull"] = False
    return issue_filter


def filter_logged_by(params, issue_filter, method, prefix=""):
    return _filter_ids(params, issue_filter, method, prefix, "logged_by", "logged_by", allow_none=True)


_FILTER_HANDLERS = {
    "state": filter_state,
    "state_group": filter_state_group,
    "estimate_point": filter_estimate_point,
    "priority": filter_priority,
    "parent": filter_parent,
    "labels": filter_labels,
    "assignees": filter_assignees,
    "mentions": filter_mentions,
    "created_by": filter_created_by,
    "logged_by": filter_logged_by,
    "name": filter_name,
    "created_at": filter_created_at,
    "updated_at": filter_updated_at,
    "start_date": filter_start_date,
    "target_date": filter_target_date,
    "completed_at": filter_completed_at,
    "type": filter_issue_state_type,
    "project": filter_project,
    "cycle": filter_cycle,
    "module": filter_module,
    "intake_status": filter_intake_status,
    "inbox_status": filter_inbox_status,
    "sub_issue": filter_sub_issue_toggle,
    "subscriber": filter_subscribed_issues,
    "start_target_date": filter_start_target_date_issues,
}


def issue_filters(query_params, method, prefix=""):
    issue_filter = {}
    for key, apply_filter in _FILTER_HANDLERS.items():
        if key in query_params:
            apply_filter(query_params, issue_filter, method, prefix)
    return issue_filter
