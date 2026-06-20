# Placement Cell test suite

Reliable, self-contained tests for the `placement_cell` API module.

## Running

Tests use a dedicated settings module (`FusionIIIT/test_settings.py`) that
disables migrations so the test database is built directly from the current
models. This is required because the project's historical migration chain does
not apply on a fresh database (e.g. `programme_curriculum.0026`), which would
otherwise break test-DB creation for reasons unrelated to placement.

List the modules explicitly — `applications/` has no `__init__.py`, so unittest
package/app-level discovery (`manage.py test applications.placement_cell`) fails
project-wide:

```bash
cd FusionIIIT
python manage.py test \
    applications.placement_cell.tests.test_placement_api \
    applications.placement_cell.tests.test_use_cases \
    applications.placement_cell.tests.test_business_rules \
    applications.placement_cell.tests.test_workflows \
    applications.placement_cell.tests.test_module \
    --settings=test_settings
```

Requires `PyYAML` (declared in `requirements.txt`) for the spec-driven modules.

## Layout

| File | What it covers |
|------|----------------|
| `test_placement_api.py` | Schema regressions (e.g. `Education.grade` width), URL wiring is API-only, authentication + role authorization. Has no external deps. |
| `test_use_cases.py` | Use-case scenarios from `specs/use_cases.yaml`. |
| `test_business_rules.py` | Business rules from `specs/business_rules.yaml`. |
| `test_workflows.py` | End-to-end workflows from `specs/workflows.yaml`. |
| `test_module.py` | Selector/service unit tests (active). The `PlacementCellApiTests` class is **skipped**: it exercises the `globals` dashboard-notification API (`NotificationList`, `Notification.module`) that is not present on this branch. Re-enable once that lands. |

## Expected result

`OK (skipped=36)` — all executed tests pass; the only skips are the documented
cross-module integration tests in `test_module.PlacementCellApiTests`.
