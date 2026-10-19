/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { Tooltip } from "@makeplane/propel/components/tooltip";
import { calculateTimeAgo, renderFormattedDate, renderFormattedTime } from "@plane/utils";

export function NotificationTimestamp({ createdAt }: { createdAt: string | undefined }) {
  // Share one parsed instant so the date and time use the same local timezone.
  const date = createdAt ? new Date(createdAt) : undefined;
  const formattedDate = renderFormattedDate(date);
  if (!date || !formattedDate) return null;

  return (
    <Tooltip label={`${formattedDate}, ${renderFormattedTime(date)}`}>
      <time dateTime={date.toISOString()} tabIndex={0} className="mt-auto flex-shrink-0 cursor-help text-tertiary">
        {calculateTimeAgo(date)}
      </time>
    </Tooltip>
  );
}
