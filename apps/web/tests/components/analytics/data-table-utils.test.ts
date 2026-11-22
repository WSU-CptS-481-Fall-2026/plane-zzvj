import { describe, expect, it, vi } from "vitest";
import type { Table as TanstackTable } from "@tanstack/react-table";
import {
  getSearchColumnId,
  getSearchFilterValue,
  setSearchFilterValue,
} from "@/components/analytics/insight-table/data-table.utils";

interface TestRow {
  project: string;
}

const createTableMock = (columnId?: string, filterValue?: string) => {
  const setFilterValue = vi.fn();
  const getColumn = vi.fn(() =>
    columnId
      ? {
          getFilterValue: () => filterValue,
          setFilterValue,
        }
      : undefined
  );
  const table = {
    getHeaderGroups: () => (columnId ? [{ headers: [{ id: columnId }] }] : []),
    getColumn,
  } as unknown as TanstackTable<TestRow>;

  return { table, getColumn, setFilterValue };
};

describe("insight table search helpers", () => {
  it("reads the first header's column ID and current filter value", () => {
    const { table } = createTableMock("project__name", "Roadmap");

    expect(getSearchColumnId(table)).toBe("project__name");
    expect(getSearchFilterValue(table)).toBe("Roadmap");
  });

  it("updates the first column's filter value", () => {
    const { table, getColumn, setFilterValue } = createTableMock("project__name");

    setSearchFilterValue(table, "Roadmap");

    expect(getColumn).toHaveBeenCalledWith("project__name");
    expect(setFilterValue).toHaveBeenCalledWith("Roadmap");
  });

  it("does nothing when the table has no searchable header", () => {
    const { table, getColumn } = createTableMock();

    expect(getSearchColumnId(table)).toBeUndefined();
    expect(getSearchFilterValue(table)).toBeUndefined();
    setSearchFilterValue(table, "Roadmap");
    expect(getColumn).not.toHaveBeenCalled();
  });
});
