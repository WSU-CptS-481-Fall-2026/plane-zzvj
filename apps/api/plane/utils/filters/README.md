# Filtering work items

The issue list accepts legacy query parameters and a JSON expression in the `filters` parameter. If a request supplies both, a work item must satisfy both. Saved views can also pass a legacy filter dictionary to the converter.

## Legacy parameters

- On GET, `state`, `labels`, `assignees`, and the other ID filters read comma-separated UUIDs. They discard invalid IDs, empty entries, and the literal `"null"`. The corresponding non-GET callers pass their lists through.
- For parent, labels, assignees, creators, loggers, cycles, and modules, the GET token `"None"` adds an `__isnull` condition. If the list also contains a valid UUID, it retains both conditions. Labels, assignees, cycles, modules, and subscribers keep their condition excluding deleted links. A caller's prefix applies to every generated lookup.
- GET ignores `"null"` for `priority`, `estimate_point`, and `intake_status`. An empty entry skips that filter, so `priority=high,` leaves priority unfiltered.
- On POST or PATCH, send `intake_status` as a list like `[0, 1]`. The older `inbox_status` wins if both have values.
- For GET dates, a bare date uses the legacy `contains` lookup. `2026-11-01;after` and `2026-11-30;before` set inclusive bounds. Relative expressions such as `2_weeks;after;fromnow` or `2_months;before;ago` use seven-day weeks and thirty-day months. On non-GET requests, timestamps accept a list of date expressions, while `start_date` and `target_date` take direct values.

## JSON expressions

This filter selects low-priority work items that are either started or completed.

```json
{
  "and": [{ "priority": "low" }, { "or": [{ "state_group": "started" }, { "state_group": "completed" }] }]
}
```

The API reads a JSON string in `filters`. A Python caller can also pass a dictionary or JSON string as `filter_data` to `ComplexFilterBackend.filter_queryset`. Explicit input takes precedence. An absent filter or an empty top-level object leaves the queryset unchanged.

| Expression     | Rule                                                                                                                                                                                                                  |
| -------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `and`, `or`    | Each takes a nonempty list of objects.                                                                                                                                                                                |
| `not`          | Takes one object, for example `{"not": {"priority": "high"}}`.                                                                                                                                                        |
| Operator names | Case-insensitive. A node can contain one operator and no field keys alongside it.                                                                                                                                     |
| Leaf fields    | Keys must match filters declared by the view, including lookup suffixes. Multiple keys in one leaf are joined with AND. Field names are case-sensitive.                                                               |
| Lists and null | CSV filters such as `state_group__in` accept an array or CSV string. A single-choice filter such as `state_group` takes one value. JSON null binds as an empty form value, whose meaning is determined by that field. |
| Depth          | The root is at depth 1. The default maximum is 5. A view can set a positive `complex_filter_max_depth`. Invalid or nonpositive settings use the default.                                                              |

Validation checks the tree's shape, the view's allowed fields, and then the filter values. A malformed JSON string returns HTTP 400 with `invalid_json`. An unknown field returns `invalid_filter_field`, an invalid choice returns `invalid_filterset` with field details, and a tree over the depth limit returns `max_depth_exceeded`.

## Converting saved filters

`LegacyToRichFiltersConverter.convert` maps legacy keys to the fields used by the JSON backend. A scalar becomes `__exact`, a list of ordinary values becomes a CSV `__in` condition, and multiple conditions are joined with `and`. For example, a saved `{"state_group": ["started", "completed"], "priority": "low"}` selects the same issues as the JSON example above.

The default mode retains valid values and omits unsupported fields or invalid entries. With `strict=True`, the converter collects field errors and raises one `ValueError`. Custom mappings and validators can extend or replace the defaults.

A single supported date becomes `__exact`. One `after` and one `before` bound become a CSV `__range`. Relative expressions and unsupported combinations, including one-sided ranges, are omitted in both modes. This preserves the behavior used by the saved-filter migration.

The [unit and API test commands](../../../tests/RUNNING_TESTS.md) exercise these rules.
