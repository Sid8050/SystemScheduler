import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Usb, Plus, Trash2, Shield, Info, HardDrive, Monitor, RefreshCw, Smartphone, MousePointer2, Keyboard, ExternalLink } from 'lucide-react'
import { api } from '../api/client'

function USBControl() {
  const [newDevice, setNewDevice] = useState({
    vendor_id: '',
    product_id: '',
    serial_number: '',
    description: '',
  })
  const [showForm, setShowForm] = useState(false)
  
  const queryClient = useQueryClient()
  
  const { data: whitelistData, isLoading: isLoadingWhitelist } = useQuery({
    queryKey: ['usb-whitelist'],
    queryFn: () => api.getUSBWhitelist().then(r => r.data),
  })

  const { data: connectedData, isLoading: isLoadingConnected } = useQuery({
    queryKey: ['usb-connected'],
    queryFn: () => api.getConnectedUSB().then(r => r.data),
    refetchInterval: 10000
  })

  const { data: policiesData } = useQuery({
    queryKey: ['policies'],
    queryFn: () => api.getPolicies().then(r => r.data),
  })
  
  const addMutation = useMutation({
    mutationFn: (device) => api.addUSBWhitelist(device),
    onSuccess: () => {
      queryClient.invalidateQueries(['usb-whitelist'])
      setShowForm(false)
      setNewDevice({ vendor_id: '', product_id: '', serial_number: '', description: '' })
    },
  })
  
  const removeMutation = useMutation({
    mutationFn: (id) => api.removeUSBWhitelist(id),
    onSuccess: () => {
      queryClient.invalidateQueries(['usb-whitelist'])
    },
  })

  const updatePolicyMutation = useMutation({
    mutationFn: ({ id, config }) => api.updatePolicy(id, { name: 'Default', config }),
    onSuccess: () => {
      queryClient.invalidateQueries(['policies'])
    },
  })
  
  const whitelist = whitelistData?.devices || []
  const connected = connectedData?.devices || []
  const defaultPolicy = policiesData?.policies?.find(p => p.is_default)
  const usbMode = defaultPolicy?.config?.usb?.mode || 'monitor'
  
  const handleToggleUSB = () => {
    const nextMode = usbMode === 'block' ? 'monitor' : 'block'
    const newConfig = { ...defaultPolicy.config }
    if (!newConfig.usb) newConfig.usb = {}
    newConfig.usb.mode = nextMode
    updatePolicyMutation.mutate({ id: defaultPolicy.id, config: newConfig })
  }

  const getDeviceIcon = (type) => {
    switch (type) {
      case 'mass_storage': return <HardDrive className="w-4 h-4" />
      case 'mtp':
      case 'ptp': return <Smartphone className="w-4 h-4" />
      case 'hid': return <MousePointer2 className="w-4 h-4" />
      default: return <Usb className="w-4 h-4" />
    }
  }
  
  const handleSubmit = (e) => {
    e.preventDefault()
    if (newDevice.vendor_id && newDevice.product_id) {
      addMutation.mutate(newDevice)
    }
  }
  
  return (
    <div className="space-y-8 animate-fade-in">
      {/* Header */}
      <div className="flex justify-between items-center border-b border-zinc-800 pb-6">
        <div>
          <h1 className="text-3xl font-bold text-white tracking-tight">USB Device Control</h1>
          <p className="text-zinc-500 mt-2 font-medium">Manage authorized USB storage devices</p>
        </div>
        
        <div className="flex gap-4">
          <div className="flex items-center gap-3 bg-zinc-900 border border-zinc-800 px-4 py-2 rounded-lg">
             <span className="text-sm font-medium text-zinc-400">USB Storage Blocking</span>
             <label className="relative inline-flex items-center cursor-pointer">
              <input 
                type="checkbox" 
                className="sr-only peer" 
                checked={usbMode === 'block'}
                onChange={handleToggleUSB}
                disabled={!defaultPolicy}
              />
              <div className="w-11 h-6 bg-zinc-700 rounded-full peer peer-checked:bg-blue-600 peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all"></div>
            </label>
          </div>
          <button
            onClick={() => setShowForm(true)}
            className="flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-500 transition-all shadow-[0_0_20px_rgba(37,99,235,0.3)] hover:shadow-[0_0_30px_rgba(37,99,235,0.5)] border border-blue-500/50"
          >
            <Plus className="w-4 h-4 mr-2" />
            Add Device
          </button>
        </div>
      </div>
      
      <div className="grid grid-cols-1 gap-8">
        <div className="bg-zinc-900/50 backdrop-blur-sm rounded-xl border border-zinc-800 overflow-hidden">
          <div className="px-6 py-4 border-b border-zinc-800 flex items-center justify-between bg-zinc-900/50">
            <div className="flex items-center gap-2">
              <Monitor className="w-4 h-4 text-blue-400" />
              <h2 className="text-sm font-semibold text-zinc-100 uppercase tracking-wider">Live Connected Devices</h2>
            </div>
            {isLoadingConnected && <RefreshCw className="w-4 h-4 text-zinc-500 animate-spin" />}
          </div>
          
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-zinc-800">
              <thead>
                <tr className="bg-zinc-950/50">
                  <th className="px-6 py-4 text-left text-xs font-semibold text-zinc-500 uppercase tracking-wider">Endpoint</th>
                  <th className="px-6 py-4 text-left text-xs font-semibold text-zinc-500 uppercase tracking-wider">Device</th>
                  <th className="px-6 py-4 text-left text-xs font-semibold text-zinc-500 uppercase tracking-wider">Type</th>
                  <th className="px-6 py-4 text-left text-xs font-semibold text-zinc-500 uppercase tracking-wider">ID / Serial</th>
                  <th className="px-6 py-4 text-right text-xs font-semibold text-zinc-500 uppercase tracking-wider">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-800">
                {connected.length === 0 ? (
                  <tr>
                    <td colSpan="5" className="px-6 py-12 text-center text-zinc-500 text-sm">
                      No connected devices detected
                    </td>
                  </tr>
                ) : (
                  connected.map((device, idx) => (
                    <tr key={idx} className="hover:bg-zinc-800/30 transition-colors">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className="text-sm font-medium text-zinc-300">{device.hostname}</span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center">
                          <div className="p-2 bg-zinc-800 rounded-lg mr-3">
                            {getDeviceIcon(device.device_type)}
                          </div>
                          <span className="text-sm font-medium text-white">{device.description}</span>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
                          device.device_type === 'mass_storage' ? 'bg-red-500/10 text-red-400 border border-red-500/20' : 'bg-zinc-800 text-zinc-400'
                        }`}>
                          {device.device_type}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <p className="text-xs text-zinc-400 font-mono">{device.vendor_id}:{device.product_id}</p>
                        <p className="text-[10px] text-zinc-500 font-mono">{device.serial_number || '-'}</p>
                      </td>
                      <td className="px-6 py-4 text-right">
                         <button 
                            onClick={() => addMutation.mutate({ 
                              vendor_id: device.vendor_id, 
                              product_id: device.product_id, 
                              serial_number: device.serial_number,
                              description: device.description 
                            })}
                            className="text-blue-400 hover:text-blue-300 text-xs font-semibold transition-colors"
                          >
                            Whitelist
                         </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
      
      <div className="bg-blue-500/5 border border-blue-500/20 rounded-xl p-6 relative overflow-hidden group">
         <div className="absolute inset-0 bg-gradient-to-br from-blue-500/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
        <div className="flex items-start relative z-10">
          <div className="p-3 bg-blue-500/10 rounded-lg mr-4 border border-blue-500/20">
             <Shield className="w-6 h-6 text-blue-400" />
          </div>
          <div>
            <h3 className="text-base font-semibold text-blue-400 mb-1">Strict Enforcement Policy Active</h3>
            <p className="text-sm text-blue-200/70 leading-relaxed">
              By default, all USB storage devices are blocked to prevent data exfiltration. 
              Only devices explicitly listed below will be allowed to mount. 
              Find the VID/PID in Device Manager (Windows) or System Information (macOS/Linux).
            </p>
          </div>
        </div>
      </div>
      
      {showForm && (
        <div className="bg-zinc-900/50 backdrop-blur-sm rounded-xl border border-zinc-800 p-6 animate-fade-in-up">
          <h2 className="text-lg font-semibold text-white mb-6 flex items-center gap-2">
            <Plus className="w-5 h-5 text-blue-500" />
            Add USB Device to Whitelist
          </h2>
          
          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="block text-sm font-medium text-zinc-400 mb-2">
                  Vendor ID (VID) <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={newDevice.vendor_id}
                  onChange={(e) => setNewDevice({ ...newDevice, vendor_id: e.target.value })}
                  placeholder="e.g., 0781"
                  className="w-full px-4 py-3 bg-zinc-950 border border-zinc-800 rounded-lg focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50 text-zinc-100 placeholder-zinc-700 outline-none transition-all font-mono"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-zinc-400 mb-2">
                  Product ID (PID) <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={newDevice.product_id}
                  onChange={(e) => setNewDevice({ ...newDevice, product_id: e.target.value })}
                  placeholder="e.g., 5567"
                  className="w-full px-4 py-3 bg-zinc-950 border border-zinc-800 rounded-lg focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50 text-zinc-100 placeholder-zinc-700 outline-none transition-all font-mono"
                  required
                />
              </div>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-zinc-400 mb-2">
                Serial Number (optional)
              </label>
              <input
                type="text"
                value={newDevice.serial_number}
                onChange={(e) => setNewDevice({ ...newDevice, serial_number: e.target.value })}
                placeholder="Leave empty to allow all devices with this VID/PID"
                className="w-full px-4 py-3 bg-zinc-950 border border-zinc-800 rounded-lg focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50 text-zinc-100 placeholder-zinc-700 outline-none transition-all font-mono"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-zinc-400 mb-2">
                Description
              </label>
              <input
                type="text"
                value={newDevice.description}
                onChange={(e) => setNewDevice({ ...newDevice, description: e.target.value })}
                placeholder="e.g., Company-approved SanDisk Drive"
                className="w-full px-4 py-3 bg-zinc-950 border border-zinc-800 rounded-lg focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50 text-zinc-100 placeholder-zinc-700 outline-none transition-all"
              />
            </div>
            
            <div className="flex gap-4 pt-2">
              <button
                type="submit"
                className="px-6 py-2.5 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-500 transition-colors shadow-lg shadow-blue-900/20"
              >
                Add to Whitelist
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
      
      <div className="bg-zinc-900/50 backdrop-blur-sm rounded-xl border border-zinc-800 overflow-hidden">
        <div className="px-6 py-4 border-b border-zinc-800 flex items-center gap-2">
          <HardDrive className="w-4 h-4 text-zinc-400" />
          <h2 className="text-sm font-semibold text-zinc-300 uppercase tracking-wider">Whitelisted Devices</h2>
        </div>
        
        {isLoading ? (
          <div className="flex items-center justify-center py-20">
            <div className="w-12 h-12 border-4 border-blue-500/30 border-t-blue-500 rounded-full animate-spin"></div>
          </div>
        ) : devices.length === 0 ? (
          <div className="text-center py-20">
            <div className="w-16 h-16 bg-zinc-800/50 rounded-full flex items-center justify-center mx-auto mb-4">
              <Usb className="w-8 h-8 text-zinc-600" />
            </div>
            <h3 className="text-lg font-medium text-white">No devices whitelisted</h3>
            <p className="text-zinc-500 mt-2">Add USB devices to allow them on endpoints.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-zinc-800">
              <thead className="bg-zinc-900/80">
                <tr>
                  <th className="px-6 py-4 text-left text-xs font-medium text-zinc-500 uppercase tracking-wider">Device</th>
                  <th className="px-6 py-4 text-left text-xs font-medium text-zinc-500 uppercase tracking-wider">VID</th>
                  <th className="px-6 py-4 text-left text-xs font-medium text-zinc-500 uppercase tracking-wider">PID</th>
                  <th className="px-6 py-4 text-left text-xs font-medium text-zinc-500 uppercase tracking-wider">Serial</th>
                  <th className="px-6 py-4 text-right text-xs font-medium text-zinc-500 uppercase tracking-wider">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-800">
                {devices.map((device) => (
                  <tr key={device.id} className="hover:bg-zinc-800/30 transition-colors group">
                    <td className="px-6 py-4">
                      <div className="flex items-center">
                        <div className="p-2 bg-zinc-800 rounded-lg mr-3 group-hover:bg-blue-500/10 group-hover:text-blue-400 transition-colors">
                          <Usb className="w-4 h-4 text-zinc-400 group-hover:text-blue-400" />
                        </div>
                        <span className="text-sm font-medium text-zinc-200">
                          {device.description || 'USB Device'}
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-sm text-zinc-400 font-mono">{device.vendor_id}</td>
                    <td className="px-6 py-4 text-sm text-zinc-400 font-mono">{device.product_id}</td>
                    <td className="px-6 py-4 text-sm text-zinc-400 font-mono">{device.serial_number || '-'}</td>
                    <td className="px-6 py-4 text-right">
                      <button
                        onClick={() => removeMutation.mutate(device.id)}
                        className="text-zinc-500 hover:text-red-400 p-2 hover:bg-red-500/10 rounded-lg transition-all"
                        title="Remove device"
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

export default USBControl
