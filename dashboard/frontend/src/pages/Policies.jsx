import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Shield, Plus, Edit, Trash2, Check, Lock, HardDrive, Wifi, Eye } from 'lucide-react'
import { api } from '../api/client'

function Policies() {
  const [showForm, setShowForm] = useState(false)
  const [editingPolicy, setEditingPolicy] = useState(null)
  
  const queryClient = useQueryClient()
  
  const { data, isLoading } = useQuery({
    queryKey: ['policies'],
    queryFn: () => api.getPolicies().then(r => r.data),
  })
  
  const createMutation = useMutation({
    mutationFn: (policy) => api.createPolicy(policy),
    onSuccess: () => {
      queryClient.invalidateQueries(['policies'])
      setShowForm(false)
    },
  })
  
  const policies = data?.policies || []
  
  const defaultConfig = {
    backup: { enabled: true },
    usb_control: { enabled: true, mode: 'monitor' },
    network: { enabled: true, blocking_enabled: true },
    data_detection: { enabled: true },
  }
  
  const [newPolicy, setNewPolicy] = useState({
    name: '',
    description: '',
    config: defaultConfig,
  })
  
  const handleSubmit = (e) => {
    e.preventDefault()
    if (newPolicy.name) {
      createMutation.mutate(newPolicy)
    }
  }
  
  return (
    <div className="space-y-8 animate-fade-in">
      {/* Header */}
      <div className="flex justify-between items-center border-b border-zinc-800 pb-6">
        <div>
          <h1 className="text-3xl font-bold text-white tracking-tight">Security Policies</h1>
          <p className="text-zinc-500 mt-2 font-medium">Configure and apply security rules to endpoints</p>
        </div>
        
        <button
          onClick={() => setShowForm(true)}
          className="flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-500 transition-all shadow-[0_0_20px_rgba(37,99,235,0.3)] hover:shadow-[0_0_30px_rgba(37,99,235,0.5)] border border-blue-500/50"
        >
          <Plus className="w-4 h-4 mr-2" />
          Create Policy
        </button>
      </div>
      
      {/* Create Form */}
      {showForm && (
        <div className="bg-zinc-900/50 backdrop-blur-sm rounded-xl border border-zinc-800 p-6 animate-fade-in-up">
          <h2 className="text-lg font-semibold text-white mb-6 flex items-center gap-2">
            <Shield className="w-5 h-5 text-blue-500" />
            Create New Policy
          </h2>
          
          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="block text-sm font-medium text-zinc-400 mb-2">
                  Policy Name <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={newPolicy.name}
                  onChange={(e) => setNewPolicy({ ...newPolicy, name: e.target.value })}
                  placeholder="e.g., Standard Security"
                  className="w-full px-4 py-3 bg-zinc-950 border border-zinc-800 rounded-lg focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50 text-zinc-100 placeholder-zinc-700 outline-none transition-all"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-zinc-400 mb-2">
                  Description
                </label>
                <input
                  type="text"
                  value={newPolicy.description}
                  onChange={(e) => setNewPolicy({ ...newPolicy, description: e.target.value })}
                  placeholder="Policy description"
                  className="w-full px-4 py-3 bg-zinc-950 border border-zinc-800 rounded-lg focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50 text-zinc-100 placeholder-zinc-700 outline-none transition-all"
                />
              </div>
            </div>
            
            <div className="border-t border-zinc-800 pt-6">
              <h3 className="text-sm font-medium text-zinc-300 mb-4 uppercase tracking-wider">Module Settings</h3>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <label className={`flex items-center p-4 rounded-xl cursor-pointer border transition-all ${newPolicy.config.backup?.enabled ? 'bg-blue-500/10 border-blue-500/30' : 'bg-zinc-900 border-zinc-800 hover:border-zinc-700'}`}>
                  <input
                    type="checkbox"
                    checked={newPolicy.config.backup?.enabled}
                    onChange={(e) => setNewPolicy({
                      ...newPolicy,
                      config: {
                        ...newPolicy.config,
                        backup: { ...newPolicy.config.backup, enabled: e.target.checked }
                      }
                    })}
                    className="w-5 h-5 text-blue-600 rounded bg-zinc-800 border-zinc-700 focus:ring-blue-500 focus:ring-offset-0"
                  />
                  <div className="ml-3">
                    <span className={`block text-sm font-medium ${newPolicy.config.backup?.enabled ? 'text-blue-400' : 'text-zinc-300'}`}>File Backup to S3</span>
                    <span className="block text-xs text-zinc-500 mt-0.5">Automated backup of critical files</span>
                  </div>
                </label>
                
                <label className={`flex items-center p-4 rounded-xl cursor-pointer border transition-all ${newPolicy.config.usb_control?.enabled ? 'bg-amber-500/10 border-amber-500/30' : 'bg-zinc-900 border-zinc-800 hover:border-zinc-700'}`}>
                  <input
                    type="checkbox"
                    checked={newPolicy.config.usb_control?.enabled}
                    onChange={(e) => setNewPolicy({
                      ...newPolicy,
                      config: {
                        ...newPolicy.config,
                        usb_control: { ...newPolicy.config.usb_control, enabled: e.target.checked }
                      }
                    })}
                    className="w-5 h-5 text-amber-600 rounded bg-zinc-800 border-zinc-700 focus:ring-amber-500 focus:ring-offset-0"
                  />
                  <div className="ml-3">
                    <span className={`block text-sm font-medium ${newPolicy.config.usb_control?.enabled ? 'text-amber-400' : 'text-zinc-300'}`}>USB Device Control</span>
                    <span className="block text-xs text-zinc-500 mt-0.5">Restrict unauthorized USB storage</span>
                  </div>
                </label>
                
                <label className={`flex items-center p-4 rounded-xl cursor-pointer border transition-all ${newPolicy.config.network?.enabled ? 'bg-red-500/10 border-red-500/30' : 'bg-zinc-900 border-zinc-800 hover:border-zinc-700'}`}>
                  <input
                    type="checkbox"
                    checked={newPolicy.config.network?.enabled}
                    onChange={(e) => setNewPolicy({
                      ...newPolicy,
                      config: {
                        ...newPolicy.config,
                        network: { ...newPolicy.config.network, enabled: e.target.checked }
                      }
                    })}
                    className="w-5 h-5 text-red-600 rounded bg-zinc-800 border-zinc-700 focus:ring-red-500 focus:ring-offset-0"
                  />
                  <div className="ml-3">
                    <span className={`block text-sm font-medium ${newPolicy.config.network?.enabled ? 'text-red-400' : 'text-zinc-300'}`}>Network Monitoring</span>
                    <span className="block text-xs text-zinc-500 mt-0.5">DNS filtering and traffic analysis</span>
                  </div>
                </label>
                
                <label className={`flex items-center p-4 rounded-xl cursor-pointer border transition-all ${newPolicy.config.data_detection?.enabled ? 'bg-violet-500/10 border-violet-500/30' : 'bg-zinc-900 border-zinc-800 hover:border-zinc-700'}`}>
                  <input
                    type="checkbox"
                    checked={newPolicy.config.data_detection?.enabled}
                    onChange={(e) => setNewPolicy({
                      ...newPolicy,
                      config: {
                        ...newPolicy.config,
                        data_detection: { ...newPolicy.config.data_detection, enabled: e.target.checked }
                      }
                    })}
                    className="w-5 h-5 text-violet-600 rounded bg-zinc-800 border-zinc-700 focus:ring-violet-500 focus:ring-offset-0"
                  />
                  <div className="ml-3">
                    <span className={`block text-sm font-medium ${newPolicy.config.data_detection?.enabled ? 'text-violet-400' : 'text-zinc-300'}`}>Sensitive Data Detection</span>
                    <span className="block text-xs text-zinc-500 mt-0.5">Scan for PII and sensitive patterns</span>
                  </div>
                </label>
              </div>
            </div>
            
            <div className="flex gap-4 pt-4">
              <button
                type="submit"
                className="px-6 py-2.5 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-500 transition-colors shadow-lg shadow-blue-900/20"
              >
                Create Policy
              </button>
              <button
                type="button"
                onClick={() => setShowForm(false)}
                className="px-6 py-2.5 bg-zinc-800 text-zinc-300 font-medium rounded-lg hover:bg-zinc-700 transition-colors border border-zinc-700"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}
      
      {/* Policies Grid */}
      {isLoading ? (
        <div className="flex items-center justify-center py-20">
          <div className="w-12 h-12 border-4 border-blue-500/30 border-t-blue-500 rounded-full animate-spin"></div>
        </div>
      ) : policies.length === 0 ? (
        <div className="bg-zinc-900/50 backdrop-blur-sm rounded-xl border border-zinc-800 p-12 text-center">
          <div className="w-16 h-16 bg-zinc-800/50 rounded-full flex items-center justify-center mx-auto mb-4">
            <Shield className="w-8 h-8 text-zinc-600" />
          </div>
          <h3 className="text-lg font-medium text-white">No policies created</h3>
          <p className="text-zinc-500 mt-2">Create a policy to configure endpoint security settings.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {policies.map((policy) => (
            <div key={policy.id} className="bg-zinc-900/50 backdrop-blur-sm rounded-xl border border-zinc-800 p-6 hover:border-zinc-700 transition-colors group">
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center">
                  <div className="p-3 bg-zinc-800 rounded-lg mr-3 group-hover:bg-blue-500/10 group-hover:text-blue-400 transition-colors">
                    <Shield className="w-6 h-6 text-zinc-400 group-hover:text-blue-400" />
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold text-white group-hover:text-blue-400 transition-colors">{policy.name}</h3>
                    {policy.is_default && (
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] uppercase font-bold tracking-wider bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 mt-1">
                        Default
                      </span>
                    )}
                  </div>
                </div>
              </div>
              
              <p className="text-sm text-zinc-500 mb-6 line-clamp-2 h-10">{policy.description || 'No description provided.'}</p>
              
              <div className="border-t border-zinc-800 pt-4">
                <p className="text-xs font-medium text-zinc-500 mb-3 uppercase tracking-wider">Active Modules</p>
                <div className="flex flex-wrap gap-2">
                  {policy.config?.backup?.enabled && (
                    <span className="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium bg-blue-500/10 text-blue-400 border border-blue-500/20" title="Backup">
                      <HardDrive className="w-3 h-3 mr-1" />
                      Backup
                    </span>
                  )}
                  {policy.config?.usb_control?.enabled && (
                    <span className="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium bg-amber-500/10 text-amber-400 border border-amber-500/20" title="USB Control">
                      <Lock className="w-3 h-3 mr-1" />
                      USB
                    </span>
                  )}
                  {policy.config?.network?.enabled && (
                    <span className="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium bg-red-500/10 text-red-400 border border-red-500/20" title="Network">
                      <Wifi className="w-3 h-3 mr-1" />
                      Net
                    </span>
                  )}
                  {policy.config?.data_detection?.enabled && (
                    <span className="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium bg-violet-500/10 text-violet-400 border border-violet-500/20" title="DLP">
                      <Eye className="w-3 h-3 mr-1" />
                      DLP
                    </span>
                  )}
                </div>
              </div>
              
              <div className="border-t border-zinc-800 mt-4 pt-4 flex justify-between items-center">
                <span className="text-sm text-zinc-500 font-mono">
                  {policy.endpoint_count || 0} endpoints
                </span>
                <button className="p-2 text-zinc-400 hover:text-white hover:bg-zinc-800 rounded-lg transition-all">
                  <Edit className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default Policies
