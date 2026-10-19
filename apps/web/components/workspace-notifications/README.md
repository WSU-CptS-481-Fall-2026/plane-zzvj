# Notification timestamps

Notifications show times like "about 2 hours ago". Hover over the time to see the
exact date and time in your local timezone. You can also press Tab to focus the
timestamp and Escape to close the tooltip. Opening the tooltip does not open the
work item or mark the notification as read.

If a notification's creation date is missing or invalid, the timestamp is hidden.
Snoozed notifications show when the snooze ends in your local timezone.

Run the timestamp tests from the repository root:

```sh
pnpm --filter web test components/workspace-notifications/sidebar/notification-card/timestamp.test.tsx
```

The tests cover mouse and keyboard use, along with missing or invalid dates. They
also cover cases where a timestamp is on one day in UTC but the previous day in Los
Angeles, plus the clock change for daylight saving time.
