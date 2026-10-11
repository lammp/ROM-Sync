/**
 * Each unit test starts clean: what one test rendered is unmounted after it,
 * and the spies a story's args carry forget the calls they saw.
 */
import { cleanup } from '@testing-library/react'
import { clearAllMocks } from 'storybook/test'
import { afterEach } from 'vitest'

afterEach(() => {
  cleanup()
  clearAllMocks()
})
