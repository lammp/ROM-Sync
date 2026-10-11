/**
 * Each unit test starts clean: what one test rendered is unmounted after it,
 * the spies a story's args carry forget the calls they saw, and the one
 * application store goes back to how the page found it.
 */
import { cleanup } from '@testing-library/react'
import { clearAllMocks } from 'storybook/test'
import { afterEach } from 'vitest'
import { resetAppStore } from '../../src/store/store'

afterEach(() => {
  cleanup()
  clearAllMocks()
  resetAppStore()
})
