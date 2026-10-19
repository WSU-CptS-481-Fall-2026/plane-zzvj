# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Contract checks that the estimate API routes are registered under /api/v1/."""

import pytest
from django.urls import resolve
from rest_framework import status

from plane.db.models import Project, ProjectMember


@pytest.mark.contract
@pytest.mark.parametrize(
    ("path", "url_name"),
    [
        (
            "/api/v1/workspaces/demo/projects/00000000-0000-0000-0000-000000000001/estimates/",
            "project-estimate",
        ),
        (
            "/api/v1/workspaces/demo/projects/00000000-0000-0000-0000-000000000001/"
            "estimates/00000000-0000-0000-0000-000000000002/estimate-points/",
            "estimate-point-list-create",
        ),
        (
            "/api/v1/workspaces/demo/projects/00000000-0000-0000-0000-000000000001/"
            "estimates/00000000-0000-0000-0000-000000000002/estimate-points/"
            "00000000-0000-0000-0000-000000000003/",
            "estimate-point-detail",
        ),
    ],
)
def test_estimate_api_route_is_registered(path, url_name):
    """Ensure documented estimate endpoints resolve instead of returning Django's 404."""
    assert resolve(path).url_name == url_name


@pytest.mark.contract
@pytest.mark.django_db
def test_project_estimate_request_reaches_endpoint(api_key_client, workspace, create_user):
    """A missing estimate should return the endpoint's response, not Django's page 404."""
    project = Project.objects.create(
        name="Estimate API Project",
        identifier="EAP",
        workspace=workspace,
        created_by=create_user,
    )
    ProjectMember.objects.create(
        workspace=workspace,
        project=project,
        member=create_user,
        role=20,
        is_active=True,
    )

    response = api_key_client.get(
        f"/api/v1/workspaces/{workspace.slug}/projects/{project.id}/estimates/"
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.data == {"error": "Estimate not found"}
