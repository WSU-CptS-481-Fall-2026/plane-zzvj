# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.


"""
Unit tests for intake work itemrejection email notifications task.

Verifies that the task sends an email notification to the creator of a rejected intake work item.
"""

from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

import pytest

from plane.bgtasks.intake_rejection_email_task import send_intake_rejection_email


@pytest.mark.unit
class TestIntakeRejectionEmail:
    @patch(
        "plane.bgtasks.intake_rejection_email_task.get_email_configuration"
    )
    @patch(
        "plane.bgtasks.intake_rejection_email_task.get_connection"
    )
    @patch(
        "plane.bgtasks.intake_rejection_email_task.EmailMultiAlternatives"
    )
    @patch(
        "plane.bgtasks.intake_rejection_email_task.IntakeIssue.objects.select_related"
    )
    def test_rejected_item_sends_email(
        self, mock_select_related, mock_email, mock_connection, mock_config
    ):
        creator = SimpleNamespace(
            first_name="Alex",
            email="alex@example.com",
        )
        intake_issue = SimpleNamespace(
            status=-1,
            created_by=creator,
            issue=SimpleNamespace(name="Test work item"),
        )
        mock_select_related.return_value.get.return_value = intake_issue
        mock_config.return_value = (
            "localhost", "user", "password", 587, "1", "0", "noreply@example.com"
        )

        send_intake_rejection_email(str(uuid4()))

        assert mock_email.call_count == 1
        assert mock_email.call_args.kwargs["to"] == ["alex@example.com"]
        mock_email.return_value.send.assert_called_once()

    @patch(
        "plane.bgtasks.intake_rejection_email_task.IntakeIssue.objects.select_related"
    )
    @patch("plane.bgtasks.intake_rejection_email_task.EmailMultiAlternatives")
    def test_non_rejected_item_does_not_send_email(
        self, mock_email, mock_select_related
    ):
        intake_issue = SimpleNamespace(
            status=-2,
            created_by=SimpleNamespace(email="alex@example.com"),
        )
        mock_select_related.return_value.get.return_value = intake_issue

        send_intake_rejection_email(str(uuid4()))

        mock_email.assert_not_called()

    @patch(
        "plane.bgtasks.intake_rejection_email_task.IntakeIssue.objects.select_related"
    )
    @patch("plane.bgtasks.intake_rejection_email_task.EmailMultiAlternatives")
    def test_missing_creator_does_not_send_email(
        self, mock_email, mock_select_related
    ):
        intake_issue = SimpleNamespace(status=-1, created_by=None)
        mock_select_related.return_value.get.return_value = intake_issue

        send_intake_rejection_email(str(uuid4()))

        mock_email.assert_not_called()

    @patch(
        "plane.bgtasks.intake_rejection_email_task.IntakeIssue.objects.select_related"
    )
    @patch("plane.bgtasks.intake_rejection_email_task.EmailMultiAlternatives")
    def test_creator_without_email_does_not_send_email(
        self, mock_email, mock_select_related
    ):
        creator = SimpleNamespace(email="")
        intake_issue = SimpleNamespace(status=-1, created_by=creator)
        mock_select_related.return_value.get.return_value = intake_issue

        send_intake_rejection_email(str(uuid4()))

        mock_email.assert_not_called()

    @patch(
        "plane.bgtasks.intake_rejection_email_task.IntakeIssue.objects.select_related"
    )
    @patch("plane.bgtasks.intake_rejection_email_task.EmailMultiAlternatives")
    def test_missing_intake_item_does_not_send_email(
        self, mock_email, mock_select_related
    ):
        from plane.db.models import IntakeIssue

        mock_select_related.return_value.get.side_effect = (
            IntakeIssue.DoesNotExist
        )

        send_intake_rejection_email(str(uuid4()))

        mock_email.assert_not_called()
