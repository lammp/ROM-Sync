import { Button } from '../../atoms/Button/Button'
import styles from './GridListToggle.module.css'

export type View = 'grid' | 'list'

const VIEWS: readonly { readonly value: View; readonly label: string }[] = [
  { value: 'grid', label: 'Grid' },
  { value: 'list', label: 'List' },
]

/** Grid or list: two toggles, one pressed. */
export function GridListToggle({
  value,
  onChange,
}: {
  value: View
  onChange: (view: View) => void
}) {
  return (
    <span className={styles.toggle} role="group" aria-label="View">
      {VIEWS.map((v) => (
        <Button
          key={v.value}
          small
          active={v.value === value}
          onClick={() => v.value !== value && onChange(v.value)}
        >
          {v.label}
        </Button>
      ))}
    </span>
  )
}
