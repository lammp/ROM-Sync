import styles from './Icon.module.css'

/** Each glyph as one 24-unit path, drawn in the text's colour. */
const PATHS = {
  edit: 'M3 17.25V21h3.75L17.8 9.94l-3.75-3.75L3 17.25Zm17.7-10.2a1 1 0 0 0 0-1.42l-2.33-2.33a1 1 0 0 0-1.42 0l-1.83 1.83 3.75 3.75 1.83-1.83Z',
  eye: 'M12 5C6.5 5 2.7 9.4 1.5 12c1.2 2.6 5 7 10.5 7s9.3-4.4 10.5-7C21.3 9.4 17.5 5 12 5Zm0 11.5a4.5 4.5 0 1 1 0-9 4.5 4.5 0 0 1 0 9Zm0-2.5a2 2 0 1 0 0-4 2 2 0 0 0 0 4Z',
  'eye-off':
    'M3.3 2.3 2 3.6l3.1 3.1C3.4 8.1 2.2 9.8 1.5 12c1.2 2.6 5 7 10.5 7 1.9 0 3.6-.5 5-1.3l3.4 3.4 1.3-1.3L3.3 2.3ZM12 16.5A4.5 4.5 0 0 1 7.5 12c0-.8.2-1.5.6-2.2l1.5 1.5a2.5 2.5 0 0 0 3.1 3.1l1.5 1.5c-.7.4-1.4.6-2.2.6ZM12 5c-1.2 0-2.3.2-3.3.6l2 2A4.5 4.5 0 0 1 16.4 13l3.2 3.2c1.3-1.2 2.3-2.7 2.9-4.2C21.3 9.4 17.5 5 12 5Z',
  remove: 'M6 7h12l-1 14H7L6 7Zm3-4h6l1 2h4v2H4V5h4l1-2Z',
  undo: 'M12.5 8c-2.6 0-5 1-6.9 2.6L2 7v9h9l-3.6-3.6a7.5 7.5 0 0 1 12 3.4l2.4-.8A10 10 0 0 0 12.5 8Z',
  tick: 'M9 16.2 4.8 12l-1.4 1.4L9 19 21 7l-1.4-1.4L9 16.2Z',
  cross:
    'M19 6.4 17.6 5 12 10.6 6.4 5 5 6.4 10.6 12 5 17.6 6.4 19 12 13.4 17.6 19 19 17.6 13.4 12 19 6.4Z',
  recycle:
    'M12 4a8 8 0 0 0-7.4 5H2l3.5 4L9 9H6.8A6 6 0 0 1 18 10h2.1A8 8 0 0 0 12 4Zm6.5 7L15 15h2.2A6 6 0 0 1 6 14H3.9a8 8 0 0 0 15.5 1H22l-3.5-4Z',
  folder: 'M10 4H4a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-8l-2-2Z',
  open: 'M14 3v2h3.6l-9.8 9.8 1.4 1.4L19 6.4V10h2V3h-7ZM5 5h6V3H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-6h-2v6H5V5Z',
  download: 'M5 20h14v-2H5v2Zm7-3 6-6-1.4-1.4L13 13.2V4h-2v9.2L7.4 9.6 6 11l6 6Z',
  play: 'M8 5v14l11-7L8 5Z',
  stop: 'M6 6h12v12H6V6Z',
} as const

export type IconName = keyof typeof PATHS

export const ICONS = Object.keys(PATHS) as IconName[]

export type IconProps = {
  readonly name: IconName
  readonly size?: number
  /** Turning, for work under way; still where motion is reduced. */
  readonly turning?: boolean
  /** A tone besides the text's own; the words beside it say the same. */
  readonly tone?: 'ok' | 'bad'
}

/**
 * One glyph, always beside words or inside a named button: it is decoration
 * to assistive technology, so it is hidden from it (F11-S51).
 */
export function Icon({ name, size = 16, turning = false, tone }: IconProps) {
  return (
    <svg
      className={[styles.icon, turning && styles.turning, tone && styles[tone]]
        .filter(Boolean)
        .join(' ')}
      viewBox="0 0 24 24"
      width={size}
      height={size}
      aria-hidden="true"
      focusable="false"
      data-icon={name}
    >
      <path fill="currentColor" d={PATHS[name]} />
    </svg>
  )
}
