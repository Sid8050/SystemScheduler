import React, { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { 
  AlertTriangle, 
  AlertCircle, 
  Info,
  Filter,
  Search,
  Activity,
  CheckCircle2
} from 'lucide-react'
import { api } from '../api/client'

function SeverityBadge({ severity }) {
  const configs = {
    critical: { 
      color: 'bg-red-500/10 text-red-400 border border-red-500/20 shadow-[0_0_10px_rgba(239,68,68,0.2)]', 
      icon: AlertTriangle 
    },
    error: { 
      color: 'bg-orange-500/10 text-orange-400 border border-orange-500/20 shadow-[0_0_10px_rgba(249,115,22,0.2)]', 
      icon: AlertCircle 
    },
    warning: { 
      color: 'bg-amber-500/10 text-amber-400 border border-amber-500/20', 
      icon: AlertTriangle 
    },
    info: { 
      color: 'bg-blue-500/10 text-blue-400 border border-blue-500/20', 
      icon: Info 
    },
    success: {
      color: 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20',
      icon: CheckCircle2
    }
  }
  
  const config = configs[severity] || configs.info
  const Icon = config.icon
  
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${config.color} backdrop-blur-sm transition-all duration-300`}>
      <Icon className="w-3 h-3 mr-1" />
      <span className="capitalize">{severity}</span>
    </span>
  )
}

function formatTime(dateString) {
  const date = new Date(dateString)
  return date.toLocaleString()
}

function Events() {
  const [filters, setFilters] = useState({
    severity: '',
    event_type: '',
  })
  
  const { data, isLoading } = useQuery({
    queryKey: ['events', filters],
    queryFn: () => api.getEvents(filters).then(r => r.data),
    refetchInterval: 30000,
  })
  
  const events = data?.events || []
  
  return (
    <div className="space-y-8 animate-fade-in">
      {/* Header */}
      <div className="flex justify-between items-end border-b border-zinc-800 pb-6">
        <div>
          <h1 className="text-3xl font-bold text-white tracking-tight">Security Events</h1>
          <p className="text-zinc-500 mt-2 font-medium">Monitor real-time security events across your infrastructure</p>
        </div>
        <div className="flex items-center gap-2 text-sm text-zinc-500">
          <Activity className="w-4 h-4 text-emerald-500 animate-pulse" />
          Live Monitoring
        </div>
      </div>
      
      {/* Filters */}
      <div className="bg-zinc-900/50 backdrop-blur-sm rounded-xl border border-zinc-800 p-4">
        <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4">
          <div className="flex items-center text-zinc-400">
            <Filter className="w-4 h-4 mr-2 text-blue-400" />
            <span className="text-sm font-medium">Filters:</span>
          </div>
          
          <div className="flex gap-4 w-full sm:w-auto">
            <select
              value={filters.severity}
              onChange={(e) => setFilters({ ...filters, severity: e.target.value })}
              className="w-full sm:w-auto px-3 py-2 bg-zinc-900 border border-zinc-700 rounded-lg text-sm text-zinc-200 focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50 outline-none transition-all"
            >
              <option value="">All Severities</option>
              <option value="critical">Critical</option>
              <option value="error">Error</option>
              <option value="warning">Warning</option>
              <option value="info">Info</option>
            </select>
            
            <select
              value={filters.event_type}
              onChange={(e) => setFilters({ ...filters, event_type: e.target.value })}
              className="w-full sm:w-auto px-3 py-2 bg-zinc-900 border border-zinc-700 rounded-lg text-sm text-zinc-200 focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50 outline-none transition-all"
            >
              <option value="">All Types</option>
              <option value="usb">USB Events</option>
              <option value="net">Network Events</option>
              <option value="file">File Events</option>
              <option value="data">Data Detection</option>
            </select>
          </div>
        </div>
      </div>
      
      {/* Events List */}
      <div className="bg-zinc-900/50 backdrop-blur-sm rounded-xl border border-zinc-800 overflow-hidden">
        {isLoading ? (
          <div className="flex items-center justify-center py-20">
             <div className="w-12 h-12 border-4 border-blue-500/30 border-t-blue-500 rounded-full animate-spin"></div>
          </div>
        ) : events.length === 0 ? (
          <div className="text-center py-20">
            <div className="w-16 h-16 bg-zinc-800/50 rounded-full flex items-center justify-center mx-auto mb-4">
              <Info className="w-8 h-8 text-zinc-600" />
            </div>
            <h3 className="text-lg font-medium text-white">No events found</h3>
            <p className="text-zinc-500 mt-2">Events will appear here as they occur.</p>
          </div>
        ) : (
          <div className="divide-y divide-zinc-800/50">
            {events.map((event) => (
              <div key={event.id} className="p-4 hover:bg-zinc-800/30 transition-colors group">
                <div className="flex flex-col sm:flex-row items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-3 mb-2">
                      <SeverityBadge severity={event.severity} />
                      <span className="text-xs text-zinc-500 font-mono bg-zinc-800/50 px-2 py-0.5 rounded border border-zinc-700/50">
                        {event.event_type}
                      </span>
                    </div>
                    <p className="text-sm text-zinc-300 font-medium">{event.message}</p>
                    {event.details && Object.keys(event.details).length > 0 && (
                      <div className="mt-3 text-xs text-zinc-400 bg-black/20 rounded-lg p-3 font-mono border border-zinc-800/50 overflow-x-auto">
                        <pre>{JSON.stringify(event.details, null, 2)}</pre>
                      </div>
                    )}
                  </div>
                  <div className="text-xs text-zinc-500 font-mono whitespace-nowrap flex-shrink-0 pt-1">
                    {formatTime(event.timestamp)}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default Events
