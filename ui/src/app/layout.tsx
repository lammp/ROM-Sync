import type { Metadata } from 'next'
import type { ReactNode } from 'react'
import '../design/tokens/tokens.css'
import '../design/base/base.css'
import { AppShell } from '../components/templates/AppShell/AppShell'
import { HeaderBar } from '../features/shell/HeaderBar/HeaderBar'
import { NoticeWatcher } from '../features/shell/NoticeWatcher/NoticeWatcher'
import { Providers } from '../features/shell/Providers/Providers'
import { SyncWatcher } from '../features/shell/SyncWatcher/SyncWatcher'
import { Toasts } from '../features/shell/Toasts/Toasts'

export const metadata: Metadata = {
  title: 'ROM-Sync',
  description: 'Curate a game library onto a handheld.',
}

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Providers>
          <SyncWatcher />
          <NoticeWatcher />
          <AppShell header={<HeaderBar />} toasts={<Toasts />}>
            {children}
          </AppShell>
        </Providers>
      </body>
    </html>
  )
}
