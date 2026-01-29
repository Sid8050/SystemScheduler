import React from 'react'
import { useQuery } from '@tanstack/react-query'
import { 
  Monitor, 
  AlertTriangle, 
  HardDrive, 
  Shield,
  Activity,
  Terminal,
  ArrowRight,
  CheckCircle2,
  XCircle,
  AlertOctagon
} from 'lucide-react'
import { api } from '../api/client'

function StatCard({ title, value, subtitle, icon: Icon, color = 'blue', trend }) {
  const themes = {
    blue: {
      bg: 'bg-blue-500/10',
      border: 'border-blue-500/20',
      text: 'text-blue-400',
      iconBg: 'bg-blue-500/20', 
      glow: 'shadow-[0_0_20px_rgba(59,130,246,0.1)]',
      gradient: 'from-blue-500/10 to-transparent'
    },
    green: {
      bg: 'bg-emerald-500/10',
      border: 'border-emerald-500/20',
      text: 'text-emerald-400',
      iconBg: 'bg-emerald-500/20',
      glow: 'shadow-[0_0_20px_rgba(16,185,129,0.1)]',
      gradient: 'from-emerald-500/10 to-transparent'
    },
    yellow: {
      bg: 'bg-amber-500/10',
      border: 'border-amber-500/20',
      text: 'text-amber-400',
      iconBg: 'bg-amber-500/20',
      glow: 'shadow-[0_0_20px_rgba(245,158,11,0.1)]',
      gradient: 'from-amber-500/10 to-transparent'
    },
    red: {
      bg: 'bg-red-500/10',
      border: 'border-red-500/20',
      text: 'text-red-400',
      iconBg: 'bg-red-500/20',
      glow: 'shadow-[0_0_20px_rgba(239,68,68,0.1)]',
      gradient: 'from-red-500/10 to-transparent'
    },
    purple: {
      bg: 'bg-violet-500/10',
      border: 'border-violet-500/20',
      text: 'text-violet-400',
      iconBg: 'bg-violet-500/20',
      glow: 'shadow-[0_0_20px_rgba(139,92,246,0.1)]',
      gradient: 'from-violet-500/10 to-transparent'
    },
  }
  
  const theme = themes[color] || themes.blue
  
  return (
    <div className={`relative overflow-hidden rounded-xl border ${theme.border} bg-zinc-900/50 backdrop-blur-sm p-6 transition-all duration-300 hover:bg-zinc-900/80 hover:border-opacity-50 group`}>
      <div className={`absolute inset-0 bg-gradient-to-br ${theme.gradient} opacity-0 group-hover:opacity-100 transition-opacity duration-500`} />
      
      <div className="relative flex justify-between items-start">
        <div>
          <p className="text-sm font-medium text-zinc-500 tracking-wide uppercase">{title}</p>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-3xl font-bold text-white tracking-tight">{value}</span>
          </div>
          {subtitle && (
            <p className="mt-2 text-sm text-zinc-400 font-medium flex items-center">
              {subtitle}
            </p>
          )}
        </div>
        <div className={`rounded-lg p-3 ${theme.iconBg} ${theme.text} ${theme.glow}`}>
          <Icon className="w-6 h-6" />
        </div>
      </div>
    </div>
  )
}

