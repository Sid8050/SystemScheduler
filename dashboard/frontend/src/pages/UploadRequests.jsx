import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { 
  FileUp, 
  Check, 
  X, 
  Clock, 
  FileText, 
  HardDrive, 
  Hash, 
  Search,
  Filter,
  Shield,
  Eye,
  AlertCircle
} from 'lucide-react'
import { api } from '../api/client'

// Utility for formatting file size
function formatBytes(bytes, decimals = 2) {
  if (!+bytes) return '0 Bytes'
  const k = 1024
  const dm = decimals < 0 ? 0 : decimals
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(dm))} ${sizes[i]}`
}

function StatusBadge({ status }) {
  const styles = {
    pending: 'bg-yellow-500/10 text-yellow-500 border-yellow-500/20',
    approved: 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20',
    denied: 'bg-red-500/10 text-red-500 border-red-500/20',
  }

  const icons = {
    pending: Clock,
    approved: Check,
    denied: X,
  }

  const Icon = icons[status] || Clock

  return (
    <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium border ${styles[status] || styles.pending} transition-colors`}>
      <Icon className="w-3 h-3 mr-1.5" />
      <span className="capitalize">{status}</span>
    </span>
  )
}

function DetailModal({ request, onClose }) {
  if (!request) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div 
        className="w-full max-w-2xl bg-zinc-900 border border-zinc-800 rounded-xl shadow-2xl overflow-hidden animate-in zoom-in-95 duration-200"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-6 py-4 border-b border-zinc-800 bg-zinc-900/50">
          <h3 className="text-lg font-semibold text-white flex items-center gap-2">
            <FileText className="w-5 h-5 text-blue-500" />
            Request Details
          </h3>
          <button 
            onClick={onClose}
            className="p-1 text-zinc-400 hover:text-white hover:bg-zinc-800 rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        
        <div className="p-6 space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-1">
              <label className="text-xs font-medium text-zinc-500 uppercase tracking-wider">File Name</label>
              <p className="text-zinc-200 font-medium break-all">{request.file_name}</p>
            </div>
            <div className="space-y-1">
              <label className="text-xs font-medium text-zinc-500 uppercase tracking-wider">Size</label>
              <p className="text-zinc-200 font-mono">{formatBytes(request.file_size)}</p>
            </div>
            <div className="space-y-1 md:col-span-2">
              <label className="text-xs font-medium text-zinc-500 uppercase tracking-wider">File Path</label>
              <div className="flex items-center gap-2 text-zinc-300 bg-zinc-950/50 p-3 rounded-lg border border-zinc-800 font-mono text-sm break-all">
                <HardDrive className="w-4 h-4 text-zinc-500 shrink-0" />
                {request.file_path}
              </div>
            </div>
            <div className="space-y-1 md:col-span-2">
              <label className="text-xs font-medium text-zinc-500 uppercase tracking-wider">SHA256 Hash</label>
              <div className="flex items-center gap-2 text-zinc-400 bg-zinc-950/50 p-3 rounded-lg border border-zinc-800 font-mono text-xs break-all">
                <Hash className="w-3.5 h-3.5 text-zinc-600 shrink-0" />
                {request.file_hash}
              </div>
            </div>
            <div className="space-y-1 md:col-span-2">
              <label className="text-xs font-medium text-zinc-500 uppercase tracking-wider">Justification</label>
              <p className="text-zinc-300 italic border-l-2 border-blue-500/30 pl-3 py-1">
                "{request.justification}"
              </p>
            </div>
            <div className="space-y-1">
              <label className="text-xs font-medium text-zinc-500 uppercase tracking-wider">Endpoint</label>
              <p className="text-zinc-200">{request.hostname || 'Unknown Host'}</p>
            </div>
            <div className="space-y-1">
              <label className="text-xs font-medium text-zinc-500 uppercase tracking-wider">Requested At</label>
              <p className="text-zinc-200">{new Date(request.requested_at).toLocaleString()}</p>
            </div>
          </div>
        </div>

        <div className="px-6 py-4 bg-zinc-900/50 border-t border-zinc-800 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-zinc-300 bg-zinc-800 hover:bg-zinc-700 rounded-lg transition-colors border border-zinc-700"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  )
}

