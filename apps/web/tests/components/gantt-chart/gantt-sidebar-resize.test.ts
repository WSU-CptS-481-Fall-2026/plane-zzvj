import { describe, expect, it } from "vitest";
import {
  clampGanttSidebarWidth,
  getGanttSidebarWidthAfterDrag,
  getGanttSidebarWidthAfterKeyboardResize,
  MAX_GANTT_SIDEBAR_WIDTH,
  MIN_GANTT_SIDEBAR_WIDTH,
} from "@/components/gantt-chart/sidebar-width-context";

describe("Gantt work item column resize", () => {
  // The divider should never shrink the work item column below its minimum or grow it without bound.
  describe("width limits", () => {
    it("clamps requested widths and allows values within the limits", () => {
      expect(clampGanttSidebarWidth(MIN_GANTT_SIDEBAR_WIDTH - 1)).toBe(MIN_GANTT_SIDEBAR_WIDTH);
      expect(clampGanttSidebarWidth(420)).toBe(420);
      expect(clampGanttSidebarWidth(MAX_GANTT_SIDEBAR_WIDTH + 1)).toBe(MAX_GANTT_SIDEBAR_WIDTH);
    });
  });

  // Pointer movement should change the column by the same horizontal distance and respect both limits.
  describe("pointer dragging", () => {
    it("adjusts the width by the pointer movement", () => {
      expect(getGanttSidebarWidthAfterDrag(360, 100, 140)).toBe(400);
    });

    it("clamps the dragged width at the minimum and maximum", () => {
      expect(getGanttSidebarWidthAfterDrag(360, 100, -100)).toBe(MIN_GANTT_SIDEBAR_WIDTH);
      expect(getGanttSidebarWidthAfterDrag(560, 100, 160)).toBe(MAX_GANTT_SIDEBAR_WIDTH);
    });
  });

  // Keyboard resizing uses 20-pixel steps and follows the same width limits as pointer dragging.
  describe("keyboard resizing", () => {
    it("adjusts the width by one keyboard step", () => {
      expect(getGanttSidebarWidthAfterKeyboardResize(360, 20)).toBe(380);
    });

    it("does not resize past either limit", () => {
      expect(getGanttSidebarWidthAfterKeyboardResize(MIN_GANTT_SIDEBAR_WIDTH, -20)).toBe(MIN_GANTT_SIDEBAR_WIDTH);
      expect(getGanttSidebarWidthAfterKeyboardResize(MAX_GANTT_SIDEBAR_WIDTH, 20)).toBe(MAX_GANTT_SIDEBAR_WIDTH);
    });
  });
});
