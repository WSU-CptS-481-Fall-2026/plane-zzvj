# Deliverable 2 — Maintaining Plane's work-item filters

**Zuriel Hernandez · November 19, 2026**

I worked on three backend files in Plane. They read filter parameters, apply nested filters to issue lists, and convert filters from older saved views. I started from my Deliverable 1 commit. [Starting commit e4f4bd7][baseline]

## Changeability

I used Radon to find the function with the most decision paths in each file. The scores below show how that maximum changed after the refactor. [Measurement script](evidence/measure.py) · [Before](evidence/original/complexity.json) · [After](evidence/final/complexity.json)

- `issue_filters.py` (10 to 8). I found 21 functions splitting comma-separated values. Two helpers now do that work. Dates need their own helper because an empty entry affects the whole date filter.
- `filter_backend.py` (17 to 9). `AND` and `OR` had separate loops that both visited each child filter. I combined them so the operator only controls how the results are joined.
- `converters.py` (22 to 10). The saved-view migration uses this code to convert dates. I put single dates and date lists through the same checks, then handled exact dates and ranges separately. [Saved-filter migration][migration]

## Testability

I added 371 cases for query strings, saved filter values, and nested filters. For example, I checked that the converter skips an invalid field by default and reports it in strict mode. One API test converts a saved filter and checks the names of the issues it returns.

I ran the 115 original cases and the 371 new ones together to compare branch coverage before and after the refactor. I added three intake status cases later, for 374 new cases in total.

| Branch coverage        | Original 115 tests | All 486 before refactoring | All 486 after refactoring |
| ---------------------- | -----------------: | -------------------------: | ------------------------: |
| Legacy filters         |             10.64% |                     99.47% |                    98.28% |
| JSON backend           |             68.10% |                     86.21% |                    97.33% |
| Saved-filter converter |                 0% |                     92.31% |                    97.44% |

The legacy tests missed one branch in both 486-case runs. The percentage dipped because the refactor took the file from 188 branches to 58. [Original coverage](evidence/original/coverage.json) · [With the added tests](evidence/expanded/coverage.json) · [Final coverage](evidence/final/coverage.json)

## Stability

All 115 original cases passed at every step. When I ran the larger suite on the old code, 481 passed and five failed. I traced those failures to two bugs. [Original run](evidence/original/pytest.txt) · [Run with the added tests](evidence/expanded/pytest.txt)

- Two cases sent `intake_status` with the values `[0, 1]`. The handler read `inbox_status` instead and got `None` on both POST and PATCH. I fixed it to use the supplied values.
- Three API cases used `AND`, `oR`, and `Not`. In the `AND` case, I asked for high-priority issues in the started state. I expected just _Prototype_ and got all four issues. I fixed the backend to handle capitalization when it reads the operator.

After the intake fix, 483 cases passed. All 486 passed after the operator fix and again after the converter refactor. I ran these seven test files with database migrations disabled. [Intake fix](evidence/legacy/pytest.txt) · [Operator fix](evidence/backend/pytest.txt) · [486-case run](evidence/final/pytest.txt)

I checked what happens when a request sends both intake status names. On POST, an empty `inbox_status` keeps the `intake_status` value. On GET, `inbox_status=1` overrides `intake_status=0`, but `inbox_status=1,` keeps `0`. All 489 cases passed across the same seven files.

## Documentation

I added examples of filter requests and wrote down how to run the seven test files with coverage. [Filter guide][filter-guide] · [Test commands][run-guide] · [Recorded runs](evidence/manifest.json)

| Change                                             | Commit                      | Tests                                                                           |
| -------------------------------------------------- | --------------------------- | ------------------------------------------------------------------------------- |
| [Legacy parsing and intake status][legacy-code] | [8b3bf60][legacy-commit] (parsing), `661da92` (build the handler table once), `8300b93` (POST test), `f65a669` (GET tests) | [Unit tests][legacy-tests] · [State-group API tests][state-tests] |
| [Nested filters and operator case][backend-code]   | [9000cd6][backend-commit]   | [Unit tests][backend-tests] · [Issue-list API tests][api-tests]                 |
| [Dates and lists in saved filters][converter-code] | [d755e94][converter-commit] | [Converter tests][converter-tests] · [Saved filter API test][saved-filter-test] |

[baseline]: https://github.com/WSU-CptS-481-Fall-2026/plane-zzvj/commit/e4f4bd728200c0ae7336e50b68d634ede919feae
[legacy-commit]: https://github.com/WSU-CptS-481-Fall-2026/plane-zzvj/commit/8b3bf60ceaa608a33dec8e41163603358e8d9286
[backend-commit]: https://github.com/WSU-CptS-481-Fall-2026/plane-zzvj/commit/9000cd699c9e99114b746376bf5884e42b312487
[converter-commit]: https://github.com/WSU-CptS-481-Fall-2026/plane-zzvj/commit/d755e9402f0ffbd66e7804f11d8c56bcb9ec2200
[legacy-code]: ../../../apps/api/plane/utils/issue_filters.py
[backend-code]: ../../../apps/api/plane/utils/filters/filter_backend.py
[converter-code]: ../../../apps/api/plane/utils/filters/converters.py
[migration]: ../../../apps/api/plane/db/migrations/0107_migrate_filters_to_rich_filters.py
[legacy-tests]: ../../../apps/api/plane/tests/unit/utils/test_issue_filters.py
[backend-tests]: ../../../apps/api/plane/tests/unit/utils/test_filter_backend.py
[converter-tests]: ../../../apps/api/plane/tests/unit/utils/test_filter_converters.py
[api-tests]: ../../../apps/api/plane/tests/contract/app/test_issue_complex_filters.py
[saved-filter-test]: ../../../apps/api/plane/tests/contract/app/test_issue_complex_filters.py#L72
[state-tests]: ../../../apps/api/plane/tests/contract/app/test_issue_state_group_filters.py
[run-guide]: ../../../apps/api/tests/RUNNING_TESTS.md#deliverable-2-filtering-regression-suite
[filter-guide]: ../../../apps/api/plane/utils/filters/README.md
