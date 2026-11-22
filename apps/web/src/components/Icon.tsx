export type IconName = 'check' | 'tag' | 'up' | 'down' | 'alert' | 'minus' | 'plus' | 'basket' | 'search' | 'arrowRight' | 'sparkles' | 'chart' | 'shield' | 'code'

/** Decorative icon: meaning is always carried by adjacent text. */
export function Icon({ name, className = 'size-4 shrink-0' }: { name: IconName; className?: string }) {
  return (
    <svg aria-hidden="true" focusable="false" viewBox="0 0 24 24" fill="none" stroke="currentColor"
      strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" className={className}>
      <use href={`/icons.svg#${name}`} />
    </svg>
  )
}
