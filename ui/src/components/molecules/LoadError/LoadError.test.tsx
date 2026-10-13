import { composeStories } from '@storybook/react'
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import * as stories from './LoadError.stories'

const { Failed, Retrying } = composeStories(stories)

describe('LoadError', () => {
  it('says what could not be read and why, as an alert, and retries', () => {
    render(<Failed />)
    expect(screen.getByRole('alert').textContent).toBe(
      'could not read the libraryThe engine did not answer.Retry',
    )
    fireEvent.click(screen.getByRole('button', { name: 'Retry' }))
    expect(Failed.args.onRetry).toHaveBeenCalledTimes(1)
  })

  it('cannot retry twice at once', () => {
    render(<Retrying />)
    expect(screen.getByRole('button', { name: 'Retrying…' }).hasAttribute('disabled')).toBe(true)
  })
})
