# Deliverable 2 — Maintaining Plane's work-item filters

**Zuriel Hernandez · November 18, 2026**

Plane accepts legacy issue filters, evaluates JSON filters on issue lists, and converts older saved filters to the JSON format. This contribution covers the three Python files responsible for those operations. The final run passed all 486 cases, including the 115 that passed before the work started. Five of the added cases exposed two existing faults.

## Starting point and scope

The starting revision was the team's [submitted Deliverable 1 commit][baseline]. It includes the earlier state-group work. A fresh export of that commit kept unrelated working-tree changes and the malformed local Git reference out of the measurements. All 115 tests in the four original files passed, and the branch counts matched the baseline for all three components. [Original test output](evidence/original/pytest.txt)

| Component and reason for selection                                                                                                        | Maintenance problem at the starting revision                                                                                                                                                          |
| ----------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [Legacy issue filters][legacy-code] build lookups for issue lists and saved views.                                                        | 21 functions split comma-separated input. Similar handlers differed in their treatment of empty values, missing relationships, and whether dates were read from a query string or a saved list.       |
| [JSON filter backend][backend-code] evaluates expressions used by issue, cycle, module, and saved-view endpoints.                         | Structure validation reached complexity 17. Evaluation reached 15 and had separate loops for AND and OR. Validation and evaluation also disagreed about operator case.                                |
| [Saved-filter converter][converter-code] builds conditions for existing views and is imported by the [saved-filter migration][migration]. | Date conversion reached complexity 22. The main conversion method reached 17 and repeated date handling for scalar and list inputs. The original suite executed none of the converter's 104 branches. |

## Tests and behavior decisions

The expanded suite added 371 cases. The legacy tests exercise the public filter function with GET strings and saved-view lists. They check exact lookup keys, prefixes, null tokens, deleted relationships, and dates against a fixed clock. The backend unit tests check validation and filter binding without a database. The API tests use an authenticated client, four work items, and exact result sets. One API case converts a saved filter and sends its output to the real issue-list endpoint. The converter tests also cover custom mappings, strict and permissive errors, and preservation of input data.

1. **Use the intake status supplied by the caller.** Sending `{"intake_status": [0, 1]}` on POST or PATCH produced an inclusion lookup with the value `None`. The handler checked `intake_status` and then read `inbox_status`. It now uses the supplied list. The older spelling still works and keeps its precedence when both have values. [Legacy tests][legacy-tests]
2. **Apply the documented case-insensitive operators.** The original API accepted `AND`, `oR`, and `Not`, but returned all four sample issues in each case. For example, high priority AND started should return only _Prototype_. Validation now normalizes operator keys once, so evaluation uses the validated operation. Field names retain their original case. [API tests][api-tests]

## Modernization and changeability

| Component      | Refactoring decision                                                                                                                                                                                    | Source lines before → after | Highest function complexity before → after | Total decisions before → after |
| -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------: | -----------------------------------------: | -----------------------------: |
| Legacy filters | Kept the named handlers and moved ID, value-list, and date handling into shared functions. Relative dates calculate one offset and then apply the requested bound.                                      |                   395 → 212 |                                     10 → 8 |                       184 → 43 |
| JSON backend   | Structure validation collects leaf names while normalizing operators. The backend checks those names against the view's FilterSet, combines AND/OR children with one loop, and binds leaves separately. |                   303 → 172 |                                     17 → 9 |                        73 → 54 |
| Converter      | Separated field selection, list validation, date classification, and construction of exact/range output. The public conversion method collects strict-mode errors in input order.                       |                   240 → 181 |                                    22 → 10 |                        71 → 54 |

Legacy CSV splitting now occurs in **two functions**. The date parser retains empty tokens because they affect the whole date filter. The list parser discards the literal `"null"`, and individual field rules determine what to do with empty entries. Keeping those rules distinct preserves both behaviors. The JSON evaluator's complexity fell from 15 to 7. In the converter, date conversion fell from 22 to 8 and the public `convert` method from 17 to 9. The remaining maximum of 10 belongs to the existing configuration constructor.

Radon 6.0.1 measured every function and method in each selected file, including new helpers. Total decisions are the sum of each function's complexity minus one. Excluding that entry point per function makes it possible to see whether extraction merely moved decisions. The CSV count identifies functions that call `split(",")` directly. These measures describe the code a maintainer must reason about. They do not measure time spent on a future change. [Measurement script](evidence/measure.py) · [Original scores](evidence/original/complexity.json) · [Final scores](evidence/final/complexity.json)

