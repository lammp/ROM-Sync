import { Bar } from '../../atoms/Bar/Bar'
import { Button } from '../../atoms/Button/Button'
import { Lamp } from '../../atoms/Lamp/Lamp'
import { Pill } from '../../atoms/Pill/Pill'
import { DeviceFigures, type DeviceFiguresProps } from '../../molecules/DeviceFigures/DeviceFigures'
import { formatBytes } from '../../../lib/format/format'
import styles from './DeviceCard.module.css'

export type Space = { readonly total: number; readonly free: number } | null

/** What a device's transport is called on its card: version 1 called a volume a drive. */
export const TRANSPORT: Readonly<Record<string, string>> = {
  adb: 'ADB',
  mtp: 'MTP',
  volume: 'drive',
  fake: 'test device',
}

export type ProfileCard = {
  readonly variant: 'profile'
  readonly name: string
  readonly online: boolean
  readonly transport: string
  /** Online: the ROMs root. Offline: when it was last seen. */
  readonly roms: string
  readonly lastSeen: string
  readonly space: Space
  /** Null until the selection and the device's contents have been read. */
  readonly figures: DeviceFiguresProps | null
  readonly onSync: () => void
  readonly onContents: () => void
  readonly onChoose: () => void
}

export type CandidateState =
  /** The probe found it and could not read it; for ADB, the debugging prompt is waiting. */
  | { readonly kind: 'debugging'; readonly reason: string }
  /** It carries a marker written by another computer. */
  | { readonly kind: 'foreign'; readonly onAdopt: () => void }
  | { readonly kind: 'new'; readonly onNew: () => void }

export type CandidateCard = {
  readonly variant: 'candidate'
  readonly label: string
  readonly transport: string
  readonly space: Space
  readonly state: CandidateState
}

export type DeviceCardProps = ProfileCard | CandidateCard

const transportName = (t: string) => TRANSPORT[t] ?? t

function SpaceLine({ space, dim }: { space: Space; dim: boolean }) {
  if (!space) return <p className={styles.space}>capacity unknown</p>
  const used = space.total > 0 ? 1 - space.free / space.total : 0
  const text = `${formatBytes(space.free)} free of ${formatBytes(space.total)}`
  return (
    <>
      <p className={styles.space}>{text}</p>
      <Bar value={used} label="Space used" valueText={text} dim={dim} />
    </>
  )
}

/** When a device was last seen, to the minute, as version 1 wrote it. */
export function seenAt(iso: string): string {
  return iso.slice(0, 16).replace('T', ' ') || 'never'
}

function Candidate({ label, transport, space, state }: CandidateCard) {
  const blocked = state.kind === 'debugging'
  return (
    <article className={styles.card} aria-label={label}>
      <h2 className={styles.name}>
        <Lamp
          state={blocked ? 'bad' : 'on'}
          label={blocked ? `${label} cannot be read` : `${label} is connected`}
        />
        {label}
      </h2>
      <p className={styles.state}>{transportName(transport)}</p>
      <SpaceLine space={space} dim={false} />
      <p>
        {state.kind === 'debugging' ? (
          <Pill tone="warn">
            {transport === 'adb'
              ? `${state.reason}: accept the debugging prompt on the device`
              : state.reason}
          </Pill>
        ) : state.kind === 'foreign' ? (
          <Pill tone="warn">carries ROM-Sync.json from another computer</Pill>
        ) : (
          <Pill>no profile yet</Pill>
        )}
      </p>
      {state.kind !== 'debugging' && (
        <div className={styles.actions}>
          {state.kind === 'foreign' ? (
            <Button variant="primary" onClick={state.onAdopt}>
              Adopt profile
            </Button>
          ) : (
            <Button variant="primary" onClick={state.onNew}>
              New profile…
            </Button>
          )}
        </div>
      )}
    </article>
  )
}

function Profile(p: ProfileCard) {
  const where = p.online
    ? `online · ${transportName(p.transport)} · ROMs at ${p.roms}`
    : `offline · last seen ${seenAt(p.lastSeen)}`
  return (
    <article
      className={[styles.card, !p.online && styles.offline].filter(Boolean).join(' ')}
      aria-label={p.name}
    >
      <h2 className={styles.name}>
        <Lamp
          state={p.online ? 'on' : 'off'}
          label={p.online ? `${p.name} is connected` : `${p.name} is not connected`}
        />
        {p.name}
      </h2>
      <p className={styles.state}>{where}</p>
      <SpaceLine space={p.space} dim={!p.online} />
      {p.figures && <DeviceFigures {...p.figures} />}
      <div className={styles.actions}>
        <Button
          variant="primary"
          disabled={!p.online}
          title={p.online ? undefined : 'Connect this device to sync'}
          onClick={p.onSync}
        >
          Sync
        </Button>
        <Button onClick={p.onContents}>Contents</Button>
        <Button onClick={p.onChoose}>Choose games</Button>
      </div>
    </article>
  )
}

/**
 * A device on the devices page (F11-S31): a profile, online or not, with its
 * space, figures and three actions; or a candidate plugged in without one,
 * in one of three states: unreadable, carrying another computer's marker,
 * or new.
 */
export function DeviceCard(props: DeviceCardProps) {
  return props.variant === 'profile' ? <Profile {...props} /> : <Candidate {...props} />
}
