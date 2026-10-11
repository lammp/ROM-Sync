/**
 * Each unit test starts clean: what one test rendered is unmounted after it,
 * the spies a story's args carry forget the calls they saw, and the one
 * application store goes back to how the page found it.
 */
import { cleanup, configure } from '@testing-library/react'
import { clearAllMocks } from 'storybook/test'
import { afterEach } from 'vitest'
import { resetAppStore } from '../../src/store/store'

// A test that reads the fake engine waits for it; a busy machine running the
// gate's shuffled passes can need more than the default second.
configure({ asyncUtilTimeout: 5000 })

afterEach(() => {
  cleanup()
  clearAllMocks()
  resetAppStore()
})
