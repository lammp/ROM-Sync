import type { Preview } from '@storybook/nextjs-vite'

const preview: Preview = {
  parameters: {
    // An accessibility violation fails the story's test, not just the panel.
    a11y: { test: 'error' },
  },
}

export default preview