function formatBytes(bytes) {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

function Dashboard() {
  const { data: stats, isLoading } = useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: () => api.getDashboardStats().then(r => r.data),
    refetchInterval: 30000,
  })
  
  const { data: eventStats } = useQuery({
    queryKey: ['event-stats'],
    queryFn: () => api.getEventStats(24).then(r => r.data),
    refetchInterval: 30000,
  })

  // New query for live feed
  const { data: recentEvents } = useQuery({
    queryKey: ['recent-events'],
    queryFn: () => api.getEvents({ limit: 5 }).then(r => r.data),
    refetchInterval: 10000,
  })
  
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="relative">
          <div className="w-12 h-12 border-4 border-blue-500/30 border-t-blue-500 rounded-full animate-spin"></div>
        </div>
      </div>
    )
  }
  
  return (
    <div className="space-y-8 animate-fade-in">
      {/* Header */}
      <div className="flex justify-between items-end border-b border-zinc-800 pb-6">
        <div>
          <h1 className="text-3xl font-bold text-white tracking-tight">Command Center</h1>
          <p className="text-zinc-500 mt-2 font-medium flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            System Operational • Monitoring Active
          </p>
        </div>
        <div className="text-right hidden sm:block">
          <p className="text-sm text-zinc-500 font-mono">{new Date().toLocaleDateString()}</p>
          <p className="text-xl text-zinc-300 font-mono font-bold">{new Date().toLocaleTimeString()}</p>
        </div>
      </div>
      
      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          title="Total Endpoints"
          value={stats?.endpoints?.total || 0}
          subtitle={`${stats?.endpoints?.online || 0} online`}
          icon={Monitor}
          color="blue"
        />
        <StatCard
          title="Critical Threats"
          value={stats?.events_24h?.critical || 0}
          subtitle="Last 24 Hours"
          icon={AlertOctagon}
          color={stats?.events_24h?.critical > 0 ? 'red' : 'green'}
        />
        <StatCard
          title="Data Protected"
          value={formatBytes(stats?.backup?.total_size_bytes || 0)}
          subtitle={`${(stats?.backup?.total_files || 0).toLocaleString()} files`}
          icon={HardDrive}
          color="purple"
        />
        <StatCard
          title="System Status"
          value="Secure"
          subtitle="All systems nominal"
          icon={Shield}
          color="green"
        />
      </div>
      
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Events by Severity */}
        <div className="lg:col-span-2 bg-zinc-900/50 backdrop-blur-sm rounded-xl border border-zinc-800 p-6">
          <h2 className="text-lg font-semibold text-white mb-6 flex items-center gap-2">
            <Activity className="w-5 h-5 text-blue-400" />
            Threat Analysis (24h)
          </h2>
          
          <div className="space-y-6">
            {['critical', 'error', 'warning', 'info'].map((severity) => {
              const count = eventStats?.by_severity?.[severity] || 0
              const total = eventStats?.total_events || 1
              const percentage = Math.round((count / total) * 100) || 0
              
              const config = {
                critical: { color: 'bg-red-500', shadow: 'shadow-[0_0_10px_rgba(239,68,68,0.5)]', label: 'text-red-400' },
                error: { color: 'bg-orange-500', shadow: 'shadow-[0_0_10px_rgba(249,115,22,0.5)]', label: 'text-orange-400' },
                warning: { color: 'bg-amber-500', shadow: 'shadow-[0_0_10px_rgba(245,158,11,0.5)]', label: 'text-amber-400' },
                info: { color: 'bg-blue-500', shadow: 'shadow-[0_0_10px_rgba(59,130,246,0.5)]', label: 'text-blue-400' },
              }[severity]
              
              return (
                <div key={severity} className="group">
                  <div className="flex justify-between text-sm mb-2">
                    <span className={`font-semibold capitalize tracking-wide ${config.label}`}>{severity}</span>
                    <span className="text-zinc-400 font-mono">{count} <span className="text-zinc-600">/ {percentage}%</span></span>
                  </div>
                  <div className="w-full bg-zinc-800/50 rounded-full h-2 overflow-hidden">
                    <div
                      className={`${config.color} h-2 rounded-full transition-all duration-1000 ${config.shadow}`}
                      style={{ width: `${Math.max(percentage, count > 0 ? 5 : 0)}%` }}
                    />
                  </div>
                </div>
              )
            })}
          </div>
        </div>

        {/* Live Feed */}
        <div className="bg-zinc-900/50 backdrop-blur-sm rounded-xl border border-zinc-800 p-6 flex flex-col">
          <h2 className="text-lg font-semibold text-white mb-6 flex items-center gap-2">
            <Terminal className="w-5 h-5 text-emerald-400" />
            Live Feed
          </h2>
          
          <div className="flex-1 space-y-4 overflow-y-auto max-h-[300px] pr-2 custom-scrollbar">
            {recentEvents?.items?.length > 0 ? (
              recentEvents.items.map((event, i) => (
                <div key={event.id || i} className="flex gap-3 items-start p-3 rounded-lg bg-zinc-900/80 border border-zinc-800/50 hover:border-zinc-700 transition-colors">
                  <div className={`mt-1 w-2 h-2 rounded-full shrink-0 ${
                    event.severity === 'critical' ? 'bg-red-500 animate-pulse' :
                    event.severity === 'warning' ? 'bg-amber-500' :
                    'bg-blue-500'
                  }`} />
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-zinc-200 truncate">{event.type}</p>
                    <p className="text-xs text-zinc-500 truncate mt-0.5">{event.description || 'System event detected'}</p>
                    <p className="text-[10px] text-zinc-600 font-mono mt-2">{new Date(event.created_at).toLocaleTimeString()}</p>
                  </div>
                </div>
              ))
            ) : (
               <div className="text-center py-10">
                 <div className="w-12 h-12 bg-zinc-800 rounded-full flex items-center justify-center mx-auto mb-3">
                   <Activity className="w-6 h-6 text-zinc-600" />
                 </div>
                 <p className="text-zinc-500 text-sm">No recent activity</p>
               </div>
            )}
          </div>
          
          <div className="mt-4 pt-4 border-t border-zinc-800">
             <button className="w-full py-2 text-xs font-medium text-zinc-400 hover:text-white hover:bg-zinc-800 rounded transition-colors flex items-center justify-center gap-2">
               View Full Log <ArrowRight className="w-3 h-3" />
             </button>
          </div>
        </div>
      </div>
      
      {/* Quick Actions & Top Types */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-zinc-900/50 backdrop-blur-sm rounded-xl border border-zinc-800 p-6">
          <h2 className="text-lg font-semibold text-white mb-4">Quick Actions</h2>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <button className="flex flex-col items-center justify-center p-4 bg-zinc-900 border border-zinc-800 hover:border-blue-500/50 hover:bg-blue-500/5 text-zinc-400 hover:text-blue-400 rounded-xl transition-all duration-300 group">
              <Monitor className="w-6 h-6 mb-2 group-hover:scale-110 transition-transform" />
              <span className="text-sm font-medium">Endpoints</span>
            </button>
            <button className="flex flex-col items-center justify-center p-4 bg-zinc-900 border border-zinc-800 hover:border-red-500/50 hover:bg-red-500/5 text-zinc-400 hover:text-red-400 rounded-xl transition-all duration-300 group">
              <AlertTriangle className="w-6 h-6 mb-2 group-hover:scale-110 transition-transform" />
              <span className="text-sm font-medium">Threats</span>
            </button>
            <button className="flex flex-col items-center justify-center p-4 bg-zinc-900 border border-zinc-800 hover:border-violet-500/50 hover:bg-violet-500/5 text-zinc-400 hover:text-violet-400 rounded-xl transition-all duration-300 group">
              <Shield className="w-6 h-6 mb-2 group-hover:scale-110 transition-transform" />
              <span className="text-sm font-medium">Policies</span>
            </button>
          </div>
        </div>
        
         <div className="bg-zinc-900/50 backdrop-blur-sm rounded-xl border border-zinc-800 p-6">
          <h2 className="text-lg font-semibold text-white mb-4">Top Event Types (24h)</h2>
          <div className="space-y-3">
            {Object.entries(eventStats?.by_type || {}).slice(0, 5).map(([type, count]) => (
              <div key={type} className="flex items-center justify-between p-3 rounded-lg bg-zinc-900/50 border border-zinc-800/50">
                <span className="text-sm font-medium text-zinc-300">{type}</span>
                <span className="px-2 py-1 rounded-md bg-zinc-800 text-xs font-mono text-zinc-100 border border-zinc-700">{count}</span>
              </div>
            ))}
            {Object.keys(eventStats?.by_type || {}).length === 0 && (
               <p className="text-zinc-500 text-sm py-4 text-center italic">No events recorded in the monitoring window</p>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default Dashboard
