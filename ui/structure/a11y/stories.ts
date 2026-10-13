/**
 * Every story of every atom, composed and ready to render, for the checks
 * that hold across the whole layer rather than within one component.
 */
import { composeStories } from '@storybook/react'
import type { ComponentType } from 'react'

type StoryModule = Parameters<typeof composeStories>[0]

const modules = import.meta.glob<StoryModule>('../../src/components/*/*/*.stories.tsx', {
  eager: true,
})

export type Named = { readonly name: string; readonly Story: ComponentType }

export function allStories(): Named[] {
  return Object.entries(modules).flatMap(([path, module]) => {
    const component = path.split('/').at(-2) ?? path
    return Object.entries(composeStories(module)).map(([story, Story]) => ({
      name: `${component}/${story}`,
      Story: Story as ComponentType,
    }))
  })
}
