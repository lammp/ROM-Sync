import type { Metadata } from 'next'
import type { ReactNode } from 'react'
import '../design/tokens/tokens.css'
import '../design/base/base.css'

export const metadata: Metadata = {
  title: 'ROM-Sync',
  description: 'Curate a game library onto a handheld.',
}

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}
