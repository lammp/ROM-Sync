import { composeStories } from '@storybook/react'
import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import * as stories from './DevicesPage.stories'

const params = { query: '' }
vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn() }),
  useSearchParams: () => new URLSearchParams(params.query),
}))

const { Every, One } = composeStories(stories)

describe('DevicesPage', () => {
  it('search_param_route: lists every device without an id', async () => {
    params.query = ''
    render(<Every />)
    expect(await screen.findByRole('heading', { name: /^Devices/ })).toBeTruthy()
  })

  it('search_param_route: shows the one device an id names', async () => {
    params.query = 'id=dev-1'
    render(<One />)
    expect(await screen.findByRole('heading', { name: /^Thor/ })).toBeTruthy()
    expect(screen.queryByRole('list', { name: 'Devices' })).toBeNull()
  })
})
