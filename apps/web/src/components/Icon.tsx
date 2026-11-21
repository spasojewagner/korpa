const paths = {
  check: 'M5 12.5l4.5 4.5L19 7.5',
  tag: 'M3 12V4h8l9 9-8 8-9-9z M7.5 7.5h.01',
  up: 'M12 19V5 M6 11l6-6 6 6',
  down: 'M12 5v14 M6 13l6 6 6-6',
  alert: 'M12 3l10 18H2L12 3z M12 10v4 M12 17.5v.01',
  minus: 'M5 12h14',
  plus: 'M12 5v14 M5 12h14',
} as const

export type IconName = keyof typeof paths

/** Decorative icon: meaning is always carried by adjacent text. */
export function Icon({ name, className = 'size-4 shrink-0' }: { name: IconName; className?: string }) {
  return (
    <svg aria-hidden="true" focusable="false" viewBox="0 0 24 24" fill="none" stroke="currentColor"
      strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" className={className}>
      <path d={paths[name]} />
    </svg>
  )
}
