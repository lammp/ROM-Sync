import styles from './CoverImage.module.css'

export type CoverSize = 'tile' | 'big' | 'row'

export type CoverImageProps = {
  readonly src: string
  /** The game's title; a cover is never decorative. */
  readonly alt: string
  readonly size?: CoverSize
}

/** A game's cover art, loaded only when near the screen and decoded off the main thread. */
export function CoverImage({ src, alt, size = 'tile' }: CoverImageProps) {
  return (
    // The export is static: there is no image optimiser to hand a cover to.
    // eslint-disable-next-line @next/next/no-img-element
    <img src={src} alt={alt} loading="lazy" decoding="async" className={styles[size]} />
  )
}
