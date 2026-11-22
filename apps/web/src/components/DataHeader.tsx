import { Link } from '@tanstack/react-router'
import { Logo } from '../Layout'
import { usePageI18n } from '../i18n/usePageI18n'
import { ScriptToggle } from './Controls'
import { Icon } from './Icon'
const activeNav = { 'aria-current': 'page' as const, className: 'is-active' }
export default function DataHeader() {
  const { t } = usePageI18n()
  const tab = 'data-tab inline-flex min-h-11 items-center border-b-3 border-transparent px-1 text-paper/90 hover:text-paper'
  return (
    <header className="bg-brand-deep text-paper">
      <div className="wrap flex flex-wrap items-center justify-between gap-4 pt-4">
        <div className="flex items-center gap-3">
          <Logo tone="dark" />
          <span aria-hidden="true" className="text-sand">/</span>
          <span className="font-display text-xl text-sand">{t('navData')}</span>
        </div>
        <div className="flex items-center gap-3">
          <Link to="/" className="inline-flex min-h-11 items-center gap-2 rounded-full px-3 font-semibold text-paper hover:bg-brand">
            <Icon name="basket" className="size-5" />
            {t('dataBack')}
          </Link>
          <ScriptToggle tone="dark" />
        </div>
      </div>
      <nav aria-label={t('dataNavLabel')} className="wrap mt-2">
        <ul className="flex flex-wrap gap-x-6">
          <li><Link to="/podaci" className={tab} activeOptions={{ exact: true }} activeProps={activeNav}>{t('dataOverview')}</Link></li>
          <li><Link to="/podaci/indeks" className={tab} activeProps={activeNav}>{t('dataIndex')}</Link></li>
          <li><Link to="/podaci/kvalitet" className={tab} activeProps={activeNav}>{t('dataQuality')}</Link></li>
          <li><Link to="/podaci/api" className={tab} activeProps={activeNav}>{t('dataApi')}</Link></li>
        </ul>
      </nav>
      <div aria-hidden="true" className="kilim" />
    </header>
  )
}

