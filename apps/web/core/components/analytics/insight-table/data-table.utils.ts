import type { Table as TanstackTable } from "@tanstack/react-table";

/** The insight table's search input filters the first visible table column. */
export const getSearchColumnId = <TData>(table: TanstackTable<TData>): string | undefined =>
  table.getHeaderGroups()[0]?.headers[0]?.id;

export const getSearchFilterValue = <TData>(table: TanstackTable<TData>): string | undefined => {
  const columnId = getSearchColumnId(table);
  return columnId ? (table.getColumn(columnId)?.getFilterValue() as string | undefined) : undefined;
};

export const setSearchFilterValue = <TData>(table: TanstackTable<TData>, value: string): void => {
  const columnId = getSearchColumnId(table);
  if (!columnId) return;

  table.getColumn(columnId)?.setFilterValue(value);
};
