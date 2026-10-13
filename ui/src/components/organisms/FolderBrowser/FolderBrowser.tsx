import { useState } from 'react'
import { Button } from '../../atoms/Button/Button'
import { Spinner } from '../../atoms/Spinner/Spinner'
import { Modal } from '../Modal/Modal'
import styles from './FolderBrowser.module.css'

export type FolderEntry = { readonly name: string; readonly path: string }

export type FolderListing = {
  /** The folder shown; null for the list of drives. */
  readonly path: string | null
  /** The folder above; null at a drive's root, where up is the list of drives. */
  readonly parent: string | null
  readonly folders: readonly FolderEntry[]
  readonly files: readonly FolderEntry[]
}

export type FolderBrowserProps = {
  /** What is being chosen: "Choose the store folder". */
  readonly title: string
  readonly kind: 'folder' | 'file'
  /** The folder shown, once the engine has listed it. */
  readonly listing?: FolderListing
  readonly loading?: boolean
  /** Why the folder asked for could not be listed. */
  readonly error?: string
  /** Opens a folder; null opens the list of drives. */
  readonly onOpen: (path: string | null) => void
  readonly onChoose: (path: string) => void
  readonly onCancel: () => void
}

/**
 * Choosing a folder or a file by browsing this computer (F11-S45), where the
 * window's own dialog cannot be opened. It starts at the drives or at the
 * current choice, opens one folder at a time, and goes up. A folder is chosen
 * as the one shown; a file is chosen by selecting it. It closes as every
 * dialog does: its close button, Escape, a click outside, or Cancel.
 */
export function FolderBrowser({
  title,
  kind,
  listing,
  loading = false,
  error,
  onOpen,
  onChoose,
  onCancel,
}: FolderBrowserProps) {
  const [file, setFile] = useState<string | null>(null)
  const here = listing?.path ?? null
  const open = (path: string | null) => {
    setFile(null)
    onOpen(path)
  }
  const chosen = kind === 'folder' ? here : file
  return (
    <Modal title={title} onClose={onCancel}>
      <div className={styles.where}>
        <Button small disabled={!here} onClick={() => open(listing?.parent ?? null)}>
          Up
        </Button>
        <span className={styles.path} aria-live="polite">
          {here ?? 'This computer'}
        </span>
        {loading && <Spinner label="Listing" />}
      </div>
      {error ? (
        <p className={styles.error} role="alert">
          {error}{' '}
          <Button small onClick={() => open(null)}>
            Show the drives
          </Button>
        </p>
      ) : (
        <ul className={styles.list} aria-label={here ? `In ${here}` : 'Drives'}>
          {listing?.folders.map((f) => (
            <li key={f.path}>
              <button type="button" className={styles.entry} onClick={() => open(f.path)}>
                <span aria-hidden="true" className={styles.glyph}>
                  ▸
                </span>
                {f.name}
              </button>
            </li>
          ))}
          {kind === 'file' &&
            listing?.files.map((f) => (
              <li key={f.path}>
                <button
                  type="button"
                  className={[styles.entry, styles.file].join(' ')}
                  aria-pressed={file === f.path}
                  onClick={() => setFile(f.path)}
                >
                  {f.name}
                </button>
              </li>
            ))}
          {listing &&
            !loading &&
            listing.folders.length === 0 &&
            (kind === 'folder' || listing.files.length === 0) && (
              <li className={styles.empty}>
                {kind === 'folder'
                  ? 'No folders in here.'
                  : 'No folders or matching files in here.'}
              </li>
            )}
        </ul>
      )}
      <div className={styles.actions}>
        <Button onClick={onCancel}>Cancel</Button>
        <Button variant="primary" disabled={!chosen} onClick={() => chosen && onChoose(chosen)}>
          {kind === 'folder' ? 'Choose this folder' : 'Choose this file'}
        </Button>
      </div>
    </Modal>
  )
}
