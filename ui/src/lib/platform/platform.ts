/**
 * Who hosts the page and what it may ask of the computer (F12-S3). The engine
 * reports both; the page never sniffs them from the browser.
 */

/** Who hosts the page, as `/session` names it. */
export type ShellKind = 'desktop' | 'browser'
/**
 * A shell action, as `/session` names it. Kept beside the session type rather
 * than imported from it (lib sits below the API client); a capability the
 * engine adds and this list lacks fails the type check in `useShell`.
 */
export type Capability = 'reveal' | 'pick_folder' | 'open_url'
export type Shell = { readonly kind: ShellKind; readonly capabilities: readonly Capability[] }

/** Until the engine answers, the page assumes the least: a browser that can ask nothing. */
export const BROWSER: Shell = { kind: 'browser', capabilities: [] }

/** Whether the page may offer an action: only one the engine said answers here. */
export const can = (shell: Shell, action: Capability): boolean =>
  shell.capabilities.includes(action)

/** Where the page is running, in words. */
export const hostOf = (shell: Shell): string =>
  shell.kind === 'desktop' ? 'desktop window' : 'browser'

/** The part of a session that describes the shell, without its token. */
export const shellOf = (session: {
  readonly kind: ShellKind
  readonly capabilities: readonly Capability[]
}): Shell => ({
  kind: session.kind,
  capabilities: session.capabilities,
})
