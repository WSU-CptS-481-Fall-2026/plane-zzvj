# Estimate API routes

The estimate endpoints are part of the external REST API and are served beneath
`/api/v1/`. Their request and response schemas are generated from the endpoint
views' OpenAPI decorators.

| Route                                                                                                   | Methods                  | Purpose                                 |
| ------------------------------------------------------------------------------------------------------- | ------------------------ | --------------------------------------- |
| `/workspaces/{slug}/projects/{project_id}/estimates/`                                                   | GET, POST, PATCH, DELETE | Retrieve or manage a project's estimate |
| `/workspaces/{slug}/projects/{project_id}/estimates/{estimate_id}/estimate-points/`                     | GET, POST                | List or create estimate points          |
| `/workspaces/{slug}/projects/{project_id}/estimates/{estimate_id}/estimate-points/{estimate_point_id}/` | PATCH, DELETE            | Update or delete an estimate point      |

These route patterns are defined in `plane/api/urls/estimate.py` and must be
included by the external API URL registry in `plane/api/urls/__init__.py` so
that the endpoints are reachable and included in the generated API schema.
