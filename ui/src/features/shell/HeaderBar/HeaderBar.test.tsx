import { composeStories } from '@storybook/react'
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { appStore } from '../../../store/store'
import { routeOf } from './HeaderBar'
import * as stories from './HeaderBar.stories'

const push = vi.fn()
vi.mock('next/navigation', () => ({ usePathname: () => '/devices/', useRouter: () => ({ push }) }))

const { OnTheLibrary } = composeStories(stories)

describe('HeaderBar', () => {
  it('reads a route without the export trailing slash', () => {
    expect(['/', '', null, '/devices/', '/devices', '/system-files/'].map(routeOf)).toEqual([
      '/',
      '/',
      '/',
      '/devices',
      '/devices',
      '/system-files',
    ])
  })

  it('marks the view on screen and lists the profiles', async () => {
    render(<OnTheLibrary />)
    expect(screen.getByRole('link', { name: 'Devices' }).getAttribute('aria-current')).toBe('page')
    expect(await screen.findByRole('option', { name: 'Thor' })).toBeTruthy()
  })

  it('takes a search to the library from any other view', () => {
    render(<OnTheLibrary />)
    fireEvent.change(screen.getByRole('searchbox'), { target: { value: 'quest' } })
    expect(appStore.getState().filters.query).toBe('quest')
    expect(push).toHaveBeenCalledWith('/')
  })
})