## Coverage and regression results

Statement and branch counts show what the selected tests exercised. The expanded baseline isolates the effect of adding tests. Its production files have the same hashes and complexity scores as the original baseline. The final run uses byte-identical copies of all seven expanded test files. [Run manifest and hashes](evidence/manifest.json)

| Component      | Measurement | Original 115 tests | Expanded tests on original code | Same tests after modernization |
| -------------- | ----------- | -----------------: | ------------------------------: | -----------------------------: |
| Legacy filters | Statements  |    73/287 (25.44%) |                  287/287 (100%) |               158/159 (99.37%) |
|                | Branches    |    20/188 (10.64%) |                187/188 (99.47%) |                 57/58 (98.28%) |
| JSON backend   | Statements  |   146/188 (77.66%) |                172/188 (91.49%) |               147/150 (98.00%) |
|                | Branches    |    79/116 (68.10%) |                100/116 (86.21%) |                 73/75 (97.33%) |
| Converter      | Statements  |    29/183 (15.85%) |                176/183 (96.17%) |               139/141 (98.58%) |
|                | Branches    |         0/104 (0%) |                 96/104 (92.31%) |                 76/78 (97.44%) |

The legacy module had one unexercised branch both before and after refactoring with the expanded suite. Its percentage changed because consolidation reduced the denominator from 188 to 58. In the final code the gap is the fallback for an unsupported relative-date unit. Remaining backend gaps include unexpected-exception logging and a child returning no condition. The converter's remaining two branches handle Python date-validator inputs outside the saved date strings used here. [Original](evidence/original/coverage.json) · [Expanded](evidence/expanded/coverage.json) · [Final coverage](evidence/final/coverage.json)

| Production state                                                  | Passed | Failed | Skipped | What the run showed                                          |
| ----------------------------------------------------------------- | -----: | -----: | ------: | ------------------------------------------------------------ |
| [Original revision, original tests](evidence/original/pytest.txt) |    115 |      0 |       0 | Starting regression result reproduced.                       |
| [Original revision, expanded tests](evidence/expanded/pytest.txt) |    481 |      5 |       0 | Two intake-status failures and three operator-case failures. |
| [After legacy refactoring](evidence/legacy/pytest.txt)            |    483 |      3 |       0 | Both intake-status cases passed.                             |
| [After JSON backend refactoring](evidence/backend/pytest.txt)     |    486 |      0 |       0 | All three operator cases returned the expected issues.       |
| [After converter refactoring](evidence/final/pytest.txt)          |    486 |      0 |       0 | The same tests passed with all three changes present.        |

All 115 original case IDs passed at every stage. The coverage tool counts branches executed by a failing test, which is why the assertion results matter alongside the percentages. The stability assessment applies to the seven listed test files. The runs used `--nomigrations`, so they establish converter behavior and API compatibility but do not exercise a database migration. Ruff 0.9.7 lint and formatting checks passed on the changed Python files.

## Documentation and traceability

I updated the filter guide and added the commands I used to run the tests and check coverage. [Filter guide][filter-guide] · [Test commands][run-guide]

| Local task                                                    | Implementation and tests                                                                                 | Test results                                        | Version control                                            |
| ------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------- | --------------------------------------------------- | ---------------------------------------------------------- |
| Consolidate legacy parsing and correct saved intake values    | [Implementation][legacy-code] · [Unit tests][legacy-tests] · [Existing endpoint regression][state-tests] | [Post-change test run](evidence/legacy/pytest.txt)  | [Baseline e4f4bd7][baseline] · [8b3bf60][legacy-commit]    |
| Simplify nested filtering and fix mixed-case filter operators | [Implementation][backend-code] · [Unit tests][backend-tests] · [API tests][api-tests]                    | [Post-change test run](evidence/backend/pytest.txt) | [Baseline e4f4bd7][baseline] · [9000cd6][backend-commit]   |
| Separate date conversion and preserve saved-filter output     | [Implementation][converter-code] · [Unit tests][converter-tests] · [API round trip][api-tests]           | [Final test run](evidence/final/pytest.txt)         | [Baseline e4f4bd7][baseline] · [d755e94][converter-commit] |

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
[state-tests]: ../../../apps/api/plane/tests/contract/app/test_issue_state_group_filters.py
[run-guide]: ../../../apps/api/tests/RUNNING_TESTS.md
[filter-guide]: ../../../apps/api/plane/utils/filters/README.md
