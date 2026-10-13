import { composeStories } from '@storybook/react'
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { testState, testWords } from './CredentialControl'
import * as stories from './CredentialControl.stories'

const { Saved, Imported, Unset, Testing, Passed, Failed, TestedThenEdited } =
  composeStories(stories)

const glyph = () =>
  screen
    .getByRole('button', { name: 'Test connection' })
    .querySelector('svg')
    ?.getAttribute('data-icon')

describe('CredentialControl', () => {
  it('locks both saved values, each with its own way to change it', () => {
    render(<Saved />)
    const id = screen.getByRole('textbox', { name: 'Twitch client ID' }) as HTMLInputElement
    expect(id.readOnly).toBe(true)
    expect((screen.getByLabelText('Client secret') as HTMLInputElement).readOnly).toBe(true)
    expect(screen.getByText(/Saved 8 Oct 2026 · 30 characters/)).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Remove the saved client secret' }))
    expect(Saved.args.onDraft).toHaveBeenCalledWith({ kind: 'remove' })
  })

  it('says where an imported secret came from', () => {
    render(<Imported />)
    expect(screen.getByText(/imported from RomCurator/)).toBeTruthy()
  })

  it('leaves both open when nothing is saved', () => {
    render(<Unset />)
    fireEvent.change(screen.getByRole('textbox', { name: 'Twitch client ID' }), {
      target: { value: 'x' },
    })
    expect(Unset.args.onClientId).toHaveBeenCalledWith('x')
    expect((screen.getByLabelText('Client secret') as HTMLInputElement).readOnly).toBe(false)
  })

  it('turns while testing, then shows a tick or a cross with the outcome in words', () => {
    const { unmount } = render(<Testing />)
    expect(glyph()).toBe('recycle')
    expect(screen.getByRole('button', { name: 'Test connection' }).getAttribute('aria-busy')).toBe(
      'true',
    )
    unmount()
    const passed = render(<Passed />)
    expect(glyph()).toBe('tick')
    expect(screen.getByRole('status').textContent).toBe('connected: token, api ok')
    passed.unmount()
    render(<Failed />)
    expect(glyph()).toBe('cross')
    expect(screen.getByRole('status').textContent).toBe(
      'token failed: Twitch rejected the credentials',
    )
  })

  it('drops the outcome from the button once the fields change', () => {
    render(<TestedThenEdited />)
    expect(glyph()).toBe('recycle')
    expect(screen.getByText('(edited since; test again)', { exact: false })).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Test connection' }))
    expect(TestedThenEdited.args.onTest).toHaveBeenCalledOnce()
  })

  it('words results and states', () => {
    expect(
      testWords({
        ok: true,
        failedAt: null,
        stages: [{ name: 'token', outcome: 'ok', message: null }],
      }),
    ).toEqual({ tone: 'ok', text: 'connected: token ok' })
    expect(testWords({ ok: false, failedAt: 'missing', stages: [] })).toEqual({
      tone: 'bad',
      text: 'missing failed',
    })
    expect(testState({ result: null, running: false, stale: false })).toBe('idle')
  })
})
