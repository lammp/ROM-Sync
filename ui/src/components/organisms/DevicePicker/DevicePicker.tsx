import { Lamp } from '../../atoms/Lamp/Lamp'
import { Select } from '../../atoms/Select/Select'

export type DeviceOption = { readonly id: string; readonly name: string; readonly online: boolean }

export type DevicePickerProps = {
  readonly devices: readonly DeviceOption[]
  readonly value: string | null
  readonly onChange: (id: string | null) => void
}

/** The device the library is curated for, or none, with its connection lamp. */
export function DevicePicker({ devices, value, onChange }: DevicePickerProps) {
  const chosen = devices.find((d) => d.id === value)
  return (
    <>
      {chosen && (
        <Lamp
          state={chosen.online ? 'on' : 'off'}
          label={chosen.online ? `${chosen.name} is connected` : `${chosen.name} is not connected`}
        />
      )}
      <Select
        label="Device"
        value={value ?? ''}
        onChange={(v) => onChange(v || null)}
        options={[
          { value: '', label: 'No device' },
          ...devices.map((d) => ({
            value: d.id,
            label: `${d.name}${d.online ? '' : ' (offline)'}`,
          })),
        ]}
      />
    </>
  )
}
