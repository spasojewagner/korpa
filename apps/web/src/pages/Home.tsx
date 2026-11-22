import { Link, createLazyRoute } from '@tanstack/react-router'
import { Suspense, lazy, useEffect, useRef, useState } from 'react'
import { Icon } from '../components'
import { homeCopy } from '../i18n/home'
import { useI18n } from '../i18n/I18nProvider'
import { formatDate, formatNumber } from '../lib/format'
import { usePageMeta } from '../lib/meta'
import { loadHome, useStatic, type HomeData } from './home-data'

/** The hero film; until the files exist the still image is shown. Paths are relative to /public. */
const HERO_VIDEO: { webm?: string; mp4?: string } = {}
const HERO_POSTER = '/media/hero-poster.webp'

function HeroMedia() {
  const { tr } = useI18n()
  const video = useRef<HTMLVideoElement>(null)
  const [playing, setPlaying] = useState(false)
  const hasVideo = Boolean(HERO_VIDEO.webm || HERO_VIDEO.mp4)
  useEffect(() => {
    if (!hasVideo || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
    video.current?.play().then(() => setPlaying(true)).catch(() => undefined)
  }, [hasVideo])
  const toggle = () => {
    const element = video.current
    if (!element) return
    if (element.paused) element.play().then(() => setPlaying(true)).catch(() => undefined)
    else { element.pause(); setPlaying(false) }
  }
  return (
    <div className="relative">
      <div aria-hidden="true" className="absolute -inset-3 -z-10 rotate-2 rounded-xl bg-sand sm:-inset-5" />
      <div className="overflow-hidden rounded-xl bg-paper-raised shadow-card">
        {hasVideo ? (
          <video ref={video} muted loop playsInline preload="metadata" poster={HERO_POSTER} aria-hidden="true"
            className="aspect-[5/6] w-full object-cover">
            {HERO_VIDEO.webm && <source src={HERO_VIDEO.webm} type="video/webm" />}
            {HERO_VIDEO.mp4 && <source src={HERO_VIDEO.mp4} type="video/mp4" />}
          </video>
        ) : (
          <img src={HERO_POSTER} alt="" width={480} height={577} fetchPriority="high"
            className="aspect-[5/6] w-full object-cover" />
        )}
        <div aria-hidden="true" className="kilim" />
      </div>
      <p className="absolute -bottom-5 left-4 max-w-[17rem] rounded-lg bg-white p-4 shadow-card sm:-left-8">
        <span className="flex items-center gap-2 text-sm font-semibold text-paprika">
          <Icon name="sparkles" className="size-4" />
          {tr(homeCopy.promptLabel)}
        </span>
        <span className="mt-1 block font-display text-lg text-ink">{tr(homeCopy.promptExample)}</span>
      </p>
      {hasVideo && (
        <button type="button" onClick={toggle} aria-pressed={!playing}
          className="absolute top-3 right-3 min-h-11 rounded-full bg-white/90 px-4 text-sm font-semibold text-ink hover:bg-white">
          {tr(playing ? homeCopy.pause : homeCopy.play)}
        </button>
      )}
    </div>
  )
}

function Hero({ data }: { data: HomeData | null }) {
  const { tr } = useI18n()
  const plural = new Intl.PluralRules('sr-Latn')
  const form = (n: number, forms: Record<string, string>) => tr(forms[plural.select(n)] ?? forms.other)
  const facts = data?.newest
    ? tr(homeCopy.facts)
      .replace('{products}', `${formatNumber(data.products)} ${form(data.products, homeCopy.productForms)}`)
      .replace('{retailers}', `${formatNumber(data.retailers)} ${form(data.retailers, homeCopy.chainForms)}`)
      .replace('{date}', formatDate(data.newest))
    : null
  return (
    <section aria-labelledby="hero-title" className="wrap grid items-center gap-14 pt-10 pb-16 lg:min-h-[calc(100svh-5.5rem)] lg:grid-cols-[1.05fr_1fr] lg:py-12">
      <div>
        <p className="enter inline-flex items-center gap-2 rounded-full bg-brand-subtle px-4 py-1.5 text-sm font-semibold text-brand">
          <span aria-hidden="true" className="size-2 rounded-full bg-brand" />
          {tr(homeCopy.eyebrow)}
        </p>
        <h1 id="hero-title" className="enter enter-2 mt-6 font-display text-[2.75rem] leading-[1.04] font-semibold sm:text-6xl lg:text-7xl">
          {tr(homeCopy.titleA)}
          <span className="block text-paprika">{tr(homeCopy.titleB)}</span>
        </h1>
        <p className="enter enter-3 mt-6 max-w-xl text-lg text-ink-soft sm:text-xl">{tr(homeCopy.lead)}</p>
        <div className="enter enter-3 mt-8 flex flex-col gap-3 sm:flex-row">
          <Link to="/korpa" hash="pomocnik" className="btn btn-primary">
            <Icon name="sparkles" className="size-5" />
            {tr(homeCopy.tryAi)}
          </Link>
          <a href="#pretraga" className="btn btn-secondary">
            <Icon name="search" className="size-5" />
            {tr(homeCopy.browse)}
          </a>
        </div>
        <p className="mt-6 min-h-6 text-sm text-ink-muted tabular-nums">{facts}</p>
      </div>
      <div className="enter enter-2 mx-auto w-full max-w-md lg:max-w-none">
        <HeroMedia />
      </div>
    </section>
  )
}

const HomeSections = lazy(() => import('./HomeSections'))

function Home() {
  usePageMeta()
  const data = useStatic(loadHome)
  return (
    <>
      <Hero data={data} />
      <Suspense fallback={null}>
        <HomeSections data={data} />
      </Suspense>
    </>
  )
}

export const Route = createLazyRoute('/')({ component: Home })
