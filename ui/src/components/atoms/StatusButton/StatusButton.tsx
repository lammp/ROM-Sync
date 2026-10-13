import { Button, type ButtonVariant } from '../Button/Button'
import { Icon, type IconName } from '../Icon/Icon'

/** Where the work a button starts stands: not run, running, or its last outcome. */
export type RunState = 'idle' | 'running' | 'passed' | 'failed'

export type StatusButtonProps = {
  /** The words on it, which are also its name: "Test connection". */
  readonly label: string
  readonly state?: RunState
  /** The glyph while idle; the recycle glyph unless something says the action better. */
  readonly icon?: IconName
  readonly variant?: ButtonVariant
  /** A tab's main action, drawn larger at its top. */
  readonly large?: boolean
  readonly small?: boolean
  readonly disabled?: boolean
  /** Why it cannot be pressed, when it cannot. */
  readonly title?: string
  readonly onClick: () => void
}

/**
 * A button that runs something and shows how it went (F11-S51): its glyph
 * turns while the work runs, then becomes a tick when it passed or a cross
 * when it failed. The words stay, so the shape and the words carry the
 * outcome, never the colour alone; what happened is said beside it.
 */
export function StatusButton({
  label,
  state = 'idle',
  icon = 'recycle',
  variant,
  large,
  small,
  disabled,
  title,
  onClick,
}: StatusButtonProps) {
  const running = state === 'running'
  return (
    <Button
      variant={variant}
      large={large}
      small={small}
      disabled={disabled || running}
      title={title}
      aria-busy={running || undefined}
      data-state={state}
      onClick={onClick}
    >
      {state === 'passed' ? (
        <Icon name="tick" tone="ok" />
      ) : state === 'failed' ? (
        <Icon name="cross" tone="bad" />
      ) : (
        <Icon name={running ? 'recycle' : icon} turning={running} />
      )}
      {label}
    </Button>
  )
}
