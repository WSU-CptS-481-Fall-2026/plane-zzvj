/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { ComponentType } from "react";
import { observer } from "mobx-react";
// helpers
import { getValidKeysFromObject } from "@plane/utils";
// hooks
import { useIssueDetail } from "@/hooks/store/use-issue-detail";
import { useTimeLineRelationOptions } from "@/components/relations";
// local components
import {
  IssueDefaultActivity,
  IssueNameActivity,
  IssueDescriptionActivity,
  IssueStateActivity,
  IssueAssigneeActivity,
  IssuePriorityActivity,
  IssueEstimateActivity,
  IssueParentActivity,
  IssueRelationActivity,
  IssueStartDateActivity,
  IssueTargetDateActivity,
  IssueCycleActivity,
  IssueModuleActivity,
  IssueLabelActivity,
  IssueLinkActivity,
  IssueAttachmentActivity,
  IssueArchivedAtActivity,
  IssueInboxActivity,
} from "./actions";

type TIssueActivityItem = {
  activityId: string;
  ends: "top" | "bottom" | undefined;
};

type TActivityRenderer = {
  Component: ComponentType<TIssueActivityItem & { showIssue?: boolean }>;
  showIssue?: boolean;
};

const estimateRenderer = { Component: IssueEstimateActivity, showIssue: false };

const activityRenderers: Record<string, TActivityRenderer | undefined> = {
  state: { Component: IssueStateActivity, showIssue: false },
  name: { Component: IssueNameActivity },
  description: { Component: IssueDescriptionActivity, showIssue: false },
  assignees: { Component: IssueAssigneeActivity, showIssue: false },
  priority: { Component: IssuePriorityActivity, showIssue: false },
  estimate_points: estimateRenderer,
  estimate_categories: estimateRenderer,
  estimate_point: estimateRenderer, // Older estimate records.
  parent: { Component: IssueParentActivity, showIssue: false },
  start_date: { Component: IssueStartDateActivity, showIssue: false },
  target_date: { Component: IssueTargetDateActivity, showIssue: false },
  cycles: { Component: IssueCycleActivity },
  modules: { Component: IssueModuleActivity },
  labels: { Component: IssueLabelActivity, showIssue: false },
  link: { Component: IssueLinkActivity, showIssue: false },
  attachment: { Component: IssueAttachmentActivity, showIssue: false },
  archived_at: { Component: IssueArchivedAtActivity },
  intake: { Component: IssueInboxActivity },
  inbox: { Component: IssueInboxActivity },
};

export const IssueActivityItem = observer(function IssueActivityItem(props: TIssueActivityItem) {
  const { activityId, ends } = props;
  const {
    activity: { getActivityById },
  } = useIssueDetail();
  const activityRelations = getValidKeysFromObject(useTimeLineRelationOptions());
  const activityField = getActivityById(activityId)?.field;

  if (activityField === null) {
    return <IssueDefaultActivity activityId={activityId} ends={ends} />;
  }
  if (activityField === undefined || activityRelations.includes(activityField)) {
    return <IssueRelationActivity activityId={activityId} ends={ends} />;
  }

  const renderer = Object.hasOwn(activityRenderers, activityField) ? activityRenderers[activityField] : undefined;
  if (!renderer) return null;

  const { Component, ...options } = renderer;
  return <Component activityId={activityId} ends={ends} {...options} />;
});
