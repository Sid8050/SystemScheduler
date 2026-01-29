import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Globe, Plus, Trash2, Shield, Ban, AlertTriangle } from 'lucide-react'
import { api } from '../api/client'

function NetworkControl() {
  const [newSite, setNewSite] = useState({
    domain: '',
    category: '',
    reason: '',
  })
  const [showForm, setShowForm] = useState(false)
  
  const queryClient = useQueryClient()
  
  const { data, isLoading } = useQuery({
    queryKey: ['blocked-sites'],
    queryFn: () => api.getBlockedSites().then(r => r.data),
  })
  
  const addMutation = useMutation({
    mutationFn: (site) => api.addBlockedSite(site),
    onSuccess: () => {
      queryClient.invalidateQueries(['blocked-sites'])
      setShowForm(false)
      setNewSite({ domain: '', category: '', reason: '' })
    },
  })
  
  const removeMutation = useMutation({
    mutationFn: (id) => api.removeBlockedSite(id),
    onSuccess: () => {
      queryClient.invalidateQueries(['blocked-sites'])
    },
  })
  
  const sites = data?.sites || []
  
  const categories = [
    { value: 'social_media', label: 'Social Media' },
    { value: 'gambling', label: 'Gambling' },
    { value: 'adult', label: 'Adult Content' },
    { value: 'streaming', label: 'Streaming' },
    { value: 'gaming', label: 'Gaming' },
    { value: 'other', label: 'Other' },
  ]
  
  const handleSubmit = (e) => {
    e.preventDefault()
    if (newSite.domain) {
      addMutation.mutate(newSite)
    }
  }
  
  return (
    <div className="space-y-8 animate-fade-in">
      {/* Header */}
      <div className="flex justify-between items-center border-b border-zinc-800 pb-6">
        <div>
          <h1 className="text-3xl font-bold text-white tracking-tight">Network Control</h1>
          <p className="text-zinc-500 mt-2 font-medium">Block websites and manage DNS filtering rules</p>
        </div>
        
        <button
          onClick={() => setShowForm(true)}
          className="flex items-center px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-500 transition-all shadow-[0_0_20px_rgba(220,38,38,0.3)] hover:shadow-[0_0_30px_rgba(220,38,38,0.5)] border border-red-500/50"
        >
          <Ban className="w-4 h-4 mr-2" />
          Block Site
        </button>
      </div>
      
      {/* Info Card */}
      <div className="bg-red-500/5 border border-red-500/20 rounded-xl p-6 relative overflow-hidden group">
        <div className="absolute inset-0 bg-gradient-to-br from-red-500/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
        <div className="flex items-start relative z-10">
          <div className="p-3 bg-red-500/10 rounded-lg mr-4 border border-red-500/20">
             <Shield className="w-6 h-6 text-red-400" />
          </div>
          <div>
            <h3 className="text-base font-semibold text-red-400 mb-1">Network Blocking Active</h3>
            <p className="text-sm text-red-200/70 leading-relaxed">
              Blocked sites are denied at the DNS level on all endpoints. Changes take effect within 60 seconds.
              Use wildcards like <code className="bg-red-900/30 px-1 py-0.5 rounded text-red-200">*.facebook.com</code> to block all subdomains.
            </p>
          </div>
        </div>
      </div>
      
      {/* Add Form */}
      {showForm && (
        <div className="bg-zinc-900/50 backdrop-blur-sm rounded-xl border border-zinc-800 p-6 animate-fade-in-up">
          <h2 className="text-lg font-semibold text-white mb-6 flex items-center gap-2">
            <Ban className="w-5 h-5 text-red-500" />
            Block Website
          </h2>
          
          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-zinc-400 mb-2">
                Domain <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                value={newSite.domain}
                onChange={(e) => setNewSite({ ...newSite, domain: e.target.value })}
                placeholder="e.g., facebook.com or *.facebook.com"
                className="w-full px-4 py-3 bg-zinc-950 border border-zinc-800 rounded-lg focus:ring-2 focus:ring-red-500/50 focus:border-red-500/50 text-zinc-100 placeholder-zinc-700 outline-none transition-all font-mono"
                required
              />
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="block text-sm font-medium text-zinc-400 mb-2">
                  Category
                </label>
                <div className="relative">
                  <select
                    value={newSite.category}
                    onChange={(e) => setNewSite({ ...newSite, category: e.target.value })}
                    className="w-full px-4 py-3 bg-zinc-950 border border-zinc-800 rounded-lg focus:ring-2 focus:ring-red-500/50 focus:border-red-500/50 text-zinc-100 outline-none transition-all appearance-none"
                  >
                    <option value="">Select category</option>
                    {categories.map((cat) => (
                      <option key={cat.value} value={cat.value}>{cat.label}</option>
                    ))}
                  </select>
                  <div className="absolute right-4 top-1/2 -translate-y-1/2 pointer-events-none text-zinc-500">
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7" /></svg>
                  </div>
                </div>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-zinc-400 mb-2">
                  Reason
                </label>
                <input
                  type="text"
                  value={newSite.reason}
                  onChange={(e) => setNewSite({ ...newSite, reason: e.target.value })}
                  placeholder="e.g., Productivity"
                  className="w-full px-4 py-3 bg-zinc-950 border border-zinc-800 rounded-lg focus:ring-2 focus:ring-red-500/50 focus:border-red-500/50 text-zinc-100 placeholder-zinc-700 outline-none transition-all"
                />
              </div>
            </div>
            
            <div className="flex gap-4 pt-2">
              <button
                type="submit"
                className="px-6 py-2.5 bg-red-600 text-white font-medium rounded-lg hover:bg-red-500 transition-colors shadow-lg shadow-red-900/20"
              >
                Block Site
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
      
      {/* Categories Summary */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
        {categories.slice(0, 3).map((cat) => {
          const count = sites.filter(s => s.category === cat.value).length
          return (
            <div key={cat.value} className="bg-zinc-900/50 backdrop-blur-sm rounded-xl p-6 border border-zinc-800">
              <p className="text-sm font-medium text-zinc-500 uppercase tracking-wide">{cat.label}</p>
              <p className="text-3xl font-bold text-white mt-2">{count} <span className="text-sm text-zinc-600 font-normal">blocked</span></p>
            </div>
          )
        })}
      </div>
      
      {/* Blocked Sites Table */}
      <div className="bg-zinc-900/50 backdrop-blur-sm rounded-xl border border-zinc-800 overflow-hidden">
        <div className="px-6 py-4 border-b border-zinc-800 flex items-center gap-2">
          <Globe className="w-4 h-4 text-zinc-400" />
          <h2 className="text-sm font-semibold text-zinc-300 uppercase tracking-wider">Blocked Sites ({sites.length})</h2>
        </div>
        
        {isLoading ? (
          <div className="flex items-center justify-center py-20">
            <div className="w-12 h-12 border-4 border-red-500/30 border-t-red-500 rounded-full animate-spin"></div>
          </div>
        ) : sites.length === 0 ? (
          <div className="text-center py-20">
            <div className="w-16 h-16 bg-zinc-800/50 rounded-full flex items-center justify-center mx-auto mb-4">
              <Globe className="w-8 h-8 text-zinc-600" />
            </div>
            <h3 className="text-lg font-medium text-white">No sites blocked</h3>
            <p className="text-zinc-500 mt-2">Add websites to block them on all endpoints.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-zinc-800">
              <thead className="bg-zinc-900/80">
                <tr>
                  <th className="px-6 py-4 text-left text-xs font-medium text-zinc-500 uppercase tracking-wider">Domain</th>
                  <th className="px-6 py-4 text-left text-xs font-medium text-zinc-500 uppercase tracking-wider">Category</th>
                  <th className="px-6 py-4 text-left text-xs font-medium text-zinc-500 uppercase tracking-wider">Reason</th>
                  <th className="px-6 py-4 text-right text-xs font-medium text-zinc-500 uppercase tracking-wider">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-800">
                {sites.map((site) => (
                  <tr key={site.id} className="hover:bg-zinc-800/30 transition-colors group">
                    <td className="px-6 py-4">
                      <div className="flex items-center">
                        <div className="p-2 bg-zinc-800 rounded-lg mr-3 group-hover:bg-red-500/10 group-hover:text-red-400 transition-colors">
                          <Ban className="w-4 h-4 text-red-500" />
                        </div>
                        <span className="text-sm font-medium text-zinc-200">{site.domain}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      {site.category && (
                        <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-zinc-800 text-zinc-300 border border-zinc-700">
                          {categories.find(c => c.value === site.category)?.label || site.category}
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-4 text-sm text-zinc-400">{site.reason || '-'}</td>
                    <td className="px-6 py-4 text-right">
                      <button
                        onClick={() => removeMutation.mutate(site.id)}
                        className="text-zinc-500 hover:text-emerald-400 p-2 hover:bg-emerald-500/10 rounded-lg transition-all"
                        title="Unblock"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
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

export default NetworkControl
