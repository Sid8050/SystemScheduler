import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { 
  Monitor, 
  MoreVertical, 
  Trash2, 
  RefreshCw,
  CheckCircle,
  XCircle,
  AlertCircle
} from 'lucide-react'
import { api } from '../api/client'

function StatusBadge({ status }) {
  const configs = {
    online: { 
      color: 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20', 
      icon: CheckCircle 
    },
    offline: { 
      color: 'bg-zinc-500/10 text-zinc-400 border border-zinc-500/20', 
      icon: XCircle 
    },
    warning: { 
      color: 'bg-amber-500/10 text-amber-400 border border-amber-500/20', 
      icon: AlertCircle 
    },
    error: { 
      color: 'bg-red-500/10 text-red-400 border border-red-500/20', 
      icon: AlertCircle 
    },
  }
  
  const config = configs[status] || configs.offline
  const Icon = config.icon
  
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${config.color} backdrop-blur-sm`}>
      <Icon className="w-3 h-3 mr-1" />
      {status}
    </span>
  )
}

function formatBytes(bytes) {
  if (!bytes) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

function timeAgo(dateString) {
  if (!dateString) return 'Never'
  
  const date = new Date(dateString)
  const now = new Date()
  const seconds = Math.floor((now - date) / 1000)
  
  if (seconds < 60) return 'Just now'
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`
  return `${Math.floor(seconds / 86400)}d ago`
}

