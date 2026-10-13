import { composeStories } from '@storybook/react'
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import * as stories from './StatusButton.stories'

const { Idle, Running, Passed, Failed, Main } = composeStories(stories)

const glyph = () =>
  screen.getByRole('button', { name: /./ }).querySelector('svg')?.getAttribute('data-icon')

describe('StatusButton', () => {
  it('runs on a click, named by its words', () => {
    render(<Idle />)
    fireEvent.click(screen.getByRole('button', { name: 'Test connection' }))
    expect(Idle.args.onClick).toHaveBeenCalledOnce()
    expect(glyph()).toBe('recycle')
  })

  it('turns and waits while running', () => {
    render(<Running />)
    const button = screen.getByRole('button', { name: 'Test connection' })
    expect((button as HTMLButtonElement).disabled).toBe(true)
    expect(button.getAttribute('aria-busy')).toBe('true')
    expect(button.querySelector('svg')?.getAttribute('class')).toMatch(/turning/)
  })

  it('shows a tick when it passed and a cross when it failed, keeping its name', () => {
    const { unmount } = render(<Passed />)
    expect(glyph()).toBe('tick')
    expect(screen.getByRole('button', { name: 'Test connection' }).dataset.state).toBe('passed')
    unmount()
    render(<Failed />)
    expect(glyph()).toBe('cross')
  })

  it('draws its own glyph as a main action', () => {
    render(<Main />)
    expect(screen.getByRole('button', { name: 'Run Initial' })).toBeTruthy()
    expect(glyph()).toBe('play')
  })
})
