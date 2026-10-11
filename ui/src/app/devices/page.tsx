import { Suspense } from 'react'
import { DevicesPage } from '../../features/devices/DevicesPage/DevicesPage'

export default function Devices() {
  // Reading the search parameter needs a boundary in a static export.
  return (
    <Suspense>
      <DevicesPage />
    </Suspense>
  )
}
