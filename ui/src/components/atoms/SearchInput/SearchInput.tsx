import { useId } from 'react'
import styles from './SearchInput.module.css'

export type SearchInputProps = {
  readonly value: string
  readonly onChange: (value: string) => void
  /** Announced, not drawn: the field's placeholder shows its purpose. */
  readonly label?: string
  readonly placeholder?: string
}

/** The library search field, drawn as a pill. */
export function SearchInput({
  value,
  onChange,
  label = 'Search the library',
  placeholder = 'Search: title, system:snes, year>1995, rating>=80',
}: SearchInputProps) {
  const id = useId()
  return (
    <>
      <label htmlFor={id} className={styles.hidden}>
        {label}
      </label>
      <input
        id={id}
        type="search"
        className={styles.search}
        value={value}
        placeholder={placeholder}
        autoComplete="off"
        spellCheck={false}
        onChange={(e) => onChange(e.target.value)}
      />
    </>
  )
}
