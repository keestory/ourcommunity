import React from 'react'
import ReactDOM from 'react-dom/client'
import { createBrowserRouter, Link, RouterProvider } from 'react-router-dom'
import '@fontsource-variable/noto-sans-kr'
import '@fontsource-variable/outfit'
import './tokens.css'
import './styles.css'
import { SessionProvider } from './lib/session'
import { BrowserDemoTools } from './components/BrowserDemoTools'
import { ToastProvider } from './components/ui'
import { GroupIndex, Layout, Protected } from './components/Layout'
import { Auth } from './pages/Auth'
import { Space } from './pages/Space'
import { Chat } from './pages/Chat'
import { CreateEvent, EventDetail, Events } from './pages/Events'
import { Memories } from './pages/Memories'
import { Settings } from './pages/Settings'
import { Invite, Notifications, PublicSpace } from './pages/Other'
function NotFound() { return <main className="narrow-page"><h1>이 페이지를 찾을 수 없어요.</h1><Link className="button secondary" to="/">내 공간으로</Link></main> }
const router = createBrowserRouter([
  { path: '/auth', element: <Auth/> }, { path: '/invite/:token', element: <Invite/> }, { path: '/public/groups/:groupId', element: <PublicSpace/> },
  { element: <Protected/>, children: [ { path: '/', element: <GroupIndex/> }, { path: '/groups/:groupId', element: <Layout/>, children: [ { path: 'space', element: <Space/> }, { path: 'chat', element: <Chat/> }, { path: 'events', element: <Events/> }, { path: 'events/new', element: <CreateEvent/> }, { path: 'events/:eventId', element: <EventDetail/> }, { path: 'memories', element: <Memories/> }, { path: 'settings', element: <Settings/> }, { path: 'notifications', element: <Notifications/> } ] } ] }, { path: '*', element: <NotFound/> }
])
ReactDOM.createRoot(document.getElementById('root')!).render(<React.StrictMode><SessionProvider><ToastProvider><BrowserDemoTools/><RouterProvider router={router}/></ToastProvider></SessionProvider></React.StrictMode>)
