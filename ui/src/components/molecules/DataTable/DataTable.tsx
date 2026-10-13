import type { ReactNode } from 'react'
import styles from './DataTable.module.css'

export type Column<R> = {
  readonly key: string
  readonly label: string
  /** Right aligned in tabular figures. */
  readonly numeric?: boolean
  readonly cell: (row: R) => ReactNode
}

export type DataTableProps<R> = {
  /** Names the table for assistive technology. */
  readonly caption: string
  readonly columns: readonly Column<R>[]
  readonly rows: readonly R[]
  readonly rowKey: (row: R) => string
  readonly empty?: ReactNode
}

/** A plain data table: column headers, cells, numbers aligned. */
export function DataTable<R>({ caption, columns, rows, rowKey, empty }: DataTableProps<R>) {
  return (
    <table className={styles.table}>
      <caption className={styles.caption}>{caption}</caption>
      <thead>
        <tr>
          {columns.map((c) => (
            <th key={c.key} scope="col" className={c.numeric ? styles.num : undefined}>
              {c.label}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.length === 0 && empty ? (
          <tr>
            <td colSpan={columns.length} className={styles.empty}>
              {empty}
            </td>
          </tr>
        ) : (
          rows.map((r) => (
            <tr key={rowKey(r)}>
              {columns.map((c) => (
                <td key={c.key} className={c.numeric ? styles.num : undefined}>
                  {c.cell(r)}
                </td>
              ))}
            </tr>
          ))
        )}
      </tbody>
    </table>
  )
}
