# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from unittest.mock import patch
from uuid import uuid4

import pytest
from django.core.cache import cache
from django.utils import timezone
from kombu.exceptions import OperationalError

from plane.bgtasks.workspace_invitation_task import workspace_invitation
from plane.db.models import User, Workspace, WorkspaceMember, WorkspaceMemberInvite


@pytest.fixture
def invitation(workspace, create_user):
    return WorkspaceMemberInvite.objects.create(
        workspace=workspace,
        email="invitee@example.invalid",
        token="existing-invitation-token",
        role=15,
        created_by=create_user,
    )


@pytest.fixture
def resend_url(workspace, invitation):
    return f"/api/workspaces/{workspace.slug}/invitations/{invitation.id}/resend/"


@pytest.fixture
def queued_invitation(settings):
    settings.CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
    cache.clear()
    with patch("plane.app.views.workspace.invite.workspace_invitation.delay") as queued:
        yield queued
    cache.clear()


@pytest.mark.contract
@pytest.mark.django_db
class TestResendWorkspaceInvitation:
    @pytest.mark.parametrize("actor_role,invite_role", [(20, 20), (20, 15), (20, 5), (15, 15), (15, 5)])
    def test_queues_existing_invitation_without_changing_it(
        self, session_client, workspace, invitation, resend_url, queued_invitation, settings, actor_role, invite_role
    ):
        WorkspaceMember.objects.filter(workspace=workspace).update(role=actor_role)
        invitation.role = invite_role
        invitation.save()
        before = WorkspaceMemberInvite.objects.values().get(pk=invitation.pk)
        response = session_client.post(resend_url)

        assert response.status_code == 202
        queued_invitation.assert_called_once_with(
            invitation.email,
            workspace.id,
            invitation.token,
            settings.APP_BASE_URL or settings.WEB_URL,
            workspace.owner.email,
        )
        assert WorkspaceMemberInvite.objects.values().get(pk=invitation.pk) == before
        assert WorkspaceMember.objects.filter(workspace=workspace).count() == 1

    @pytest.mark.parametrize("role,is_active", [(15, True), (5, True), (20, False)])
    def test_rejects_insufficient_or_inactive_membership(
        self, session_client, workspace, invitation, resend_url, queued_invitation, role, is_active
    ):
        invitation.role = 20
        invitation.save()
        WorkspaceMember.objects.filter(workspace=workspace).update(role=role, is_active=is_active)
        assert session_client.post(resend_url).status_code == 403
        queued_invitation.assert_not_called()

    @pytest.mark.parametrize("anonymous", [True, False])
    def test_rejects_nonmembers(self, api_client, resend_url, queued_invitation, anonymous):
        if not anonymous:
            api_client.force_authenticate(
                user=User.objects.create(email="outsider@example.invalid", username=uuid4().hex)
            )
        assert api_client.post(resend_url).status_code == (401 if anonymous else 403)
        queued_invitation.assert_not_called()

    def test_scopes_invitation_to_workspace(self, session_client, create_user, invitation, queued_invitation):
        other = Workspace.objects.create(name="Other", slug="other", owner=create_user)
        WorkspaceMember.objects.create(workspace=other, member=create_user, role=20)
        response = session_client.post(f"/api/workspaces/{other.slug}/invitations/{invitation.id}/resend/")
        assert response.status_code == 404
        queued_invitation.assert_not_called()

    @pytest.mark.parametrize("state", ["missing", "removed", "accepted", "declined"])
    def test_rejects_unavailable_invitations(self, session_client, invitation, resend_url, queued_invitation, state):
        if state == "missing":
            resend_url = resend_url.replace(str(invitation.id), str(uuid4()))
        elif state == "removed":
            invitation.delete()
        else:
            invitation.accepted = state == "accepted"
            invitation.responded_at = timezone.now() if state == "declined" else None
            invitation.save()
        response = session_client.post(resend_url)
        assert response.status_code == (404 if state in {"missing", "removed"} else 400)
        queued_invitation.assert_not_called()

    @pytest.mark.parametrize("is_active", [True, False])
    def test_only_active_invitees_are_already_members(
        self, session_client, workspace, invitation, resend_url, queued_invitation, is_active
    ):
        member = User.objects.create(email=invitation.email.upper(), username=uuid4().hex)
        WorkspaceMember.objects.create(workspace=workspace, member=member, role=5, is_active=is_active)
        response = session_client.post(resend_url)
        assert response.status_code == (400 if is_active else 202)
        assert queued_invitation.call_count == (0 if is_active else 1)

    def test_duplicate_requests_share_a_cooldown_across_senders(
        self, session_client, api_client, workspace, resend_url, queued_invitation
    ):
        assert session_client.post(resend_url).status_code == 202
        colleague = User.objects.create(email="colleague@example.invalid", username=uuid4().hex)
        WorkspaceMember.objects.create(workspace=workspace, member=colleague, role=20)
        api_client.force_authenticate(user=colleague)
        response = api_client.post(resend_url)
        assert response.status_code == 429
        assert response["Retry-After"] == "60"
        queued_invitation.assert_called_once()

    def test_can_resend_after_cooldown(self, session_client, resend_url, queued_invitation):
        with patch("django.core.cache.backends.locmem.time.time", return_value=1000):
            assert session_client.post(resend_url).status_code == 202
        with patch("django.core.cache.backends.locmem.time.time", return_value=1061):
            assert session_client.post(resend_url).status_code == 202
        assert queued_invitation.call_count == 2

    def test_cooldown_does_not_block_other_invitations(self, session_client, workspace, resend_url, queued_invitation):
        other = WorkspaceMemberInvite.objects.create(workspace=workspace, email="other@example.invalid", token="other")
        assert session_client.post(resend_url).status_code == 202
        assert (
            session_client.post(f"/api/workspaces/{workspace.slug}/invitations/{other.id}/resend/").status_code == 202
        )
        assert queued_invitation.call_count == 2

    def test_queue_failure_allows_retry(self, session_client, resend_url, queued_invitation):
        queued_invitation.side_effect = OperationalError("Test broker unavailable")
        response = session_client.post(resend_url)
        assert response.status_code == 503
        assert "error" in response.data
        queued_invitation.side_effect = None
        assert session_client.post(resend_url).status_code == 202

    def test_get_cannot_send_mail(self, session_client, resend_url, queued_invitation):
        assert session_client.get(resend_url).status_code == 405
        queued_invitation.assert_not_called()


