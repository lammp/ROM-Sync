import type { Preview } from '@storybook/nextjs-vite'
import { configure } from 'storybook/test'
import '../src/design/tokens/tokens.css'
import '../src/design/base/base.css'

// Stories that read the fake engine wait for it; under a full, shuffled run in
// one browser a second is not always enough, so every wait allows five.
configure({ asyncUtilTimeout: 5000 })

const preview: Preview = {
  parameters: {
    // An accessibility violation fails the story's test, not just the panel.
    a11y: { test: 'error' },
  },
}

export default preview
