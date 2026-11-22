import { describe, expect, it } from "vitest";
import { EChartModels } from "@plane/constants";
import type { TChart } from "@plane/types";
import { ChartXAxisProperty, ChartYAxisMetric } from "@plane/types";
import { buildPriorityChartBars } from "@/components/analytics/work-items/utils";

// TChartDatum currently intersects string-valued key/name fields with Record<string, number>.
// The API shape is valid; this cast keeps that unrelated shared type issue local to this fixture.
const chartData = {
  data: [
    { key: "project-a", name: "Project A", count: 4, backlog: 2, started: 0, done: 2 },
    { key: "project-b", name: "Project B", count: 4, backlog: 0, started: 1, done: 3 },
  ],
  schema: { backlog: "Backlog", started: "Started", done: "Done" },
} as unknown as TChart;

describe("buildPriorityChartBars", () => {
  it("returns no bars until chart data is available", () => {
    expect(
      buildPriorityChartBars({
        chartModel: EChartModels.BASIC,
        x_axis: ChartXAxisProperty.PRIORITY,
        y_axis: ChartYAxisMetric.WORK_ITEM_COUNT,
      })
    ).toEqual([]);
  });

  it("builds the single count bar and preserves priority coloring for a basic chart", () => {
    const bars = buildPriorityChartBars({
      parsedData: chartData,
      chartModel: EChartModels.BASIC,
      resolvedTheme: "light",
      x_axis: ChartXAxisProperty.PRIORITY,
      y_axis: ChartYAxisMetric.WORK_ITEM_COUNT,
    });

    expect(bars).toHaveLength(1);
    expect(bars[0]).toMatchObject({ key: "count", label: "Count", stackId: "bar-one" });
    expect(typeof bars[0]?.fill).toBe("function");
    expect(typeof bars[0]?.showTopBorderRadius).toBe("function");
    expect(bars[0]?.showTopBorderRadius?.("count", chartData.data[0])).toBe(true);
    expect(bars[0]?.showBottomBorderRadius?.("count", chartData.data[0])).toBe(true);
    expect(typeof bars[0]?.fill === "function" && bars[0].fill({ key: "high" })).toBe("#f97316");
  });

  it("builds stacked series and rounds only the non-zero ends of each stack", () => {
    const bars = buildPriorityChartBars({
      parsedData: chartData,
      chartModel: EChartModels.STACKED,
      resolvedTheme: "dark",
      x_axis: ChartXAxisProperty.STATES,
      y_axis: ChartYAxisMetric.WORK_ITEM_COUNT,
    });
    const [backlog, started, done] = bars;

    expect(bars.map(({ key, label }) => ({ key, label }))).toEqual([
      { key: "backlog", label: "Backlog" },
      { key: "started", label: "Started" },
      { key: "done", label: "Done" },
    ]);
    expect(backlog?.showBottomBorderRadius?.("backlog", chartData.data[0])).toBe(true);
    expect(backlog?.showTopBorderRadius?.("backlog", chartData.data[0])).toBe(false);
    expect(started?.showBottomBorderRadius?.("started", chartData.data[1])).toBe(true);
    expect(done?.showTopBorderRadius?.("done", chartData.data[0])).toBe(true);
    expect(done?.showTopBorderRadius?.("done", chartData.data[1])).toBe(true);
    expect(bars.every(({ fill }) => typeof fill === "string" && fill.length > 0)).toBe(true);
  });

  it("returns no series for chart models that are not supported here", () => {
    expect(
      buildPriorityChartBars({
        parsedData: chartData,
        chartModel: EChartModels.GROUPED,
        x_axis: ChartXAxisProperty.PRIORITY,
        y_axis: ChartYAxisMetric.WORK_ITEM_COUNT,
      })
    ).toEqual([]);
  });
});
