import React from 'react'
import { Routes, Route, Link, useLocation, Navigate } from 'react-router-dom'
import { 
  LayoutDashboard, 
  Monitor, 
  Shield, 
  Usb, 
  Globe, 
  FileSearch,
  Settings as SettingsIcon,
  Bell,
  Calendar,
  Book,
  LogOut,
  User
} from 'lucide-react'

import { AuthProvider, useAuth } from './context/AuthContext'

import Dashboard from './pages/Dashboard'
import Endpoints from './pages/Endpoints'
import Events from './pages/Events'
import USBControl from './pages/USBControl'
import NetworkControl from './pages/NetworkControl'
import Policies from './pages/Policies'
import Login from './pages/Login'
import AccessDenied from './pages/AccessDenied'
import Schedules from './pages/Schedules'
import Settings from './pages/Settings'
import Setup from './pages/Setup'

const navigation = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard },
  { name: 'Endpoints', href: '/endpoints', icon: Monitor },
  { name: 'Events', href: '/events', icon: Bell },
  { name: 'Schedules', href: '/schedules', icon: Calendar },
  { name: 'USB Control', href: '/usb', icon: Usb },
  { name: 'Network', href: '/network', icon: Globe },
  { name: 'Policies', href: '/policies', icon: Shield },
  { name: 'Setup Guide', href: '/setup', icon: Book },
  { name: 'Settings', href: '/settings', icon: SettingsIcon },
]

function Sidebar() {
  const location = useLocation()
  const { user, logout } = useAuth()
  
  return (
    <div className="flex flex-col w-64 bg-zinc-950 border-r border-zinc-800 min-h-screen transition-all duration-300">
      <div className="flex items-center h-16 px-6 bg-zinc-950/50 backdrop-blur-xl border-b border-zinc-800">
        <div className="relative">
          <Shield className="w-8 h-8 text-blue-500 relative z-10" />
          <div className="absolute inset-0 bg-blue-500/20 blur-lg rounded-full" />
        </div>
        <span className="ml-3 text-lg font-bold text-white tracking-wide">EndpointSec</span>
      </div>
      
      <nav className="flex-1 px-3 py-6 space-y-1 overflow-y-auto">
        {navigation.map((item) => {
          const isActive = location.pathname === item.href
          return (
            <Link
              key={item.name}
              to={item.href}
              className={`
                group flex items-center px-3 py-2.5 text-sm font-medium rounded-lg transition-all duration-200
                ${isActive 
                  ? 'bg-blue-500/10 text-blue-400 shadow-[0_0_20px_rgba(59,130,246,0.1)] border border-blue-500/20' 
                  : 'text-zinc-400 hover:bg-zinc-900 hover:text-zinc-100 hover:translate-x-1'
                }
              `}
            >
              <item.icon className={`w-5 h-5 mr-3 transition-colors ${isActive ? 'text-blue-400' : 'text-zinc-500 group-hover:text-zinc-300'}`} />
              {item.name}
              {isActive && (
                <div className="ml-auto w-1.5 h-1.5 rounded-full bg-blue-400 shadow-[0_0_8px_rgba(96,165,250,0.8)]" />
              )}
            </Link>
          )
        })}
      </nav>
      
      <div className="p-4 border-t border-zinc-800 bg-zinc-900/30">
        {user && (
          <div className="mb-4 flex items-center p-2 rounded-lg bg-zinc-900/50 border border-zinc-800/50">
            <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-blue-600 to-blue-400 flex items-center justify-center text-white shadow-lg">
              <User className="w-4 h-4" />
            </div>
            <div className="ml-3 overflow-hidden">
              <p className="text-sm font-medium text-zinc-200 truncate">{user.username}</p>
              <p className="text-xs text-blue-400 uppercase tracking-wider font-semibold">{user.role}</p>
            </div>
          </div>
        )}
        <button
          onClick={logout}
          className="flex items-center justify-center w-full px-4 py-2 text-sm font-medium text-zinc-400 hover:text-red-400 hover:bg-red-500/10 hover:border-red-500/20 border border-transparent rounded-lg transition-all duration-200"
        >
          <LogOut className="w-4 h-4 mr-2" />
          Sign Out
        </button>
        <div className="mt-4 text-center">
          <p className="text-[10px] text-zinc-600 uppercase tracking-widest">System v1.0</p>
        </div>
      </div>
    </div>
  )
}

function ProtectedRoute({ children }) {
  const { isAuthenticated, loading, setupRequired } = useAuth()
  
  if (loading) {
    return (
      <div className="min-h-screen bg-zinc-950 flex items-center justify-center">
        <div className="relative">
          <div className="w-16 h-16 border-4 border-blue-500/30 border-t-blue-500 rounded-full animate-spin"></div>
          <div className="absolute inset-0 flex items-center justify-center">
            <Shield className="w-6 h-6 text-blue-500 animate-pulse" />
          </div>
        </div>
      </div>
    )
  }
  
  if (setupRequired) {
    return <Navigate to="/login" replace />
  }
  
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }
  
  return children
}

function AppLayout() {
  return (
    <div className="flex min-h-screen bg-black text-slate-400 selection:bg-blue-500/30">
      <Sidebar />
      <main className="flex-1 overflow-auto bg-gradient-to-br from-zinc-950 via-zinc-900 to-zinc-950">
        <div className="min-h-full p-8">
          <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/endpoints" element={<Endpoints />} />
          <Route path="/events" element={<Events />} />
          <Route path="/schedules" element={<Schedules />} />
          <Route path="/usb" element={<USBControl />} />
          <Route path="/network" element={<NetworkControl />} />
          <Route path="/policies" element={<Policies />} />
          <Route path="/setup" element={<Setup />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
        </div>
      </main>
    </div>
  )
}

function AppRoutes() {
  const { isAuthenticated, loading } = useAuth()
  
  const isDashboardHost = [
    'localhost', 
    '127.0.0.1', 
    '0.0.0.0'
  ].includes(window.location.hostname)

  if (loading) {
    return (
      <div className="min-h-screen bg-zinc-950 flex items-center justify-center">
        <div className="relative">
          <div className="w-16 h-16 border-4 border-blue-500/30 border-t-blue-500 rounded-full animate-spin"></div>
        </div>
      </div>
    )
  }

  if (!isDashboardHost) {
    return <AccessDenied />
  }
  
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/blocked" element={<AccessDenied />} />
      <Route path="/*" element={
        <ProtectedRoute>
          <AppLayout />
        </ProtectedRoute>
      } />
    </Routes>
  )
}

function App() {
  return (
    <AuthProvider>
      <AppRoutes />
    </AuthProvider>
  )
}

export default App
