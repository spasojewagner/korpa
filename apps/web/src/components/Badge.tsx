import type { ReactNode } from 'react'
import { useI18n } from '../i18n/I18nProvider'
import type { CopyKey } from '../i18n/sr-Latn'
import { Icon, type IconName } from './Icon'

export type BadgeVariant = 'cheapest' | 'discount' | 'partial' | 'increase' | 'decrease'

const variants: Record<BadgeVariant, { className: string; icon: IconName; label: CopyKey }> = {
  cheapest: { className: 'bg-brand-subtle text-brand', icon: 'check', label: 'badgeCheapest' },
  discount: { className: 'bg-discount-subtle text-discount', icon: 'tag', label: 'badgeDiscount' },
  partial: { className: 'bg-warn-subtle text-warn', icon: 'alert', label: 'basketPartial' },
  increase: { className: 'bg-danger-subtle text-danger', icon: 'up', label: 'badgeIncrease' },
  decrease: { className: 'bg-brand-subtle text-brand', icon: 'down', label: 'badgeDecrease' },
}

/** Status label: icon + text, never color alone. */
export function Badge({ variant, children }: { variant: BadgeVariant; children?: ReactNode }) {
  const { t } = useI18n()
  const { className, icon, label } = variants[variant]
  return (
    <span className={`inline-flex items-center gap-1 rounded-sm px-2 py-0.5 text-sm font-semibold ${className}`}>
      <Icon name={icon} />
      {children ?? t(label)}
    </span>
  )
}
