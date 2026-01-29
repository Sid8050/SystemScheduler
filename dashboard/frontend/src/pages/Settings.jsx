import React, { useState, useEffect } from 'react'
import { useAuth } from '../context/AuthContext'
import client from '../api/client'
import { 
  User, 
  Mail, 
  Lock, 
  Shield, 
  Trash2, 
  Edit, 
  Plus, 
  Key, 
  Users,
  Check,
  X,
  AlertCircle,
  Save,
  Server,
  Activity
} from 'lucide-react'

const Settings = () => {
  const { user } = useAuth()
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState(null)
  
  // Modals
  const [showPasswordModal, setShowPasswordModal] = useState(false)
  const [showUserModal, setShowUserModal] = useState(false)
  const [editingUser, setEditingUser] = useState(null)

  // Forms
  const [passwordForm, setPasswordForm] = useState({
    current_password: '',
    new_password: '',
    confirm_password: ''
  })

  const [userForm, setUserForm] = useState({
    username: '',
    email: '',
    password: '',
    full_name: '',
    role: 'viewer',
    is_active: true
  })

  useEffect(() => {
    if (user?.role === 'admin') {
      fetchUsers()
    }
  }, [user])

  const fetchUsers = async () => {
    try {
      setLoading(true)
      const res = await client.get('/auth/users')
      setUsers(res.data)
    } catch (err) {
      console.error('Failed to fetch users:', err)
      showMessage('error', 'Failed to load users')
    } finally {
      setLoading(false)
    }
  }

  const showMessage = (type, text) => {
    setMessage({ type, text })
    setTimeout(() => setMessage(null), 3000)
  }

  const handlePasswordChange = async (e) => {
    e.preventDefault()
    if (passwordForm.new_password !== passwordForm.confirm_password) {
      showMessage('error', 'New passwords do not match')
      return
    }

    try {
      await client.post('/auth/change-password', {
        current_password: passwordForm.current_password,
        new_password: passwordForm.new_password
      })
      showMessage('success', 'Password changed successfully')
      setShowPasswordModal(false)
      setPasswordForm({ current_password: '', new_password: '', confirm_password: '' })
    } catch (err) {
      showMessage('error', err.response?.data?.detail || 'Failed to change password')
    }
  }

  const handleUserSubmit = async (e) => {
    e.preventDefault()
    try {
      if (editingUser) {
        // Update user
        await client.put(`/auth/users/${editingUser.id}`, {
          email: userForm.email,
          full_name: userForm.full_name,
          role: userForm.role,
          is_active: userForm.is_active
        })
        showMessage('success', 'User updated successfully')
      } else {
        // Create user
        await client.post('/auth/users', userForm)
        showMessage('success', 'User created successfully')
      }
      setShowUserModal(false)
      fetchUsers()
      resetUserForm()
    } catch (err) {
      showMessage('error', err.response?.data?.detail || 'Operation failed')
    }
  }

  const handleDeleteUser = async (userId) => {
    if (!window.confirm('Are you sure you want to delete this user?')) return

    try {
      await client.delete(`/auth/users/${userId}`)
      showMessage('success', 'User deleted successfully')
      fetchUsers()
    } catch (err) {
      showMessage('error', err.response?.data?.detail || 'Failed to delete user')
    }
  }

  const openEditUser = (u) => {
    setEditingUser(u)
    setUserForm({
      username: u.username,
      email: u.email,
      password: '', // Password not editable here usually
      full_name: u.full_name,
      role: u.role,
      is_active: u.is_active
    })
    setShowUserModal(true)
  }

  const openAddUser = () => {
    setEditingUser(null)
    resetUserForm()
    setShowUserModal(true)
  }

  const resetUserForm = () => {
    setUserForm({
      username: '',
      email: '',
      password: '',
      full_name: '',
      role: 'viewer',
      is_active: true
    })
  }

  // Common UI Components
  const SectionHeader = ({ icon: Icon, title }) => (
    <div className="flex items-center gap-3 mb-6 border-b border-zinc-800 pb-4">
      <div className="p-2 bg-blue-500/10 rounded-lg border border-blue-500/20">
        <Icon className="text-blue-400 w-5 h-5" />
      </div>
      <h2 className="text-xl font-bold text-white tracking-tight">{title}</h2>
    </div>
  )

  const Modal = ({ title, onClose, children }) => (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4 animate-fade-in">
      <div className="bg-zinc-900 rounded-xl shadow-2xl w-full max-w-md border border-zinc-800 overflow-hidden animate-fade-in-up">
        <div className="flex justify-between items-center p-6 border-b border-zinc-800 bg-zinc-900/50">
          <h3 className="text-lg font-bold text-white">{title}</h3>
          <button onClick={onClose} className="text-zinc-500 hover:text-white transition-colors">
            <X size={20} />
          </button>
        </div>
        <div className="p-6">
          {children}
        </div>
      </div>
    </div>
  )

  if (!user) return null

  return (
    <div className="space-y-8 animate-fade-in">
      <div className="flex justify-between items-end border-b border-zinc-800 pb-6">
        <div>
          <h1 className="text-3xl font-bold text-white tracking-tight">System Settings</h1>
          <p className="text-zinc-500 mt-2 font-medium">Manage your account and system configuration</p>
        </div>
      </div>

      {message && (
        <div className={`p-4 rounded-xl flex items-center gap-3 animate-fade-in ${
          message.type === 'error' 
            ? 'bg-red-500/10 text-red-400 border border-red-500/20 shadow-[0_0_20px_rgba(239,68,68,0.1)]' 
            : 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 shadow-[0_0_20px_rgba(16,185,129,0.1)]'
        }`}>
          {message.type === 'error' ? <AlertCircle size={20} /> : <Check size={20} />}
          <span className="font-medium">{message.text}</span>
        </div>
      )}

      {/* Profile Section */}
      <div className="bg-zinc-900/50 backdrop-blur-sm rounded-xl p-6 border border-zinc-800 hover:border-zinc-700 transition-colors">
        <SectionHeader icon={User} title="My Profile" />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="space-y-6">
             <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
               <div className="space-y-2">
                 <label className="text-xs text-zinc-500 uppercase font-bold tracking-wider ml-1">Username</label>
                 <div className="bg-zinc-950 p-3 rounded-lg border border-zinc-800 text-zinc-200 font-mono">
                   {user.username}
                 </div>
               </div>
               
               <div className="space-y-2">
                 <label className="text-xs text-zinc-500 uppercase font-bold tracking-wider ml-1">Role</label>
                 <div className="h-[46px] flex items-center px-1">
                   <span className={`px-3 py-1.5 rounded-lg text-xs font-bold uppercase tracking-wide border ${
                     user.role === 'admin' ? 'bg-purple-500/10 text-purple-400 border-purple-500/20' : 
                     user.role === 'editor' ? 'bg-blue-500/10 text-blue-400 border-blue-500/20' : 'bg-zinc-800 text-zinc-400 border-zinc-700'
                   }`}>
                     {user.role}
                   </span>
                 </div>
               </div>

               <div className="space-y-2 sm:col-span-2">
                 <label className="text-xs text-zinc-500 uppercase font-bold tracking-wider ml-1">Email</label>
                 <div className="bg-zinc-950 p-3 rounded-lg border border-zinc-800 text-zinc-200 flex items-center gap-2">
                   <Mail className="w-4 h-4 text-zinc-500" />
                   {user.email}
                 </div>
               </div>
               
               <div className="space-y-2 sm:col-span-2">
                 <label className="text-xs text-zinc-500 uppercase font-bold tracking-wider ml-1">Full Name</label>
                 <div className="bg-zinc-950 p-3 rounded-lg border border-zinc-800 text-zinc-200">
                   {user.full_name}
                 </div>
               </div>
             </div>
             
             <div className="pt-2">
               <button 
                 onClick={() => setShowPasswordModal(true)}
                 className="flex items-center gap-2 px-4 py-2 bg-zinc-800 hover:bg-zinc-700 text-zinc-200 rounded-lg transition-all border border-zinc-700 hover:border-zinc-600 shadow-lg shadow-black/20"
               >
                 <Key size={16} />
                 <span>Change Password</span>
               </button>
             </div>
          </div>
          
          <div className="hidden md:flex items-center justify-center p-8 bg-zinc-950/50 rounded-xl border border-zinc-800/50">
             <div className="text-center">
                <div className="w-24 h-24 bg-zinc-900 rounded-full flex items-center justify-center mx-auto mb-4 border-2 border-zinc-800 shadow-xl">
                   <User className="w-12 h-12 text-zinc-600" />
                </div>
                <h3 className="text-lg font-bold text-white">{user.full_name}</h3>
                <p className="text-zinc-500 text-sm">Active Session</p>
             </div>
          </div>
        </div>
      </div>

      {/* User Management Section (Admin Only) */}
      {user.role === 'admin' && (
        <div className="bg-zinc-900/50 backdrop-blur-sm rounded-xl p-6 border border-zinc-800 hover:border-zinc-700 transition-colors">
          <div className="flex justify-between items-center mb-6 border-b border-zinc-800 pb-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-purple-500/10 rounded-lg border border-purple-500/20">
                <Users className="text-purple-400 w-5 h-5" />
              </div>
              <h2 className="text-xl font-bold text-white tracking-tight">User Management</h2>
            </div>
            <button 
              onClick={openAddUser}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm font-medium transition-all shadow-[0_0_15px_rgba(37,99,235,0.3)] hover:shadow-[0_0_25px_rgba(37,99,235,0.4)] border border-blue-500/50"
            >
              <Plus size={16} />
              Add User
            </button>
          </div>
          
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-zinc-800">
                  <th className="p-4 text-xs font-medium text-zinc-500 uppercase tracking-wider">User</th>
                  <th className="p-4 text-xs font-medium text-zinc-500 uppercase tracking-wider">Role</th>
                  <th className="p-4 text-xs font-medium text-zinc-500 uppercase tracking-wider">Status</th>
                  <th className="p-4 text-xs font-medium text-zinc-500 uppercase tracking-wider">Last Login</th>
                  <th className="p-4 text-xs font-medium text-zinc-500 uppercase tracking-wider text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-800">
                {users.map(u => (
                  <tr key={u.id} className="group hover:bg-zinc-800/30 transition-colors">
                    <td className="p-4">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full bg-zinc-800 flex items-center justify-center text-zinc-400 text-xs font-bold">
                          {u.username.substring(0, 2).toUpperCase()}
                        </div>
                        <div>
                          <div className="font-medium text-zinc-200">{u.username}</div>
                          <div className="text-zinc-500 text-xs">{u.email}</div>
                        </div>
                      </div>
                    </td>
                    <td className="p-4">
                      <span className={`px-2 py-1 rounded text-[10px] font-bold uppercase tracking-wide border ${
                        u.role === 'admin' ? 'bg-purple-500/10 text-purple-400 border-purple-500/20' : 
                        u.role === 'editor' ? 'bg-blue-500/10 text-blue-400 border-blue-500/20' : 
                        'bg-zinc-800 text-zinc-400 border-zinc-700'
                      }`}>
                        {u.role}
                      </span>
                    </td>
                    <td className="p-4">
                      <span className={`flex items-center gap-1.5 text-xs font-medium ${u.is_active ? 'text-emerald-400' : 'text-red-400'}`}>
                        <span className={`w-1.5 h-1.5 rounded-full ${u.is_active ? 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]' : 'bg-red-500'}`}></span>
                        {u.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                    <td className="p-4 font-mono text-xs text-zinc-500">
                      {u.last_login ? new Date(u.last_login).toLocaleDateString() : 'Never'}
                    </td>
                    <td className="p-4 text-right">
                      <div className="flex justify-end gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                        <button 
                          onClick={() => openEditUser(u)}
                          className="p-2 text-zinc-400 hover:text-blue-400 hover:bg-blue-500/10 rounded-lg transition-colors"
                          title="Edit User"
                        >
                          <Edit size={16} />
                        </button>
                        {u.id !== user.id && (
                          <button 
                            onClick={() => handleDeleteUser(u.id)}
                            className="p-2 text-zinc-400 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-colors"
                            title="Delete User"
                          >
                            <Trash2 size={16} />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
                {users.length === 0 && !loading && (
                  <tr>
                    <td colSpan="5" className="p-12 text-center text-zinc-500">
                      <Users className="w-12 h-12 mx-auto mb-3 opacity-20" />
                      No users found
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* General Settings Section */}
      <div className="bg-zinc-900/50 backdrop-blur-sm rounded-xl p-6 border border-zinc-800 hover:border-zinc-700 transition-colors">
        <SectionHeader icon={Shield} title="System Information" />
        <div className="space-y-6">
          <div>
            <label className="block text-sm font-medium text-zinc-400 mb-2">API Endpoint Status</label>
            <div className="flex items-center gap-3 bg-zinc-950/50 border border-zinc-800 rounded-lg p-4">
              <div className="p-2 bg-emerald-500/10 rounded-lg border border-emerald-500/20">
                 <Activity size={18} className="text-emerald-500" />
              </div>
              <div className="flex-1">
                <div className="text-sm font-medium text-zinc-200">System Operational</div>
                <code className="text-zinc-500 text-xs mt-0.5 block">
                  {import.meta.env.VITE_API_URL || 'http://localhost:8000'}
                </code>
              </div>
              <div className="flex items-center gap-2">
                 <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                 <span className="text-xs text-emerald-500 font-medium">Online</span>
              </div>
            </div>
          </div>

          <div className="border-t border-zinc-800 pt-6">
            <h3 className="text-zinc-200 font-bold mb-2">About Platform</h3>
            <p className="text-zinc-400 text-sm mb-4 leading-relaxed max-w-2xl">
              Cybersecurity Command Center is an enterprise-grade endpoint protection and monitoring dashboard.
              Designed for real-time threat analysis, policy enforcement, and system auditing.
            </p>
            <div className="flex items-center gap-4 text-xs text-zinc-500 font-mono bg-zinc-950 inline-flex px-3 py-1.5 rounded-full border border-zinc-800">
              <span className="flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-blue-500"></span>
                v1.2.0-stable
              </span>
              <span className="text-zinc-700">|</span>
              <span>Build: 2024.01.29</span>
            </div>
          </div>
        </div>
      </div>

      {/* Change Password Modal */}
      {showPasswordModal && (
        <Modal title="Change Password" onClose={() => setShowPasswordModal(false)}>
          <form onSubmit={handlePasswordChange} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-zinc-400 mb-1.5">Current Password</label>
              <input
                type="password"
                required
                className="w-full bg-zinc-950 border border-zinc-800 rounded-lg p-2.5 text-zinc-100 focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50 outline-none transition-all placeholder-zinc-700"
                value={passwordForm.current_password}
                onChange={e => setPasswordForm({...passwordForm, current_password: e.target.value})}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-zinc-400 mb-1.5">New Password</label>
              <input
                type="password"
                required
                className="w-full bg-zinc-950 border border-zinc-800 rounded-lg p-2.5 text-zinc-100 focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50 outline-none transition-all placeholder-zinc-700"
                value={passwordForm.new_password}
                onChange={e => setPasswordForm({...passwordForm, new_password: e.target.value})}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-zinc-400 mb-1.5">Confirm New Password</label>
              <input
                type="password"
                required
                className="w-full bg-zinc-950 border border-zinc-800 rounded-lg p-2.5 text-zinc-100 focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50 outline-none transition-all placeholder-zinc-700"
                value={passwordForm.confirm_password}
                onChange={e => setPasswordForm({...passwordForm, confirm_password: e.target.value})}
              />
            </div>
            <div className="flex justify-end gap-3 mt-6 pt-2">
              <button 
                type="button" 
                onClick={() => setShowPasswordModal(false)}
                className="px-4 py-2 text-zinc-400 hover:text-white font-medium transition-colors"
              >
                Cancel
              </button>
              <button 
                type="submit" 
                className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg transition-all shadow-lg shadow-blue-900/20 flex items-center gap-2 font-medium"
              >
                <Save size={16} />
                Update Password
              </button>
            </div>
          </form>
        </Modal>
      )}

      {/* User Edit/Add Modal */}
      {showUserModal && (
        <Modal title={editingUser ? 'Edit User' : 'Add New User'} onClose={() => setShowUserModal(false)}>
          <form onSubmit={handleUserSubmit} className="space-y-5">
            {!editingUser && (
              <div>
                <label className="block text-sm font-medium text-zinc-400 mb-1.5">Username</label>
                <input
                  type="text"
                  required
                  className="w-full bg-zinc-950 border border-zinc-800 rounded-lg p-2.5 text-zinc-100 focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50 outline-none transition-all placeholder-zinc-700"
                  value={userForm.username}
                  onChange={e => setUserForm({...userForm, username: e.target.value})}
                />
              </div>
            )}
            
            <div className="grid grid-cols-2 gap-5">
              <div className="col-span-2">
                <label className="block text-sm font-medium text-zinc-400 mb-1.5">Full Name</label>
                <input
                  type="text"
                  required
                  className="w-full bg-zinc-950 border border-zinc-800 rounded-lg p-2.5 text-zinc-100 focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50 outline-none transition-all placeholder-zinc-700"
                  value={userForm.full_name}
                  onChange={e => setUserForm({...userForm, full_name: e.target.value})}
                />
              </div>
              <div className="col-span-2">
                <label className="block text-sm font-medium text-zinc-400 mb-1.5">Email</label>
                <input
                  type="email"
                  required
                  className="w-full bg-zinc-950 border border-zinc-800 rounded-lg p-2.5 text-zinc-100 focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50 outline-none transition-all placeholder-zinc-700"
                  value={userForm.email}
                  onChange={e => setUserForm({...userForm, email: e.target.value})}
                />
              </div>
            </div>

            {!editingUser && (
              <div>
                <label className="block text-sm font-medium text-zinc-400 mb-1.5">Password</label>
                <input
                  type="password"
                  required
                  className="w-full bg-zinc-950 border border-zinc-800 rounded-lg p-2.5 text-zinc-100 focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50 outline-none transition-all placeholder-zinc-700"
                  value={userForm.password}
                  onChange={e => setUserForm({...userForm, password: e.target.value})}
                />
              </div>
            )}

            <div className="grid grid-cols-2 gap-5">
              <div>
                <label className="block text-sm font-medium text-zinc-400 mb-1.5">Role</label>
                <div className="relative">
                  <select
                    className="w-full bg-zinc-950 border border-zinc-800 rounded-lg p-2.5 text-zinc-100 focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50 outline-none transition-all appearance-none"
                    value={userForm.role}
                    onChange={e => setUserForm({...userForm, role: e.target.value})}
                  >
                    <option value="viewer">Viewer</option>
                    <option value="editor">Editor</option>
                    <option value="admin">Admin</option>
                  </select>
                  <div className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none text-zinc-500">
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7" /></svg>
                  </div>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-zinc-400 mb-1.5">Status</label>
                <div className="relative">
                  <select
                    className="w-full bg-zinc-950 border border-zinc-800 rounded-lg p-2.5 text-zinc-100 focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50 outline-none transition-all appearance-none"
                    value={userForm.is_active}
                    onChange={e => setUserForm({...userForm, is_active: e.target.value === 'true'})}
                  >
                    <option value="true">Active</option>
                    <option value="false">Inactive</option>
                  </select>
                  <div className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none text-zinc-500">
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7" /></svg>
                  </div>
                </div>
              </div>
            </div>

            <div className="flex justify-end gap-3 mt-6 pt-2">
              <button 
                type="button" 
                onClick={() => setShowUserModal(false)}
                className="px-4 py-2 text-zinc-400 hover:text-white font-medium transition-colors"
              >
                Cancel
              </button>
              <button 
                type="submit" 
                className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg transition-all shadow-lg shadow-blue-900/20 flex items-center gap-2 font-medium"
              >
                <Save size={16} />
                {editingUser ? 'Save Changes' : 'Create User'}
              </button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  )
}

export default Settings
