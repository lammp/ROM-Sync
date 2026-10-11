import type { Preview } from '@storybook/nextjs-vite'
import '../src/design/tokens/tokens.css'
import '../src/design/base/base.css'

const preview: Preview = {
  parameters: {
    // An accessibility violation fails the story's test, not just the panel.
    a11y: { test: 'error' },
  },
}

export default preview
