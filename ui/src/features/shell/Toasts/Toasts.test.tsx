import { composeStories } from '@storybook/react'
import { act, render, screen } from '@testing-library/react'
import { expect, it } from 'vitest'
import { appStore } from '../../../store/store'
import * as stories from './Toasts.stories'

const { FromTheStore } = composeStories(stories)

it('announces what the store says, and lets it go', () => {
  render(<FromTheStore />)
  let id = 0
  act(() => {
    id = appStore.getState().ui.toast('Library scanned')
  })
  expect(screen.getByRole('status').textContent).toContain('Library scanned')
  act(() => screen.getAllByRole('button', { name: 'Dismiss' }).at(-1)?.click())
  expect(appStore.getState().ui.toasts.some((t) => t.id === id)).toBe(false)
})
