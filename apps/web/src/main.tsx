import React from 'react'
import ReactDOM from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createRootRoute, createRoute, createRouter, RouterProvider } from '@tanstack/react-router'
import { App } from './App'
import { I18nProvider } from './i18n/I18nProvider'
import './styles.css'

const rootRoute = createRootRoute()
const home = createRoute({ getParentRoute: () => rootRoute, path: '/', component: App })
const router = createRouter({ routeTree: rootRoute.addChildren([home]) })
declare module '@tanstack/react-router' { interface Register { router: typeof router } }
const client = new QueryClient()
ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode><QueryClientProvider client={client}>
    <I18nProvider><RouterProvider router={router} /></I18nProvider>
  </QueryClientProvider></React.StrictMode>,
)
