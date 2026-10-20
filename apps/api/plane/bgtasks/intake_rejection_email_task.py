# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Python imports
import logging

# Third party imports
from celery import shared_task

# Django imports
# Third party imports
from django.core.mail import EmailMultiAlternatives, get_connection

# Module imports
from plane.db.models import IntakeIssue
from plane.license.utils.instance_value import get_email_configuration
from plane.utils.exception_logger import log_exception

@shared_task
def send_intake_rejection_email(intake_issue_id):
    try:
        # Find the rejected intake item and its creator
        intake_issue = IntakeIssue.objects.select_related(
            "created_by", "issue"
        ).get(pk=intake_issue_id)

        # Only notify for rejected intake items
        if intake_issue.status != -1:
            return

        # Skip items without a creator or email address
        creator = intake_issue.created_by
        if creator is None or not creator.email:
            return

        subject = "Your intake work item was declined--Plane"

        body = (
            f"Hello {creator.first_name or creator.email},\n\n"
            f"Your intake work item: '{intake_issue.issue.name}' "
            "has been declined.\n\n"
            "Thank you,\n"
            "Plane"
        )

        (
            email_host,
            email_host_user,
            email_host_password,
            email_port,
            email_use_tls,
            email_use_ssl,
            email_from,
        ) = get_email_configuration()

        connection = get_connection(
            host=email_host,
            port=int(email_port),
            username=email_host_user,
            password=email_host_password,
            use_tls=email_use_tls == "1",
            use_ssl=email_use_ssl == "1",
        )

        message = EmailMultiAlternatives(
            subject=subject,
            body=body,
            from_email=email_from,
            to=[creator.email],
            connection=connection,
        )

        message.send()

        logging.getLogger("plane.worker").info(
            "Intake rejection email sent successfully."
        )

    except IntakeIssue.DoesNotExist:
        return
    except Exception as e:
        log_exception(e)
        return
