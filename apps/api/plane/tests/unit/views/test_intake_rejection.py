# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""
Unit tests for intake rejection notification triggers.
"""

import pytest

from unittest.mock import Mock

def schedule_rejection_notification(old_status, new_status, email_task, intake_issue_id):
    """Test helper of rejection condition used by the views."""
    if old_status != -1 and new_status == -1:
        email_task.delay(intake_issue_id)


@pytest.mark.unit
class TestIntakeRejectionStatus:
    @pytest.mark.parametrize(
        "old_status,new_status,should_notify",
        [
            (-2, -1, True),   # Pending->Rejected
            (1, -1, True),    # Accepted->Rejected
            (-1, -1, False),  # Rejected->Rejected
            (-2, 1, False),   # Pending->Accepted
        ],
    )
    def test_rejection_status_change(
        self, old_status, new_status, should_notify
    ):
        email_task = Mock()

        schedule_rejection_notification(
            old_status,
            new_status,
            email_task,
            "test-intake-id",
        )

        if should_notify:
            email_task.delay.assert_called_once_with("test-intake-id")
        else:
            email_task.delay.assert_not_called()
