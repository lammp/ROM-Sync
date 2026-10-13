import { TILE_MAX, TILE_MIN } from '../../../design/tokens/tokens'
import { Range } from '../../atoms/Range/Range'

/** The tile slider, over version 1's range. */
export function TileSizeControl({
  value,
  onChange,
}: {
  value: number
  onChange: (px: number) => void
}) {
  return (
    <Range
      label="Tiles"
      min={TILE_MIN}
      max={TILE_MAX}
      value={value}
      onChange={onChange}
      valueText={`${value} pixels wide`}
    />
  )
}
