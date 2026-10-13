import { existsSync } from 'node:fs'
import { defineConfig, devices } from '@playwright/test'

const PORT = 4310
const CHROMIUM = process.env.ROMSYNC_CHROMIUM ?? '/opt/pw-browsers/chromium'

// The assembled application, as the user meets it: the static export served by
// manifest lookup, with the engine faked over HTTP (REBUILD-UI section 14.4).
export default defineConfig({
  testDir: 'e2e',
  testMatch: '**/*.spec.ts',
  fullyParallel: false,
  workers: 1,
  reporter: 'list',
  use: {
    baseURL: `http://127.0.0.1:${PORT}`,
    ...devices['Desktop Chrome'],
    launchOptions: existsSync(CHROMIUM) ? { executablePath: CHROMIUM } : {},
  },
  webServer: {
    command: `npm run bundle && node --experimental-strip-types --disable-warning=ExperimentalWarning e2e/serve.ts ${PORT}`,
    url: `http://127.0.0.1:${PORT}/`,
    reuseExistingServer: false,
    timeout: 240_000,
  },
})
