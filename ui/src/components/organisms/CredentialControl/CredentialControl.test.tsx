import { composeStories } from '@storybook/react'
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { savedOn, testWords } from './CredentialControl'
import * as stories from './CredentialControl.stories'

const { Saved, Imported, Unset, Typing, Removing, Tested, TestedThenEdited } =
  composeStories(stories)

describe('CredentialControl', () => {
  it('describes a saved secret without any of it, and offers Replace and Remove', () => {
    render(<Saved />)
    expect(screen.getByText('Saved 8 Oct 2026 · 30 characters · not shown again')).toBeTruthy()
    expect(document.querySelector('input[type="password"]')).toBeNull()
    fireEvent.click(screen.getByRole('button', { name: 'Remove' }))
    expect(Saved.args.onDraft).toHaveBeenCalledWith({ kind: 'remove' })
    fireEvent.change(screen.getByRole('textbox', { name: 'Twitch client ID' }), {
      target: { value: 'x' },
    })
    expect(Saved.args.onClientId).toHaveBeenCalledWith('x')
  })

  it('says where an imported secret came from', () => {
    render(<Imported />)
    expect(screen.getByText(/imported from RomCurator/)).toBeTruthy()
  })

  it('says what is missing without credentials, and adds them', () => {
    render(<Unset />)
    expect(screen.getByText(/^Not set\./)).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: 'Add credentials' }))
    expect(Unset.args.onDraft).toHaveBeenCalledWith({ kind: 'typed', text: '' })
  })

  it('takes a new secret in a password field, warns when short, and can go back', () => {
    render(<Typing />)
    const field = screen.getByLabelText('New client secret') as HTMLInputElement
    expect(field.type).toBe('password')
    expect(screen.getByText('That is shorter than a Twitch secret usually is.')).toBeTruthy()
    fireEvent.change(field, { target: { value: 'a-much-longer-secret-typed' } })
    expect(Typing.args.onDraft).toHaveBeenCalledWith({
      kind: 'typed',
      text: 'a-much-longer-secret-typed',
    })
    fireEvent.click(screen.getByRole('button', { name: 'Keep the saved one' }))
    expect(Typing.args.onDraft).toHaveBeenLastCalledWith({ kind: 'keep' })
  })

  it('says a removal waits for the save', () => {
    render(<Removing />)
    expect(screen.getByText('Will be removed when this section is saved.')).toBeTruthy()
  })

  it('says which stage of the test failed, and when a result is stale', () => {
    render(<Tested />)
    expect(screen.getByRole('status').textContent).toBe(
      'token failed: Twitch rejected the credentials',
    )
    render(<TestedThenEdited />)
    expect(screen.getByText('(edited since; test again)', { exact: false })).toBeTruthy()
  })

  it('words dates and results', () => {
    expect([savedOn(null), savedOn('2026-10-08T04:11:00+00:00'), savedOn('soon')]).toEqual([
      '',
      '8 Oct 2026',
      'soon',
    ])
    expect(
      testWords({
        ok: true,
        failedAt: null,
        stages: [{ name: 'token', outcome: 'ok', message: null }],
      }),
    ).toEqual({
      tone: 'ok',
      text: 'connected: token ok',
    })
    expect(testWords({ ok: false, failedAt: 'missing', stages: [] })).toEqual({
      tone: 'bad',
      text: 'missing failed',
    })
  })
})
