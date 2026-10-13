/** F11-S11: every field any atom draws is named by a label tied to it. */
import { render } from '@testing-library/react'
import { createElement } from 'react'
import { describe, expect, it } from 'vitest'
import { allStories } from './stories'

const FIELDS = 'input, select, textarea'

type Field = HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement

/** A label element tied to the field, or a name it is labelled by; a placeholder is neither. */
function labelled(field: Field): boolean {
  const byLabel = [...(field.labels ?? [])].some((l) => (l.textContent ?? '').trim() !== '')
  const byRef = (field.getAttribute('aria-labelledby') ?? '')
    .split(/\s+/)
    .filter(Boolean)
    .some((id) => (field.ownerDocument.getElementById(id)?.textContent ?? '').trim() !== '')
  const byName = (field.getAttribute('aria-label') ?? '').trim() !== ''
  return byLabel || byRef || byName
}

export function unlabelled(root: Element): string[] {
  return [...root.querySelectorAll<Field>(FIELDS)]
    .filter((el) => !labelled(el))
    .map((el) => `${el.tagName.toLowerCase()}[type=${el.getAttribute('type') ?? ''}]`)
}

describe('labels', () => {
  it('no_unlabelled_input', () => {
    let fields = 0
    for (const { name, Story } of allStories()) {
      const { container, unmount } = render(createElement(Story))
      fields += container.querySelectorAll(FIELDS).length
      expect(unlabelled(container), name).toEqual([])
      unmount()
    }
    expect(fields).toBeGreaterThanOrEqual(6)
  })

  it('accepts each way of tying a label, and refuses an empty one', () => {
    const { container } = render(
      createElement(
        'div',
        null,
        createElement('label', { htmlFor: 'a' }, 'Store'),
        createElement('input', { id: 'a' }),
        createElement('span', { id: 'n' }, 'Rating'),
        createElement('input', { 'aria-labelledby': 'n' }),
        createElement('select', { 'aria-label': 'Sort' }),
        createElement('label', null, ' ', createElement('input', { type: 'checkbox' })),
      ),
    )
    expect(unlabelled(container)).toEqual(['input[type=checkbox]'])
  })

  it('catches a field named only by its placeholder', () => {
    const { container } = render(createElement('input', { type: 'text', placeholder: 'Search' }))
    expect(unlabelled(container)).toEqual(['input[type=text]'])
  })
})