function Endpoints() {
  const queryClient = useQueryClient()
  const [syncingId, setSyncingId] = useState(null)
  
  const { data, isLoading } = useQuery({
    queryKey: ['endpoints'],
    queryFn: () => api.getEndpoints().then(r => r.data),
    refetchInterval: 10000
  })
  
  const deleteMutation = useMutation({
    mutationFn: (id) => api.deleteEndpoint(id),
    onSuccess: () => queryClient.invalidateQueries(['endpoints']),
  })

  const handleSync = (id) => {
    setSyncingId(id)
    queryClient.invalidateQueries(['endpoints'])
    setTimeout(() => setSyncingId(null), 1500)
  }

  const endpoints = data?.endpoints || []

  
  return (
    <div className="space-y-8 animate-fade-in">
      {/* Header */}
      <div className="flex justify-between items-center border-b border-zinc-800 pb-6">
        <div>
          <h1 className="text-3xl font-bold text-white tracking-tight">Endpoints</h1>
          <p className="text-zinc-500 mt-2 font-medium">Manage registered security agents</p>
        </div>
        
        <button
          onClick={() => refetch()}
          className="flex items-center px-4 py-2 bg-zinc-900 border border-zinc-800 rounded-lg hover:bg-zinc-800 hover:border-zinc-700 text-zinc-300 transition-all duration-300"
        >
          <RefreshCw className="w-4 h-4 mr-2" />
          Refresh
        </button>
      </div>
      
      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="bg-zinc-900/50 backdrop-blur-sm rounded-xl p-6 border border-zinc-800">
          <p className="text-sm font-medium text-zinc-500 uppercase tracking-wide">Total Endpoints</p>
          <p className="text-3xl font-bold text-white mt-2">{data?.total || 0}</p>
        </div>
        <div className="bg-zinc-900/50 backdrop-blur-sm rounded-xl p-6 border border-zinc-800">
          <p className="text-sm font-medium text-zinc-500 uppercase tracking-wide">Online</p>
          <p className="text-3xl font-bold text-emerald-400 mt-2">
            {endpoints.filter(e => e.status === 'online').length}
          </p>
        </div>
        <div className="bg-zinc-900/50 backdrop-blur-sm rounded-xl p-6 border border-zinc-800">
          <p className="text-sm font-medium text-zinc-500 uppercase tracking-wide">Offline</p>
          <p className="text-3xl font-bold text-zinc-400 mt-2">
            {endpoints.filter(e => e.status === 'offline').length}
          </p>
        </div>
        <div className="bg-zinc-900/50 backdrop-blur-sm rounded-xl p-6 border border-zinc-800">
          <p className="text-sm font-medium text-zinc-500 uppercase tracking-wide">Warnings</p>
          <p className="text-3xl font-bold text-amber-400 mt-2">
            {endpoints.filter(e => e.status === 'warning').length}
          </p>
        </div>
      </div>
      
      {/* Table */}
      <div className="bg-zinc-900/50 backdrop-blur-sm rounded-xl border border-zinc-800 overflow-hidden">
        {isLoading ? (
          <div className="flex items-center justify-center py-20">
            <div className="relative">
              <div className="w-12 h-12 border-4 border-blue-500/30 border-t-blue-500 rounded-full animate-spin"></div>
            </div>
          </div>
        ) : endpoints.length === 0 ? (
          <div className="text-center py-20">
            <div className="w-16 h-16 bg-zinc-800/50 rounded-full flex items-center justify-center mx-auto mb-4">
              <Monitor className="w-8 h-8 text-zinc-600" />
            </div>
            <h3 className="text-lg font-medium text-white">No endpoints registered</h3>
            <p className="text-zinc-500 mt-2">Install the agent on your machines to see them here.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-zinc-800">
              <thead className="bg-zinc-900/80">
                <tr>
                  <th className="px-6 py-4 text-left text-xs font-medium text-zinc-500 uppercase tracking-wider">
                    Hostname
                  </th>
                  <th className="px-6 py-4 text-left text-xs font-medium text-zinc-500 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-6 py-4 text-left text-xs font-medium text-zinc-500 uppercase tracking-wider">
                    Last Seen
                  </th>
                  <th className="px-6 py-4 text-left text-xs font-medium text-zinc-500 uppercase tracking-wider">
                    Files Backed Up
                  </th>
                  <th className="px-6 py-4 text-left text-xs font-medium text-zinc-500 uppercase tracking-wider">
                    Events
                  </th>
                  <th className="px-6 py-4 text-right text-xs font-medium text-zinc-500 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-800">
                {endpoints.map((endpoint) => (
                  <tr key={endpoint.id} className="hover:bg-zinc-800/30 transition-colors">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center">
                        <div className="p-2 rounded-lg bg-zinc-800 mr-3">
                          <Monitor className="w-5 h-5 text-zinc-400" />
                        </div>
                        <div>
                          <div className="text-sm font-medium text-zinc-200">
                            {endpoint.hostname}
                          </div>
                          <div className="text-xs text-zinc-500 font-mono mt-0.5">
                            {endpoint.machine_id}
                          </div>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <StatusBadge status={endpoint.status} />
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-zinc-400">
                      {timeAgo(endpoint.last_seen)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm text-zinc-200">
                        {endpoint.stats?.files_backed_up?.toLocaleString() || 0}
                      </div>
                      <div className="text-xs text-zinc-500 font-mono mt-0.5">
                        {formatBytes(endpoint.stats?.backup_size || 0)}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center gap-3 text-sm">
                        <span className="flex items-center text-amber-500">
                          {endpoint.stats?.usb_events || 0} <span className="text-zinc-500 ml-1 text-xs">USB</span>
                        </span>
                        <span className="flex items-center text-red-500">
                          {endpoint.stats?.network_blocks || 0} <span className="text-zinc-500 ml-1 text-xs">Blocked</span>
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => handleSync(endpoint.id)}
                          className={`p-2 rounded-lg transition-all ${syncingId === endpoint.id ? 'text-blue-400 bg-blue-500/10' : 'text-zinc-500 hover:text-blue-400 hover:bg-blue-500/10'}`}
                          title="Refresh Stats"
                        >
                          <RefreshCw className={`w-4 h-4 ${syncingId === endpoint.id ? 'animate-spin' : ''}`} />
                        </button>
                        <button
                          onClick={() => deleteMutation.mutate(endpoint.id)}
                          className="text-zinc-500 hover:text-red-400 p-2 hover:bg-red-500/10 rounded-lg transition-all"
                          title="Delete endpoint"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}

export default Endpoints
