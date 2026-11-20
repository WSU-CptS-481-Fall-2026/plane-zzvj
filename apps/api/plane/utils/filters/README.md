# Filtering work items

Pass `priority=low` as a query parameter, or send JSON in `filters`. If you use both, an issue has to match both.

## Legacy parameters

- ID filters like `state` and `labels` take comma-separated UUIDs on GET and lists on POST or PATCH. GET skips bad UUIDs, blanks, and `null`.
- `labels=None` finds issues without labels. `None` also works for parent, assignees, creators, loggers, cycles, and modules. If you include a UUID, both checks apply.
- On GET, `priority=high,null` filters by high priority. `priority=high,` skips the filter. `estimate_point` and `intake_status` handle blanks and `null` the same way.
- On POST or PATCH, send `{"intake_status": [0, 1]}`. The older `inbox_status` wins if both have values. An empty `inbox_status` leaves `intake_status` alone.

On GET, `2026-11-01;after` means November 1 onward. `before` includes its end date too. A bare date uses `contains`. `2_weeks;after;fromnow` starts two weeks from today. Months count as 30 days. On POST or PATCH, pass a list for timestamps and a direct value for `start_date` or `target_date`.

## JSON expressions

This `filters` value skips an issue if its priority is `high` or its state group is `completed`.

```json
{ "not": { "or": [{ "priority": "high" }, { "state_group": "completed" }] } }
```

Use `and` or `or` with a nonempty list of objects, and `not` with one object. Keep each operator in its own object. Operator names ignore case. Two fields in one object must both match.

Use field names exactly as the view defines them. `state_group` takes one value. For several, use `state_group__in` with a list or a comma-separated string.

The default limit is five levels, counting the outer object. A view can set a positive `complex_filter_max_depth` to change it. If you get a 400, `invalid_filter_field` points to an unknown field and `invalid_filterset` gives the field errors.

In Python, `filter_data` overrides the query parameter. Pass a dict or a JSON string. `{}` adds no filter.

## Converting saved filters

`LegacyToRichFiltersConverter.convert` turns `{"priority": ["high", "low"]}` into `{"priority__in": "high,low"}`. `{"priority": "low"}` uses `priority__exact`. Multiple fields are joined with `and`.

The converter skips unknown fields and bad values by default. Use `strict=True` to get the errors in one `ValueError`.

A saved date can be a single date (`__exact`) or an `after` and `before` pair (`__range`). The converter skips relative dates and one-sided ranges in both modes.

[Run the filter tests](../../../tests/RUNNING_TESTS.md#deliverable-2-filtering-regression-suite).
