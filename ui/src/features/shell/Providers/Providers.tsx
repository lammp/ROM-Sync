'use client'

import type { ReactNode } from 'react'
import { EngineProvider, type Engine } from '../../../queries/engine/engine'

/** The engine connection every feature below reads through; one per page load. */
export function Providers({ engine, children }: { engine?: Engine; children: ReactNode }) {
  return <EngineProvider engine={engine}>{children}</EngineProvider>
}
