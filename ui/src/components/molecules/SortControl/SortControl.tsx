import { Select } from '../../atoms/Select/Select'

/** Version 1's six orders, by name. */
export const SORT_OPTIONS = [
  { value: 'title', label: 'Title' },
  { value: 'year', label: 'Newest' },
  { value: 'rating', label: 'Rating' },
  { value: 'size', label: 'Largest' },
  { value: 'system', label: 'System' },
  { value: 'mtime', label: 'Recently added' },
] as const

export type SortValue = (typeof SORT_OPTIONS)[number]['value']

/** The library's order. */
export function SortControl({
  value,
  onChange,
}: {
  value: string
  onChange: (value: SortValue) => void
}) {
  return (
    <Select
      label="Sort"
      options={SORT_OPTIONS}
      value={value}
      onChange={(v) => onChange(v as SortValue)}
    />
  )
}
