# Resend workspace invitations

Go to **Workspace settings → Members → Pending invites** and choose
**Resend invitation** from the invitation's menu.

Active workspace admins and members can resend pending invitations for their
own role or a lower role. The recipient must not already be an active member.

Resending keeps the same link and role. Success means the email was queued.
Wait 60 seconds before resending the same invitation.

Run tests from the repository root:

```bash
pnpm --filter web test components/workspace/settings/invitations-list-item.test.tsx
docker compose -f docker-compose-test.yml run --rm api-tests \
  pytest plane/tests/contract/app/test_workspace_invitation_resend.py
```
