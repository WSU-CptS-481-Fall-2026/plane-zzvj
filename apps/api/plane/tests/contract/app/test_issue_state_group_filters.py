# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Invalid state groups must be client errors in both issue-list filter paths."""

import json

import pytest

from plane.db.models import Issue, Project, ProjectMember, State, StateGroup


@pytest.fixture
def issue_list_url(workspace, create_user):
    project = Project.objects.create(name="Group filters", identifier="GF", workspace=workspace)
    ProjectMember.objects.create(project=project, workspace=workspace, member=create_user, role=20)
    for group in ["completed", "started", "backlog"]:
        state = State.objects.create(name=group, group=group, project=project, workspace=workspace)
        Issue.objects.create(name=group, state=state, project=project, workspace=workspace, priority="low")
    return f"/api/workspaces/{workspace.slug}/projects/{project.id}/issues/"


def group_params(path, groups):
    if path == "legacy":
        return {"state_group": ",".join(groups)}
    return {"filters": json.dumps({"state_group__in": groups})}


@pytest.mark.contract
@pytest.mark.django_db
class TestIssueStateGroupFilters:
    @pytest.mark.parametrize("path", ["legacy", "json"])
    @pytest.mark.parametrize("groups", [["hello"], ["hello", "completed"], ["completed", "hello"]])
    def test_invalid_and_mixed_groups_return_400(self, session_client, issue_list_url, path, groups):
        response = session_client.get(issue_list_url, group_params(path, groups))
        assert response.status_code == 400
        assert "state_group" in str(response.data)
        assert "hello" in str(response.data)

    @pytest.mark.parametrize("lookup", ["state_group", "state_group__exact"])
    @pytest.mark.parametrize(
        "groups", [["hello", "completed"], ["completed", "hello"], ["completed", "started"], ["completed"]]
    )
    def test_scalar_json_lookups_reject_arrays(self, session_client, issue_list_url, lookup, groups):
        response = session_client.get(issue_list_url, {"filters": json.dumps({lookup: groups})})
        assert response.status_code == 400
        assert response.data["code"] == "invalid_filterset"
        assert lookup in response.data["errors"]

    @pytest.mark.parametrize("path", ["legacy", "json"])
    @pytest.mark.parametrize("group", StateGroup.values)
    def test_each_valid_group_including_no_matches(self, session_client, issue_list_url, path, group):
        response = session_client.get(issue_list_url, group_params(path, [group]))
        assert response.status_code == 200, response.data
        expected = {group} if group in {"completed", "started", "backlog"} else set()
        assert {issue["name"] for issue in response.data["results"]} == expected

    @pytest.mark.parametrize("path", ["legacy", "json"])
    def test_multiple_valid_groups_with_paging_and_other_filter(self, session_client, issue_list_url, path):
        params = {**group_params(path, ["completed", "started"]), "priority": "low"}
        response = session_client.get(issue_list_url, params)
        assert response.status_code == 200, response.data
        assert {issue["name"] for issue in response.data["results"]} == {"completed", "started"}
        response = session_client.get(issue_list_url, {**params, "per_page": 1})
        assert response.status_code == 200
        assert len(response.data["results"]) == 1
        assert response.data["total_count"] == 2

    @pytest.mark.parametrize(
        "filters",
        [
            {"state_group": "hello"},
            {"state_group__exact": "hello"},
            {"state_group__in": "hello,completed"},
            {"or": [{"state_group": "completed"}, {"state_group": "hello"}]},
            {"and": [{"state_group": "completed"}, {"state_group": "hello"}]},
            {"not": {"state_group__in": ["hello", "completed"]}},
        ],
    )
    def test_invalid_json_lookups_and_nested_filters(self, session_client, issue_list_url, filters):
        response = session_client.get(issue_list_url, {"filters": json.dumps(filters)})
        assert response.status_code == 400
        assert response.data["code"] == "invalid_filterset"
        assert "hello" in str(response.data["errors"])

    @pytest.mark.parametrize(
        "filters",
        [
            {"state_group__in": "completed,started"},
            {"or": [{"state_group": "completed"}, {"state_group__exact": "started"}]},
            {"not": {"state_group": "backlog"}},
        ],
    )
    def test_valid_json_csv_and_nested_filters(self, session_client, issue_list_url, filters):
        response = session_client.get(issue_list_url, {"filters": json.dumps(filters)})
        assert response.status_code == 200, response.data
        assert {issue["name"] for issue in response.data["results"]} == {"completed", "started"}

    def test_other_csv_filter_types_preserve_json_lists(self, session_client, issue_list_url):
        states = list(Issue.objects.filter(name__in=["completed", "started"]).values_list("state_id", flat=True))
        filters = {
            "state_id__in": [str(state) for state in states],
            "priority__in": ["low", "high"],
            "created_at__range": ["2000-01-01", "2099-12-31"],
        }
        response = session_client.get(issue_list_url, {"filters": json.dumps(filters)})
        assert response.status_code == 200, response.data
        assert {issue["name"] for issue in response.data["results"]} == {"completed", "started"}

    @pytest.mark.parametrize("params", [{}, {"state_group": ""}, {"state_group": "null"}, {"filters": "{}"}])
    def test_unset_filters_preserve_results(self, session_client, issue_list_url, params):
        response = session_client.get(issue_list_url, params)
        assert response.status_code == 200, response.data
        assert len(response.data["results"]) == 3
