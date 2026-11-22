/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { CHART_COLOR_PALETTES, EChartModels } from "@plane/constants";
import type { ChartYAxisMetric, IState, TBarItem, TChart, TChartDatum } from "@plane/types";
import { ChartXAxisProperty } from "@plane/types";
import { generateExtendedColors } from "@/components/chart/utils";

interface ParamsProps {
  x_axis: ChartXAxisProperty;
  y_axis: ChartYAxisMetric;
  group_by?: ChartXAxisProperty;
}

export const generateBarColor = (
  value: string | null | undefined,
  params: ParamsProps,
  baseColors: string[],
  workspaceStates?: IState[]
): string => {
  if (!value) return baseColors[0];
  let color = baseColors[0];
  // Priority
  if (params.x_axis === ChartXAxisProperty.PRIORITY) {
    color =
      value === "urgent"
        ? "#ef4444"
        : value === "high"
          ? "#f97316"
          : value === "medium"
            ? "#eab308"
            : value === "low"
              ? "#22c55e"
              : "#ced4da";
  }

  // State
  if (params.x_axis === ChartXAxisProperty.STATES) {
    if (workspaceStates && workspaceStates.length > 0) {
      const state = workspaceStates.find((s) => s.id === value);
      if (state) {
        color = state.color;
      } else {
        const index = Math.abs(value.split("").reduce((acc, char) => acc + char.charCodeAt(0), 0)) % baseColors.length;
        color = baseColors[index];
      }
    }
  }

  return color;
};

interface BuildPriorityChartBarsProps {
  parsedData?: TChart;
  chartModel: EChartModels;
  resolvedTheme?: string;
  x_axis: ChartXAxisProperty;
  y_axis: ChartYAxisMetric;
  group_by?: ChartXAxisProperty;
  workspaceStates?: IState[];
}

/**
 * Build the series definitions used by the work-item analytics bar chart.
 * Keeping this transformation outside the component makes the chart rules
 * independently testable and leaves the React component focused on rendering.
 */
export const buildPriorityChartBars = ({
  parsedData,
  chartModel,
  resolvedTheme,
  x_axis,
  y_axis,
  group_by,
  workspaceStates,
}: BuildPriorityChartBarsProps): TBarItem<string>[] => {
  if (!parsedData) return [];

  const schemaKeys = Object.keys(parsedData.schema);
  const baseColors = CHART_COLOR_PALETTES[0]?.[resolvedTheme === "dark" ? "dark" : "light"];
  const extendedColors = generateExtendedColors(baseColors ?? [], schemaKeys.length);

  if (chartModel === EChartModels.BASIC) {
    return [
      {
        key: "count",
        label: "Count",
        stackId: "bar-one",
        fill: (payload) =>
          generateBarColor(payload.key, { x_axis, y_axis, group_by }, baseColors ?? [], workspaceStates),
        textClassName: "",
        showPercentage: false,
        showTopBorderRadius: () => true,
        showBottomBorderRadius: () => true,
      },
    ];
  }

  if (chartModel !== EChartModels.STACKED) return [];

  const stackedBarExtremes = parsedData.data.reduce<Record<string, { top: string | null; bottom: string | null }>>(
    (extremesByDatum, datum) => {
      let top: string | null = null;
      let bottom: string | null = null;

      for (const key of schemaKeys) {
        if (datum[key] === 0) continue;
        if (!bottom) bottom = key;
        top = key;
      }

      extremesByDatum[datum.key] = { top, bottom };
      return extremesByDatum;
    },
    {}
  );

  return schemaKeys.map((key, index) => ({
    key,
    label: parsedData.schema[key],
    stackId: "bar-one",
    fill: extendedColors[index],
    textClassName: "",
    showPercentage: false,
    showTopBorderRadius: (value, payload: TChartDatum) => stackedBarExtremes[payload.key]?.top === value,
    showBottomBorderRadius: (value, payload: TChartDatum) => stackedBarExtremes[payload.key]?.bottom === value,
  }));
};
