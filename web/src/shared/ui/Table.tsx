import type { ReactNode } from "react";

export type TableColumn = string | { label: string; hidden?: boolean; className?: string };

function ColumnHeader({ column }: { column: TableColumn }) {
  const spec = typeof column === "string" ? { label: column } : column;
  return (
    <th scope="col" className={spec.className}>
      {spec.hidden ? <span className="visually-hidden">{spec.label}</span> : spec.label}
    </th>
  );
}

export function Table({
  label,
  columns,
  children,
}: {
  label: string;
  columns?: TableColumn[];
  children: ReactNode;
}) {
  return (
    <div className="table-scroll">
      <table className="table" aria-label={label}>
        {columns && (
          <thead>
            <tr>
              {columns.map((column) => (
                <ColumnHeader
                  key={typeof column === "string" ? column : column.label}
                  column={column}
                />
              ))}
            </tr>
          </thead>
        )}
        {columns ? <tbody>{children}</tbody> : children}
      </table>
    </div>
  );
}

export const ACTIONS_COLUMN: TableColumn = {
  label: "Actions",
  hidden: true,
  className: "cell-actions",
};
