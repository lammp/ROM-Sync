import type { ReactNode } from 'react'
import { Button } from '../../atoms/Button/Button'
import { Modal } from '../Modal/Modal'
import styles from './ConfirmDialog.module.css'

export type ConfirmDialogProps = {
  readonly title: string
  readonly children: ReactNode
  readonly confirm: string
  /** The confirmation removes or overwrites something. */
  readonly danger?: boolean
  readonly onConfirm: () => void
  readonly onCancel: () => void
}

/** A yes or no question in a dialog. Cancel has focus first, so Enter does no harm. */
export function ConfirmDialog({
  title,
  children,
  confirm,
  danger = false,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  return (
    <Modal title={title} onClose={onCancel}>
      <div className={styles.body}>{children}</div>
      <div className={styles.actions}>
        <Button onClick={onCancel}>Cancel</Button>
        <Button variant={danger ? 'danger' : 'primary'} onClick={onConfirm}>
          {confirm}
        </Button>
      </div>
    </Modal>
  )
}
