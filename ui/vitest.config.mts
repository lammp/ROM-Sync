import { existsSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { storybookTest } from '@storybook/addon-vitest/vitest-plugin'
import react from '@vitejs/plugin-react'
import { playwright } from '@vitest/browser-playwright'
import { defineConfig } from 'vitest/config'

const UI = dirname(fileURLToPath(import.meta.url))

// A preinstalled Chromium, where the machine has one, is used as it is; elsewhere
// Playwright's own download is.
const CHROMIUM = process.env.ROMSYNC_CHROMIUM ?? '/opt/pw-browsers/chromium'
const launchOptions = existsSync(CHROMIUM) ? { executablePath: CHROMIUM } : {}

export default defineConfig({
  plugins: [react()],
  resolve: { tsconfigPaths: true },
  test: {
    projects: [
      {
        extends: true,
        test: {
          name: 'unit',
          environment: 'jsdom',
          include: ['src/**/*.test.{ts,tsx}', 'parity/**/*.test.ts', 'structure/**/*.test.ts'],
        },
      },
      {
        extends: true,
        plugins: [storybookTest({ configDir: join(UI, '.storybook') })],
        test: {
          name: 'storybook',
          browser: {
            enabled: true,
            headless: true,
            provider: playwright({ launchOptions }),
            instances: [{ browser: 'chromium' }],
          },
        },
      },
    ],
  },
})
