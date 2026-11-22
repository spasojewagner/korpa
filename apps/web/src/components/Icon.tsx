const paths = {
  check: 'M5 12.5l4.5 4.5L19 7.5',
  tag: 'M3 12V4h8l9 9-8 8-9-9z M7.5 7.5h.01',
  up: 'M12 19V5 M6 11l6-6 6 6',
  down: 'M12 5v14 M6 13l6 6 6-6',
  alert: 'M12 3l10 18H2L12 3z M12 10v4 M12 17.5v.01',
  minus: 'M5 12h14',
  plus: 'M12 5v14 M5 12h14',
  // From Lucide (ISC), each subpath made absolute: shopping-basket, search, arrow-right, sparkles, chart-line, shield-check, code-xml.
  basket: 'M15 11l-1 9 M19 11l-4-7 M2 11h20 M3.5 11l1.6 7.4a2 2 0 0 0 2 1.6h9.8a2 2 0 0 0 2-1.6l1.7-7.4 M4.5 15.5h15 M5 11l4-7 M9 11l1 9',
  search: 'M21 21l-4.34-4.34 M3 11a8 8 0 1 0 16 0a8 8 0 1 0-16 0',
  arrowRight: 'M5 12h14 M12 5l7 7-7 7',
  sparkles: 'M11.017 2.814a1 1 0 0 1 1.966 0l1.051 5.558a2 2 0 0 0 1.594 1.594l5.558 1.051a1 1 0 0 1 0 1.966l-5.558 1.051a2 2 0 0 0-1.594 1.594l-1.051 5.558a1 1 0 0 1-1.966 0l-1.051-5.558a2 2 0 0 0-1.594-1.594l-5.558-1.051a1 1 0 0 1 0-1.966l5.558-1.051a2 2 0 0 0 1.594-1.594z M20 2v4 M22 4h-4 M2 20a2 2 0 1 0 4 0a2 2 0 1 0-4 0',
  chart: 'M3 3v16a2 2 0 0 0 2 2h16 M19 9l-5 5-4-4-3 3',
  shield: 'M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z M9 12l2 2 4-4',
  code: 'M18 16l4-4-4-4 M6 8l-4 4 4 4 M14.5 4l-5 16',
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
