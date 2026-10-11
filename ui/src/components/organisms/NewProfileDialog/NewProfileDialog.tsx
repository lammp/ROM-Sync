import { useState } from 'react'
import { Button } from '../../atoms/Button/Button'
import { Checkbox } from '../../atoms/Checkbox/Checkbox'
import { KeyValueText } from '../../atoms/KeyValueText/KeyValueText'
import { Muted } from '../../atoms/Muted/Muted'
import { TextInput } from '../../atoms/TextInput/TextInput'
import { Modal } from '../Modal/Modal'
import styles from './NewProfileDialog.module.css'

export type NewProfileDialogProps = {
  /** The device as the probe described it. */
  readonly device: string
  /** Where its ROMs will be kept: the destination's own root. */
  readonly root: string
  /** A volume is a drive; anything else is a device. */
  readonly drive: boolean
  readonly busy?: boolean
  readonly error?: string
  readonly onCreate: (name: string, writeMarker: boolean) => void
  readonly onCancel: () => void
}

/**
 * Makes a profile for a device plugged in without one (F11-S31): a name, the
 * folder its ROMs go in, and whether the marker is written. Version 1 asked a
 * native confirm after the dialog; here the dialog says what will happen and
 * Create is the confirmation (SPEC section 10).
 */
export function NewProfileDialog({
  device,
  root,
  drive,
  busy = false,
  error,
  onCreate,
  onCancel,
}: NewProfileDialogProps) {
  const [name, setName] = useState('')
  const [marker, setMarker] = useState(true)
  const where = drive ? 'drive' : 'device'
  const named = name.trim()
  return (
    <Modal title="New device profile" onClose={onCancel}>
      <form
        className={styles.form}
        onSubmit={(e) => {
          e.preventDefault()
          if (named && !busy) onCreate(named, marker)
        }}
      >
        <Muted>{device}</Muted>
        <TextInput
          label="Name"
          value={name}
          onChange={setName}
          placeholder="e.g. AYN Thor, Steam Deck SD card"
          error={error}
        />
        <p className={styles.root}>
          ROMs folder on the {where} (ES-DE layout): <KeyValueText>{root}</KeyValueText>
          <br />
          <Muted>Created there if it does not exist.</Muted>
        </p>
        <Checkbox
          label={`Write ROM-Sync.json to the ${where} so it is recognised anywhere`}
          checked={marker}
          onChange={setMarker}
        />
        <p className={styles.consequence}>
          {named
            ? `Creates the profile “${named}” with its ROMs at ${root} on this ${where}.${marker ? ' ROM-Sync.json will be written there.' : ''}`
            : 'Name the profile to create it.'}
        </p>
        <div className={styles.actions}>
          <Button type="button" onClick={onCancel}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" disabled={!named || busy}>
            {busy ? 'Creating…' : 'Create'}
          </Button>
        </div>
      </form>
    </Modal>
  )
}
