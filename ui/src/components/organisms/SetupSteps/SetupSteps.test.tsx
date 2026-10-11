import { composeStories } from '@storybook/react'
import { fireEvent, render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import * as stories from './SetupSteps.stories'

const { Incomplete, Complete } = composeStories(stories)

describe('SetupSteps', () => {
  it('setup_steps: lists the steps in first-run order, each done or to do, with an action for what is left', () => {
    render(<Incomplete />)
    const steps = within(screen.getByRole('list', { name: 'Setup' })).getAllByRole('listitem')
    expect(steps.map((s) => s.textContent)).toEqual([
      '1. Point at your ROMs folder done',
      '2. Read the library to doRescan store',
      '3. Add IGDB credentials for covers and details to dolibretro box art needs no account.Go to Metadata',
    ])
    fireEvent.click(screen.getByRole('button', { name: 'Go to Metadata' }))
    expect(Incomplete.args.steps?.[2]?.action.onClick).toHaveBeenCalled()
  })

  it('collapses to one dismissible line once every step is done', () => {
    render(<Complete />)
    expect(screen.getByRole('status').textContent).toContain('Setup complete.')
    fireEvent.click(screen.getByRole('button', { name: 'Dismiss' }))
    expect(Complete.args.onDismiss).toHaveBeenCalled()
  })
})