function UploadRequests() {
  const [filterStatus, setFilterStatus] = useState('all')
  const [selectedRequest, setSelectedRequest] = useState(null)
  const queryClient = useQueryClient()

  // Fetch requests
  const { data, isLoading } = useQuery({
    queryKey: ['upload-requests', filterStatus],
    queryFn: () => api.getUploadRequests({ status: filterStatus === 'all' ? undefined : filterStatus }),
    refetchInterval: 10000,
  })

  // Review mutation
  const reviewMutation = useMutation({
    mutationFn: ({ id, status }) => api.reviewUploadRequest(id, status),
    onSuccess: () => {
      queryClient.invalidateQueries(['upload-requests'])
    },
  })

  const requests = data?.data?.requests || [] // Safely access requests

  const handleReview = async (id, status, e) => {
    e.stopPropagation()
    try {
      await reviewMutation.mutateAsync({ id, status })
    } catch (error) {
      console.error('Failed to review request:', error)
    }
  }

  return (
    <div className="space-y-8 animate-fade-in pb-10">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 border-b border-zinc-800 pb-6">
        <div>
          <h1 className="text-3xl font-bold text-white tracking-tight flex items-center gap-3">
            <FileUp className="w-8 h-8 text-blue-500" />
            Upload Requests
          </h1>
          <p className="text-zinc-500 mt-2 font-medium max-w-2xl">
            Review and manage file upload requests from endpoints. Approved files will be allowed for transfer for a limited time.
          </p>
        </div>
        
        {/* Filter */}
        <div className="flex items-center bg-zinc-900 p-1 rounded-lg border border-zinc-800">
          {['all', 'pending', 'approved', 'denied'].map((status) => (
            <button
              key={status}
              onClick={() => setFilterStatus(status)}
              className={`
                px-4 py-1.5 text-sm font-medium rounded-md transition-all capitalize
                ${filterStatus === status 
                  ? 'bg-zinc-800 text-white shadow-sm' 
                  : 'text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800/50'
                }
              `}
            >
              {status}
            </button>
          ))}
        </div>
      </div>

      {/* Main Content */}
      <div className="bg-zinc-900/50 backdrop-blur-sm rounded-xl border border-zinc-800 overflow-hidden shadow-xl">
        {isLoading ? (
          <div className="flex flex-col items-center justify-center py-32 space-y-4">
            <div className="w-12 h-12 border-4 border-blue-500/30 border-t-blue-500 rounded-full animate-spin"></div>
            <p className="text-zinc-500 text-sm animate-pulse">Loading requests...</p>
          </div>
        ) : requests.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-32 text-center">
            <div className="w-20 h-20 bg-zinc-800/50 rounded-full flex items-center justify-center mb-6">
              <FileUp className="w-10 h-10 text-zinc-600" />
            </div>
            <h3 className="text-xl font-medium text-white">No requests found</h3>
            <p className="text-zinc-500 mt-2 max-w-sm">
              {filterStatus === 'all' 
                ? "There are no upload requests to show at the moment."
                : `There are no ${filterStatus} requests found.`}
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="border-b border-zinc-800 bg-zinc-900/50">
                  <th className="px-6 py-4 text-xs font-semibold text-zinc-500 uppercase tracking-wider">Endpoint</th>
                  <th className="px-6 py-4 text-xs font-semibold text-zinc-500 uppercase tracking-wider">File Details</th>
                  <th className="px-6 py-4 text-xs font-semibold text-zinc-500 uppercase tracking-wider">Destination</th>
                  <th className="px-6 py-4 text-xs font-semibold text-zinc-500 uppercase tracking-wider">Justification</th>
                  <th className="px-6 py-4 text-xs font-semibold text-zinc-500 uppercase tracking-wider">Status</th>
                  <th className="px-6 py-4 text-xs font-semibold text-zinc-500 uppercase tracking-wider">Time</th>
                  <th className="px-6 py-4 text-xs font-semibold text-zinc-500 uppercase tracking-wider text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-800/50">
                {requests.map((req) => (
                  <tr 
                    key={req.id} 
                    onClick={() => setSelectedRequest(req)}
                    className="group hover:bg-zinc-800/30 transition-colors cursor-pointer"
                  >
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center">
                        <div className="w-8 h-8 rounded-lg bg-zinc-800 flex items-center justify-center mr-3 border border-zinc-700">
                          <MonitorIcon hostname={req.hostname} />
                        </div>
                        <span className="text-sm font-medium text-zinc-200">{req.hostname || 'Unknown'}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex flex-col">
                        <span className="text-sm font-medium text-white mb-0.5 truncate max-w-[200px]" title={req.file_name}>
                          {req.file_name}
                        </span>
                        <span className="text-xs text-zinc-500 font-mono">
                          {formatBytes(req.file_size)}
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center text-sm text-zinc-400 font-mono truncate max-w-[150px]" title={req.file_path}>
                        {req.file_path}
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <p className="text-sm text-zinc-400 truncate max-w-[200px]" title={req.justification}>
                        {req.justification}
                      </p>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <StatusBadge status={req.status} />
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-zinc-500">
                      {new Date(req.requested_at).toLocaleDateString()}
                      <span className="block text-xs text-zinc-600">{new Date(req.requested_at).toLocaleTimeString()}</span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right">
                      <div className="flex items-center justify-end gap-2" onClick={(e) => e.stopPropagation()}>
                        {req.status === 'pending' ? (
                          <>
                            <button
                              onClick={(e) => handleReview(req.id, 'approved', e)}
                              disabled={reviewMutation.isPending}
                              className="p-2 text-emerald-500 hover:bg-emerald-500/10 border border-transparent hover:border-emerald-500/20 rounded-lg transition-all"
                              title="Approve"
                            >
                              <Check className="w-4 h-4" />
                            </button>
                            <button
                              onClick={(e) => handleReview(req.id, 'denied', e)}
                              disabled={reviewMutation.isPending}
                              className="p-2 text-red-500 hover:bg-red-500/10 border border-transparent hover:border-red-500/20 rounded-lg transition-all"
                              title="Deny"
                            >
                              <X className="w-4 h-4" />
                            </button>
                          </>
                        ) : (
                          <button
                            onClick={() => setSelectedRequest(req)}
                            className="p-2 text-zinc-500 hover:text-blue-400 hover:bg-blue-500/10 rounded-lg transition-all"
                            title="View Details"
                          >
                            <Eye className="w-4 h-4" />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Details Modal */}
      {selectedRequest && (
        <DetailModal 
          request={selectedRequest} 
          onClose={() => setSelectedRequest(null)} 
        />
      )}
    </div>
  )
}

function MonitorIcon({ hostname }) {
  // Generate a deterministic color based on hostname to make it look nicer
  return <HardDrive className="w-4 h-4 text-zinc-400" />
}

export default UploadRequests
