# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import json

import pytest

from plane.db.models import Issue, Project, ProjectMember, State
from plane.utils.filters import LegacyToRichFiltersConverter

pytestmark = [pytest.mark.contract, pytest.mark.django_db]


@pytest.fixture
def issue_list_url(workspace, create_user):
    project = Project.objects.create(name="Issue filters", identifier="FILT", workspace=workspace)
    ProjectMember.objects.create(project=project, workspace=workspace, member=create_user, role=20)
    for group, items in [
        ("started", [("Prototype", "high"), ("Polish", "low")]),
        ("completed", [("Release", "low")]),
        ("backlog", [("Archive", "high")]),
    ]:
        state = State.objects.create(name=group, group=group, project=project, workspace=workspace)
        for name, priority in items:
            Issue.objects.create(name=name, priority=priority, state=state, project=project, workspace=workspace)
    return f"/api/workspaces/{workspace.slug}/projects/{project.id}/issues/"


@pytest.mark.parametrize(
    ("tree", "names"),
    [
        ({"priority": "high", "state_group": "backlog"}, {"Archive"}),
        ({"and": [{"priority": "low"}, {"state_group": "backlog"}]}, set()),
        (
            {
                "or": [
                    {"and": [{"state_group": "started"}, {"not": {"priority": "high"}}]},
                    {"state_group": "completed"},
                ]
            },
            {"Polish", "Release"},
        ),
        ({"AND": [{"priority": "high"}, {"state_group": "started"}]}, {"Prototype"}),
        ({"oR": [{"state_group": "completed"}, {"state_group": "backlog"}]}, {"Release", "Archive"}),
        ({"Not": {"state_group": "started"}}, {"Release", "Archive"}),
    ],
    ids=["leaf-fields", "empty-intersection", "nested", "uppercase-and", "mixed-case-or", "mixed-case-not"],
)
def test_filters_select_matching_issues(session_client, issue_list_url, tree, names):
    response = session_client.get(issue_list_url, {"filters": json.dumps(tree)})
    assert response.status_code == 200, response.data
    assert {issue["name"] for issue in response.data["results"]} == names
    assert response.data["total_count"] == len(names)


@pytest.mark.parametrize(
    ("raw_filter", "code"),
    [
        ("{", "invalid_json"),
        (json.dumps({"and": []}), "invalid_operator_children"),
        (json.dumps({"not": {"priority__startswith": "h"}}), "invalid_filter_field"),
        (json.dumps({"or": [{"state_group": "unrecognized"}, {"priority": "high"}]}), "invalid_filterset"),
    ],
)
def test_invalid_filters_return_a_client_error(session_client, issue_list_url, raw_filter, code):
    response = session_client.get(issue_list_url, {"filters": raw_filter})
    assert response.status_code == 400, response.data
    assert response.data["code"] == code


def test_converted_saved_filter_selects_the_expected_issues(session_client, issue_list_url):
    saved_filter = {"state_group": ["started", "completed"], "priority": "low"}
    converted = LegacyToRichFiltersConverter().convert(saved_filter, strict=True)
    response = session_client.get(issue_list_url, {"filters": json.dumps(converted)})
    assert response.status_code == 200, response.data
    assert {issue["name"] for issue in response.data["results"]} == {"Polish", "Release"}
