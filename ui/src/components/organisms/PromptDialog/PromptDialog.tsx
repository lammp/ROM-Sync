import { useState } from 'react'
import { Button } from '../../atoms/Button/Button'
import { TextInput } from '../../atoms/TextInput/TextInput'
import { Modal } from '../Modal/Modal'
import styles from './PromptDialog.module.css'

export type PromptDialogProps = {
  readonly title: string
  readonly label: string
  readonly initial?: string
  readonly submit: string
  readonly onSubmit: (value: string) => void
  readonly onCancel: () => void
}

/** Asks for one line of text, replacing version 1's prompt(). Blank is not an answer. */
export function PromptDialog({
  title,
  label,
  initial = '',
  submit,
  onSubmit,
  onCancel,
}: PromptDialogProps) {
  const [value, setValue] = useState(initial)
  return (
    <Modal title={title} onClose={onCancel} initialFocus="input">
      <form
        onSubmit={(e) => {
          e.preventDefault()
          if (value.trim()) onSubmit(value.trim())
        }}
      >
        <TextInput label={label} value={value} onChange={setValue} />
        <div className={styles.actions}>
          <Button onClick={onCancel}>Cancel</Button>
          <Button type="submit" variant="primary" disabled={!value.trim()}>
            {submit}
          </Button>
        </div>
      </form>
    </Modal>
  )
}
