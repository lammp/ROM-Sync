/**
 * F11-S10: everything that acts on a click is a control the keyboard reaches.
 * React keeps each element's props on the node; any element carrying a
 * pointer handler must be a native control, and no control may be taken out
 * of the tab order.
 */
import { render } from '@testing-library/react'
import { createElement } from 'react'
import { describe, expect, it } from 'vitest'
import { allStories } from './stories'

const CONTROLS = new Set(['BUTTON', 'A', 'INPUT', 'SELECT', 'TEXTAREA', 'SUMMARY', 'LABEL'])
const POINTER = [
  'onClick',
  'onMouseDown',
  'onMouseUp',
  'onPointerDown',
  'onPointerUp',
  'onDoubleClick',
]

function props(el: Element): Record<string, unknown> {
  const key = Object.keys(el).find((k) => k.startsWith('__reactProps$'))
  return key ? ((el as unknown as Record<string, Record<string, unknown>>)[key] ?? {}) : {}
}

export function inoperable(root: Element): string[] {
  return [...root.querySelectorAll('*')].flatMap((el) => {
    const p = props(el)
    const handled = POINTER.filter((h) => typeof p[h] === 'function')
    const out: string[] = []
    if (handled.length > 0 && !CONTROLS.has(el.tagName))
      out.push(`${el.tagName.toLowerCase()} handles ${handled.join(', ')}`)
    if (CONTROLS.has(el.tagName) && el.tagName !== 'LABEL' && el.getAttribute('tabindex') === '-1')
      out.push(`${el.tagName.toLowerCase()} is out of the tab order`)
    return out
  })
}

describe('keyboard', () => {
  it('finds every atom story', () => {
    expect(allStories().length).toBeGreaterThanOrEqual(26)
  })

  it('all_atoms_operable', () => {
    for (const { name, Story } of allStories()) {
      const { container, unmount } = render(createElement(Story))
      expect(inoperable(container), name).toEqual([])
      unmount()
    }
  })

  it('catches a clickable span and a control taken out of the tab order', () => {
    const { container } = render(
      createElement(
        'div',
        null,
        createElement('span', { onClick: () => undefined }, 'clear'),
        createElement('button', { type: 'button', tabIndex: -1 }, 'hidden'),
      ),
    )
    expect(inoperable(container)).toEqual([
      'span handles onClick',
      'button is out of the tab order',
    ])
  })
})
