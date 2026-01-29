import React, { useState, useEffect } from 'react'
import { 
  Calendar, 
  Clock, 
  Play, 
  Trash2, 
  Edit, 
  Plus, 
  RefreshCw, 
  CheckCircle, 
  XCircle, 
  AlertCircle,
  History,
  X
} from 'lucide-react'
import { api } from '../api/client'

const Schedules = () => {
  const [schedules, setSchedules] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [presets, setPresets] = useState([])
  
  // Modal states
  const [showModal, setShowModal] = useState(false)
  const [showHistoryModal, setShowHistoryModal] = useState(false)
  const [showDeleteModal, setShowDeleteModal] = useState(false)
  const [isEditing, setIsEditing] = useState(false)
  const [processing, setProcessing] = useState(false)
  
  // Selected item states
  const [currentSchedule, setCurrentSchedule] = useState(null)
  const [scheduleRuns, setScheduleRuns] = useState([])
  const [loadingRuns, setLoadingRuns] = useState(false)
  
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    schedule_type: 'full_scan',
    cron_expression: '0 0 * * *',
    target_paths: '',
    target_endpoints: []
  })

  // Schedule types mapping
  const scheduleTypes = {
    full_scan: 'Full System Scan',
    incremental_backup: 'Incremental Backup',
    sensitive_scan: 'Sensitive Data Scan',
    network_audit: 'Network Audit'
  }

  // Fetch initial data
  useEffect(() => {
    fetchSchedules()
    fetchPresets()
  }, [])

  const fetchSchedules = async () => {
    try {
      setLoading(true)
      const response = await api.getSchedules()
      setSchedules(response.data.schedules || [])
      setError(null)
    } catch (err) {
      console.error('Failed to fetch schedules:', err)
      setError('Failed to load schedules. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const fetchPresets = async () => {
    try {
      const response = await api.getSchedulePresets()
      setPresets(response.data.presets || [])
    } catch (err) {
      console.error('Failed to fetch presets:', err)
      setPresets([
        { label: 'Daily at Midnight', value: '0 0 * * *' },
        { label: 'Weekly (Sunday)', value: '0 0 * * 0' },
        { label: 'Hourly', value: '0 * * * *' }
      ])
    }
  }

  const fetchScheduleRuns = async (id) => {
    try {
      setLoadingRuns(true)
      const response = await api.getScheduleRuns(id)
      setScheduleRuns(response.data.runs || [])
    } catch (err) {
      console.error('Failed to fetch runs:', err)
      setScheduleRuns([])
    } finally {
      setLoadingRuns(false)
    }
  }

  // Handlers
  const handleOpenCreate = () => {
    setFormData({
      name: '',
      description: '',
      schedule_type: 'full_scan',
      cron_expression: '0 0 * * *',
      target_paths: '',
      target_endpoints: []
    })
    setIsEditing(false)
    setCurrentSchedule(null)
    setShowModal(true)
  }

  const handleOpenEdit = (schedule) => {
    setFormData({
      name: schedule.name,
      description: schedule.description || '',
      schedule_type: schedule.schedule_type,
      cron_expression: schedule.cron_expression,
      target_paths: Array.isArray(schedule.target_paths) ? schedule.target_paths.join(', ') : schedule.target_paths,
      target_endpoints: schedule.target_endpoints || []
    })
    setIsEditing(true)
    setCurrentSchedule(schedule)
    setShowModal(true)
  }

  const handleOpenDelete = (schedule) => {
    setCurrentSchedule(schedule)
    setShowDeleteModal(true)
  }

  const handleOpenHistory = (schedule) => {
    setCurrentSchedule(schedule)
    setScheduleRuns([])
    setShowHistoryModal(true)
    fetchScheduleRuns(schedule.id)
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setProcessing(true)
    
    // Parse paths
    const paths = formData.target_paths
      .split(',')
      .map(p => p.trim())
      .filter(p => p)
      
    const payload = {
      ...formData,
      target_paths: paths
    }

    try {
      if (isEditing) {
        await api.updateSchedule(currentSchedule.id, payload)
      } else {
        await api.createSchedule(payload)
      }
      setShowModal(false)
      fetchSchedules()
    } catch (err) {
      console.error('Operation failed:', err)
      alert('Failed to save schedule. Please check your inputs.')
    } finally {
      setProcessing(false)
    }
  }

  const handleDelete = async () => {
    if (!currentSchedule) return
    setProcessing(true)
    try {
      await api.deleteSchedule(currentSchedule.id)
      setShowDeleteModal(false)
      fetchSchedules()
    } catch (err) {
      console.error('Delete failed:', err)
      alert('Failed to delete schedule.')
    } finally {
      setProcessing(false)
      setCurrentSchedule(null)
    }
  }

  const handleToggleActive = async (id) => {
    try {
      await api.toggleSchedule(id)
      // Optimistic update or refresh
      setSchedules(schedules.map(s => 
        s.id === id ? { ...s, is_active: !s.is_active } : s
      ))
    } catch (err) {
      console.error('Toggle failed:', err)
      alert('Failed to toggle schedule status.')
    }
  }

  const handleRunNow = async (id) => {
    try {
      await api.runScheduleNow(id)
      alert('Schedule execution triggered successfully.')
      fetchSchedules() // Refresh to see updated last run status potentially
    } catch (err) {
      console.error('Run failed:', err)
      alert('Failed to trigger schedule.')
    }
  }

  // Format helpers
  const formatCron = (cron) => {
    const preset = presets.find(p => p.value === cron)
    return preset ? preset.label : cron
  }

  const formatDate = (dateString) => {
    if (!dateString) return 'Never'
    return new Date(dateString).toLocaleString()
  }

  const getStatusColor = (status) => {
    switch (status) {
      case 'success': return 'text-emerald-400'
      case 'failed': return 'text-red-400'
      case 'running': return 'text-blue-400'
      default: return 'text-zinc-500'
    }
  }

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Header */}
      <div className="flex justify-between items-center border-b border-zinc-800 pb-6">
        <div>
          <h1 className="text-3xl font-bold text-white tracking-tight">Scheduled Scans</h1>
          <p className="text-zinc-500 mt-2 font-medium">Manage automated scans, backups, and audits</p>
        </div>
        <button
          onClick={handleOpenCreate}
          className="flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-500 transition-all shadow-[0_0_20px_rgba(37,99,235,0.3)] hover:shadow-[0_0_30px_rgba(37,99,235,0.5)] border border-blue-500/50"
        >
          <Plus className="w-4 h-4 mr-2" />
          New Schedule
        </button>
      </div>

      {/* Error Message */}
      {error && (
        <div className="bg-red-500/10 border border-red-500/20 text-red-400 p-4 rounded-xl flex items-center gap-2">
          <AlertCircle className="w-5 h-5" />
          {error}
        </div>
      )}

      {/* Loading State */}
      {loading ? (
        <div className="flex justify-center items-center py-20">
          <div className="w-12 h-12 border-4 border-blue-500/30 border-t-blue-500 rounded-full animate-spin"></div>
        </div>
      ) : (
        /* Schedules List */
        <div className="space-y-4">
          {schedules.length === 0 ? (
            <div className="text-center py-20 bg-zinc-900/50 backdrop-blur-sm rounded-xl border border-zinc-800">
              <Calendar className="w-12 h-12 text-zinc-600 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-white">No schedules found</h3>
              <p className="text-zinc-500 mt-2">Create a new schedule to get started</p>
            </div>
          ) : (
            schedules.map((schedule) => (
              <div 
                key={schedule.id}
                className="bg-zinc-900/50 backdrop-blur-sm border border-zinc-800 rounded-xl p-6 transition-all hover:border-zinc-700 hover:bg-zinc-900/80 group"
              >
                <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                  {/* Left Section: Info */}
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <h3 className="text-lg font-semibold text-white group-hover:text-blue-400 transition-colors">{schedule.name}</h3>
                      <span className={`px-2 py-0.5 text-xs font-medium rounded-full border ${
                        schedule.is_active 
                          ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' 
                          : 'bg-zinc-800 text-zinc-500 border-zinc-700'
                      }`}>
                        {schedule.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </div>
                    <div className="flex flex-wrap gap-x-6 gap-y-2 text-sm text-zinc-400">
                      <div className="flex items-center gap-1.5">
                        <Calendar className="w-4 h-4 text-zinc-500" />
                        <span className="font-mono">{formatCron(schedule.cron_expression)}</span>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <Clock className="w-4 h-4 text-zinc-500" />
                        <span>{scheduleTypes[schedule.schedule_type] || schedule.schedule_type}</span>
                      </div>
                      {schedule.last_run_at && (
                        <div className="flex items-center gap-1.5">
                          <History className="w-4 h-4 text-zinc-500" />
                          <span>Last run: {formatDate(schedule.last_run_at)}</span>
                          <span className={`ml-1 capitalize ${getStatusColor(schedule.last_run_status)}`}>
                            ({schedule.last_run_status})
                          </span>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Right Section: Actions */}
                  <div className="flex items-center gap-2 self-end md:self-auto">
                    <button
                      onClick={() => handleToggleActive(schedule.id)}
                      className={`p-2 rounded-lg transition-colors ${
                        schedule.is_active 
                          ? 'text-emerald-400 hover:bg-emerald-500/10' 
                          : 'text-zinc-500 hover:bg-zinc-800 hover:text-zinc-300'
                      }`}
                      title={schedule.is_active ? "Deactivate" : "Activate"}
                    >
                      {schedule.is_active ? <CheckCircle className="w-5 h-5" /> : <XCircle className="w-5 h-5" />}
                    </button>
                    
                    <button
                      onClick={() => handleRunNow(schedule.id)}
                      className="p-2 text-blue-400 hover:bg-blue-500/10 rounded-lg transition-colors"
                      title="Run Now"
                    >
                      <Play className="w-5 h-5" />
                    </button>

                    <button
                      onClick={() => handleOpenHistory(schedule)}
                      className="p-2 text-violet-400 hover:bg-violet-500/10 rounded-lg transition-colors"
                      title="View History"
                    >
                      <History className="w-5 h-5" />
                    </button>

                    <button
                      onClick={() => handleOpenEdit(schedule)}
                      className="p-2 text-zinc-400 hover:text-white hover:bg-zinc-800 rounded-lg transition-colors"
                      title="Edit"
                    >
                      <Edit className="w-5 h-5" />
                    </button>

                    <button
                      onClick={() => handleOpenDelete(schedule)}
                      className="p-2 text-zinc-500 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-colors"
                      title="Delete"
                    >
                      <Trash2 className="w-5 h-5" />
                    </button>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* Create/Edit Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto shadow-2xl animate-fade-in-up">
            <div className="p-6 border-b border-zinc-800 flex justify-between items-center sticky top-0 bg-zinc-900 z-10">
              <h2 className="text-xl font-bold text-white">
                {isEditing ? 'Edit Schedule' : 'Create New Schedule'}
              </h2>
              <button 
                onClick={() => setShowModal(false)}
                className="text-zinc-500 hover:text-white transition-colors"
              >
                <X className="w-6 h-6" />
              </button>
            </div>
            
            <form onSubmit={handleSubmit} className="p-6 space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-2">
                  <label className="text-sm font-medium text-zinc-400">Name</label>
                  <input
                    type="text"
                    required
                    value={formData.name}
                    onChange={e => setFormData({...formData, name: e.target.value})}
                    className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-4 py-3 text-zinc-100 focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50 outline-none transition-all placeholder-zinc-700"
                    placeholder="e.g. Daily Full Scan"
                  />
                </div>
                
                <div className="space-y-2">
                  <label className="text-sm font-medium text-zinc-400">Task Type</label>
                  <div className="relative">
                    <select
                      value={formData.schedule_type}
                      onChange={e => setFormData({...formData, schedule_type: e.target.value})}
                      className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-4 py-3 text-zinc-100 focus:ring-2 focus:ring-blue-500/50 outline-none appearance-none"
                    >
                      {Object.entries(scheduleTypes).map(([value, label]) => (
                        <option key={value} value={value}>{label}</option>
                      ))}
                    </select>
                    <div className="absolute right-4 top-1/2 -translate-y-1/2 pointer-events-none text-zinc-500">
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7" /></svg>
                    </div>
                  </div>
                </div>
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium text-zinc-400">Description</label>
                <textarea
                  value={formData.description}
                  onChange={e => setFormData({...formData, description: e.target.value})}
                  className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-4 py-3 text-zinc-100 focus:ring-2 focus:ring-blue-500/50 outline-none h-24 resize-none placeholder-zinc-700"
                  placeholder="Optional description of this schedule..."
                />
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium text-zinc-400">Schedule Frequency</label>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="relative">
                    <select
                      onChange={e => {
                        if (e.target.value) {
                          setFormData({...formData, cron_expression: e.target.value})
                        }
                      }}
                      className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-4 py-3 text-zinc-100 focus:ring-2 focus:ring-blue-500/50 outline-none appearance-none"
                    >
                      <option value="">Select a preset...</option>
                      {presets.map((preset, idx) => (
                        <option key={idx} value={preset.value}>
                          {preset.label}
                        </option>
                      ))}
                    </select>
                    <div className="absolute right-4 top-1/2 -translate-y-1/2 pointer-events-none text-zinc-500">
                       <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7" /></svg>
                    </div>
                  </div>
                  <input
                    type="text"
                    required
                    value={formData.cron_expression}
                    onChange={e => setFormData({...formData, cron_expression: e.target.value})}
                    className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-4 py-3 text-zinc-100 focus:ring-2 focus:ring-blue-500/50 outline-none font-mono text-sm"
                    placeholder="Cron expression (e.g. 0 0 * * *)"
                  />
                </div>
                <p className="text-xs text-zinc-500 mt-1">Use standard cron syntax or select a preset.</p>
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium text-zinc-400">Target Paths</label>
                <input
                  type="text"
                  required
                  value={formData.target_paths}
                  onChange={e => setFormData({...formData, target_paths: e.target.value})}
                  className="w-full bg-zinc-950 border border-zinc-800 rounded-lg px-4 py-3 text-zinc-100 focus:ring-2 focus:ring-blue-500/50 outline-none font-mono text-sm"
                  placeholder="e.g. /home/user, /var/log (comma separated)"
                />
                <p className="text-xs text-zinc-500 mt-1">Paths to be scanned or backed up.</p>
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t border-zinc-800 mt-6">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="px-6 py-2.5 text-zinc-400 hover:text-white hover:bg-zinc-800 rounded-lg transition-colors font-medium"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={processing}
                  className="px-6 py-2.5 bg-blue-600 hover:bg-blue-500 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 font-medium shadow-lg shadow-blue-900/20"
                >
                  {processing && <RefreshCw className="w-4 h-4 animate-spin" />}
                  {isEditing ? 'Save Changes' : 'Create Schedule'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {showDeleteModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
          <div className="bg-zinc-900 border border-zinc-800 rounded-xl w-full max-w-md p-6 shadow-2xl animate-fade-in-up">
            <h2 className="text-xl font-bold text-white mb-2">Delete Schedule?</h2>
            <p className="text-zinc-400 mb-6">
              Are you sure you want to delete <span className="text-white font-semibold">"{currentSchedule?.name}"</span>? This action cannot be undone.
            </p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setShowDeleteModal(false)}
                className="px-4 py-2 text-zinc-400 hover:text-white hover:bg-zinc-800 rounded-lg transition-colors font-medium"
              >
                Cancel
              </button>
              <button
                onClick={handleDelete}
                disabled={processing}
                className="px-4 py-2 bg-red-600 hover:bg-red-500 text-white rounded-lg transition-colors disabled:opacity-50 flex items-center gap-2 font-medium shadow-lg shadow-red-900/20"
              >
                {processing && <RefreshCw className="w-4 h-4 animate-spin" />}
                Delete Schedule
              </button>
            </div>
          </div>
        </div>
      )}

      {/* History Modal */}
      {showHistoryModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
          <div className="bg-zinc-900 border border-zinc-800 rounded-xl w-full max-w-3xl max-h-[80vh] flex flex-col shadow-2xl animate-fade-in-up">
            <div className="p-6 border-b border-zinc-800 flex justify-between items-center shrink-0">
              <div>
                <h2 className="text-xl font-bold text-white">Run History</h2>
                <p className="text-sm text-zinc-500 mt-1 font-medium">{currentSchedule?.name}</p>
              </div>
              <button 
                onClick={() => setShowHistoryModal(false)}
                className="text-zinc-500 hover:text-white transition-colors"
              >
                <X className="w-6 h-6" />
              </button>
            </div>
            
            <div className="flex-1 overflow-y-auto p-6 custom-scrollbar">
              {loadingRuns ? (
                <div className="flex justify-center py-8">
                  <RefreshCw className="w-8 h-8 text-blue-500 animate-spin" />
                </div>
              ) : scheduleRuns.length === 0 ? (
                <div className="text-center py-12 text-zinc-500">
                  <History className="w-12 h-12 mx-auto mb-3 opacity-20" />
                  No execution history found for this schedule.
                </div>
              ) : (
                <div className="space-y-4">
                  {scheduleRuns.map((run) => (
                    <div key={run.id} className="bg-zinc-950/50 border border-zinc-800 rounded-xl p-4 hover:border-zinc-700 transition-colors">
                      <div className="flex justify-between items-start mb-3">
                        <div className="flex items-center gap-2">
                          <span className={`w-2.5 h-2.5 rounded-full ${
                            run.status === 'success' ? 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]' : 
                            run.status === 'failed' ? 'bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.5)]' : 'bg-blue-500'
                          }`} />
                          <span className="font-medium text-zinc-200 capitalize">{run.status}</span>
                        </div>
                        <span className="text-xs text-zinc-500 font-mono">{formatDate(run.created_at)}</span>
                      </div>
                      
                      <div className="grid grid-cols-2 gap-4 text-sm mt-2">
                        <div className="bg-zinc-900 rounded-lg p-3">
                          <span className="text-zinc-500 text-xs uppercase tracking-wide block mb-1">Duration</span>
                          <span className="text-zinc-200 font-mono">{run.duration ? `${run.duration}s` : '-'}</span>
                        </div>
                        <div className="bg-zinc-900 rounded-lg p-3">
                          <span className="text-zinc-500 text-xs uppercase tracking-wide block mb-1">Items Scanned</span>
                          <span className="text-zinc-200 font-mono">{run.items_scanned || 0}</span>
                        </div>
                      </div>
                      
                      {run.error_message && (
                        <div className="mt-3 p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-red-300 text-xs font-mono break-all">
                          {run.error_message}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default Schedules
