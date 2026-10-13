'use client'

import { useSearchParams } from 'next/navigation'
import { DeviceView } from '../DeviceView/DeviceView'
import { DevicesView } from '../DevicesView/DevicesView'

/**
 * `/devices` and `/devices?id=` (D20): a static export cannot have a page per
 * device, so the device is a search parameter and this chooses the view.
 */
export function DevicesPage() {
  const id = useSearchParams().get('id')
  return id ? <DeviceView key={id} id={id} /> : <DevicesView />
}
