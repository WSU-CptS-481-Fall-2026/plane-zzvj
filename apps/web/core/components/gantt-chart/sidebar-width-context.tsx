/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { createContext, useContext } from "react";

export const DEFAULT_GANTT_SIDEBAR_WIDTH = 360;
export const MIN_GANTT_SIDEBAR_WIDTH = 220;
export const MAX_GANTT_SIDEBAR_WIDTH = 600;

export const clampGanttSidebarWidth = (width: number) =>
  Math.min(MAX_GANTT_SIDEBAR_WIDTH, Math.max(MIN_GANTT_SIDEBAR_WIDTH, width));

export const getGanttSidebarWidthAfterDrag = (startWidth: number, startX: number, currentX: number) =>
  clampGanttSidebarWidth(startWidth + currentX - startX);

export const getGanttSidebarWidthAfterKeyboardResize = (currentWidth: number, delta: number) =>
  clampGanttSidebarWidth(currentWidth + delta);

type TGanttSidebarWidthContext = {
  sidebarWidth: number;
  setSidebarWidth: (width: number) => void;
};

export const GanttSidebarWidthContext = createContext<TGanttSidebarWidthContext>({
  sidebarWidth: DEFAULT_GANTT_SIDEBAR_WIDTH,
  setSidebarWidth: () => undefined,
});

export const useGanttSidebarWidth = () => useContext(GanttSidebarWidthContext);