@pytest.fixture
def deliver_invitation(invitation, create_user, monkeypatch):
    monkeypatch.setattr(
        "plane.bgtasks.workspace_invitation_task.get_email_configuration",
        lambda: ("test-smtp.invalid", "", "", "25", "0", "0", "noreply@example.invalid"),
    )

    def deliver(**overrides):
        args = dict(
            email=invitation.email,
            workspace_id=invitation.workspace_id,
            token=invitation.token,
            current_site="http://localhost:3000",
            inviter=create_user.email,
        )
        workspace_invitation.run(**(args | overrides))

    return deliver


@pytest.mark.contract
@pytest.mark.django_db
class TestWorkspaceInvitationDelivery:
    def test_sends_original_link_and_keeps_invitation_pending(self, invitation, deliver_invitation, mailoutbox):
        deliver_invitation()
        assert len(mailoutbox) == 1
        assert mailoutbox[0].to == [invitation.email]
        assert f"invitation_id={invitation.id}" in mailoutbox[0].body
        assert f"token={invitation.token}" in mailoutbox[0].body
        invitation.refresh_from_db()
        assert invitation.responded_at is None
        assert invitation.accepted is False

    @pytest.mark.parametrize("state", ["accepted", "declined", "removed", "member"])
    def test_skips_invitation_changed_since_queuing(self, invitation, deliver_invitation, mailoutbox, state):
        if state == "removed":
            invitation.delete()
        elif state == "member":
            member = User.objects.create(email=invitation.email, username=uuid4().hex)
            WorkspaceMember.objects.create(workspace=invitation.workspace, member=member, role=15)
        else:
            invitation.accepted = state == "accepted"
            invitation.responded_at = timezone.now()
            invitation.save()
        deliver_invitation()
        assert not mailoutbox

    def test_requires_matching_workspace(self, deliver_invitation, mailoutbox, create_user):
        other = Workspace.objects.create(name="Other", slug="other", owner=create_user)
        deliver_invitation(workspace_id=other.id)
        assert not mailoutbox

    @pytest.mark.parametrize("removed", [True, False])
    def test_response_during_render_does_not_resurrect_invitation(
        self, invitation, deliver_invitation, mailoutbox, removed
    ):
        def render(*args, **kwargs):
            if removed:
                invitation.delete()
            else:
                WorkspaceMemberInvite.objects.filter(pk=invitation.pk).update(
                    accepted=True, responded_at=timezone.now()
                )
            return "<p>Test invitation</p>"

        with patch("plane.bgtasks.workspace_invitation_task.render_to_string", side_effect=render):
            deliver_invitation()
        assert not mailoutbox
        if removed:
            assert not WorkspaceMemberInvite.objects.filter(pk=invitation.pk).exists()
        else:
            invitation.refresh_from_db()
            assert invitation.accepted
            assert invitation.responded_at is not None
