import { useState } from 'react'
import { Button } from '../../atoms/Button/Button'
import { TextInput } from '../../atoms/TextInput/TextInput'
import styles from './TagAdd.module.css'

export type NewTag = { readonly tag: string; readonly kind: string }

/** "franchise: Mortal Kombat" names its kind; anything else is a user tag. Blank is nothing. */
export function parseTag(text: string): NewTag | null {
  const v = text.trim()
  if (!v) return null
  const m = /^(franchise|theme|genre)\s*:\s*(.+)$/i.exec(v)
  return m
    ? { kind: (m[1] ?? '').toLowerCase(), tag: (m[2] ?? '').trim() }
    : { kind: 'user', tag: v }
}

/** Adds a tag by hand. */
export function TagAdd({ onAdd }: { onAdd: (tag: NewTag) => void }) {
  const [text, setText] = useState('')
  const add = () => {
    const tag = parseTag(text)
    if (!tag) return
    onAdd(tag)
    setText('')
  }
  return (
    <form
      className={styles.tagadd}
      onSubmit={(e) => {
        e.preventDefault()
        add()
      }}
    >
      <TextInput
        label="Add a tag"
        hideLabel
        value={text}
        placeholder="add a tag (e.g. franchise: Mortal Kombat)"
        onChange={setText}
      />
      <Button type="submit" disabled={!text.trim()}>
        Add
      </Button>
    </form>
  )
}
