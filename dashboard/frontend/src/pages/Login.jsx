import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import client from '../api/client'
import { Shield, Lock, User, Mail, Eye, EyeOff } from 'lucide-react'

const Login = () => {
  const { setupRequired, login } = useAuth()
  const navigate = useNavigate()
  
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  
  // Login State
  const [loginData, setLoginData] = useState({
    username: '',
    password: ''
  })
  
  // Setup State
  const [setupData, setSetupData] = useState({
    username: '',
    email: '',
    full_name: '',
    password: '',
    confirmPassword: ''
  })
  
  const handleLoginChange = (e) => {
    setLoginData({ ...loginData, [e.target.name]: e.target.value })
    setError('')
  }
  
  const handleSetupChange = (e) => {
    setSetupData({ ...setupData, [e.target.name]: e.target.value })
    setError('')
  }
  
  const handleLogin = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    
    try {
      const formData = new URLSearchParams()
      formData.append('username', loginData.username)
      formData.append('password', loginData.password)
      
      const response = await client.post('/auth/login', formData, {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded'
        }
      })
      
      const { access_token, user } = response.data
      login(access_token, user)
      navigate('/')
    } catch (err) {
      console.error('Login error:', err)
      setError(err.response?.data?.detail || 'Invalid username or password')
    } finally {
      setLoading(false)
    }
  }
  
  const handleSetup = async (e) => {
    e.preventDefault()
    
    if (setupData.password !== setupData.confirmPassword) {
      setError('Passwords do not match')
      return
    }
    
    if (setupData.password.length < 8) {
      setError('Password must be at least 8 characters long')
      return
    }
    
    setLoading(true)
    setError('')
    
    try {
      const payload = {
        username: setupData.username,
        email: setupData.email,
        password: setupData.password,
        full_name: setupData.full_name || undefined
      }
      
      const response = await client.post('/auth/setup', payload)
      
      const { access_token, user } = response.data
      login(access_token, user)
      navigate('/')
    } catch (err) {
      console.error('Setup error:', err)
      setError(err.response?.data?.detail || 'Setup failed. Please try again.')
    } finally {
      setLoading(false)
    }
  }
  
  if (setupRequired) {
    return (
      <div className="min-h-screen bg-zinc-950 flex items-center justify-center p-4 selection:bg-blue-500/30">
        <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-20 pointer-events-none" />
        
        <div className="relative bg-zinc-900/50 border border-zinc-800 backdrop-blur-xl rounded-2xl shadow-2xl w-full max-w-md p-8 animate-fade-in">
          <div className="flex flex-col items-center mb-8">
            <div className="relative mb-4">
              <div className="w-16 h-16 bg-blue-500/20 rounded-2xl flex items-center justify-center relative z-10 border border-blue-500/30">
                <Shield className="w-8 h-8 text-blue-500" />
              </div>
              <div className="absolute inset-0 bg-blue-500/20 blur-2xl rounded-full" />
            </div>
            <h1 className="text-2xl font-bold text-white tracking-tight">System Setup</h1>
            <p className="text-zinc-500 mt-2 text-center text-sm font-medium">Create your security administrator account</p>
          </div>
          
          {error && (
            <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-3 mb-6 text-red-400 text-sm flex items-center gap-2">
              <div className="w-1 h-4 bg-red-500 rounded-full" />
              {error}
            </div>
          )}
          
          <form onSubmit={handleSetup} className="space-y-4">
            <div className="space-y-1">
              <label className="block text-xs font-bold text-zinc-500 uppercase tracking-widest ml-1">Username</label>
              <div className="relative group">
                <User className="absolute left-3 top-3 w-5 h-5 text-zinc-600 group-focus-within:text-blue-500 transition-colors" />
                <input
                  type="text"
                  name="username"
                  value={setupData.username}
                  onChange={handleSetupChange}
                  className="w-full bg-zinc-950 border border-zinc-800 rounded-xl py-2.5 pl-10 pr-4 text-zinc-100 placeholder-zinc-700 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50 transition-all"
                  placeholder="admin"
                  required
                />
              </div>
            </div>
            
            <div className="space-y-1">
              <label className="block text-xs font-bold text-zinc-500 uppercase tracking-widest ml-1">Email Address</label>
              <div className="relative group">
                <Mail className="absolute left-3 top-3 w-5 h-5 text-zinc-600 group-focus-within:text-blue-500 transition-colors" />
                <input
                  type="email"
                  name="email"
                  value={setupData.email}
                  onChange={handleSetupChange}
                  className="w-full bg-zinc-950 border border-zinc-800 rounded-xl py-2.5 pl-10 pr-4 text-zinc-100 placeholder-zinc-700 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50 transition-all"
                  placeholder="admin@security.local"
                  required
                />
              </div>
            </div>
            
            <div className="space-y-1">
              <label className="block text-xs font-bold text-zinc-500 uppercase tracking-widest ml-1">Password</label>
              <div className="relative group">
                <Lock className="absolute left-3 top-3 w-5 h-5 text-zinc-600 group-focus-within:text-blue-500 transition-colors" />
                <input
                  type={showPassword ? "text" : "password"}
                  name="password"
                  value={setupData.password}
                  onChange={handleSetupChange}
                  className="w-full bg-zinc-950 border border-zinc-800 rounded-xl py-2.5 pl-10 pr-10 text-zinc-100 placeholder-zinc-700 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50 transition-all"
                  placeholder="••••••••"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-3 text-zinc-600 hover:text-zinc-400 transition-colors"
                >
                  {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                </button>
              </div>
            </div>
            
            <div className="space-y-1">
              <label className="block text-xs font-bold text-zinc-500 uppercase tracking-widest ml-1">Confirm Password</label>
              <div className="relative group">
                <Lock className="absolute left-3 top-3 w-5 h-5 text-zinc-600 group-focus-within:text-blue-500 transition-colors" />
                <input
                  type={showPassword ? "text" : "password"}
                  name="confirmPassword"
                  value={setupData.confirmPassword}
                  onChange={handleSetupChange}
                  className="w-full bg-zinc-950 border border-zinc-800 rounded-xl py-2.5 pl-10 pr-10 text-zinc-100 placeholder-zinc-700 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50 transition-all"
                  placeholder="••••••••"
                  required
                />
              </div>
            </div>
            
            <button
              type="submit"
              disabled={loading}
              className="w-full bg-blue-600 hover:bg-blue-500 text-white font-bold py-3 px-4 rounded-xl transition-all shadow-[0_0_20px_rgba(59,130,246,0.3)] hover:shadow-[0_0_30px_rgba(59,130,246,0.5)] active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed mt-6"
            >
              {loading ? (
                <div className="flex items-center justify-center gap-2">
                  <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Initializng...
                </div>
              ) : 'Complete Initialization'}
            </button>
          </form>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-zinc-950 flex items-center justify-center p-4 selection:bg-blue-500/30">
      <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-20 pointer-events-none" />
      
      <div className="relative bg-zinc-900/50 border border-zinc-800 backdrop-blur-xl rounded-2xl shadow-2xl w-full max-w-md p-8 animate-fade-in">
        <div className="flex flex-col items-center mb-8">
          <div className="relative mb-4">
            <div className="w-16 h-16 bg-blue-500/20 rounded-2xl flex items-center justify-center relative z-10 border border-blue-500/30">
              <Shield className="w-8 h-8 text-blue-500" />
            </div>
            <div className="absolute inset-0 bg-blue-500/20 blur-2xl rounded-full" />
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight">EndpointSec</h1>
          <p className="text-zinc-500 mt-2 font-medium">Secure Terminal Authentication</p>
        </div>
        
        {error && (
          <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-3 mb-6 text-red-400 text-sm flex items-center gap-2">
            <div className="w-1 h-4 bg-red-500 rounded-full" />
            {error}
          </div>
        )}
        
        <form onSubmit={handleLogin} className="space-y-6">
          <div className="space-y-1">
            <label className="block text-xs font-bold text-zinc-500 uppercase tracking-widest ml-1">Username</label>
            <div className="relative group">
              <User className="absolute left-3 top-3 w-5 h-5 text-zinc-600 group-focus-within:text-blue-500 transition-colors" />
              <input
                type="text"
                name="username"
                value={loginData.username}
                onChange={handleLoginChange}
                className="w-full bg-zinc-950 border border-zinc-800 rounded-xl py-2.5 pl-10 pr-4 text-zinc-100 placeholder-zinc-700 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50 transition-all"
                placeholder="Enter username"
                required
              />
            </div>
          </div>
          
          <div className="space-y-1">
            <label className="block text-xs font-bold text-zinc-500 uppercase tracking-widest ml-1">Access Password</label>
            <div className="relative group">
              <Lock className="absolute left-3 top-3 w-5 h-5 text-zinc-600 group-focus-within:text-blue-500 transition-colors" />
              <input
                type={showPassword ? "text" : "password"}
                name="password"
                value={loginData.password}
                onChange={handleLoginChange}
                className="w-full bg-zinc-950 border border-zinc-800 rounded-xl py-2.5 pl-10 pr-10 text-zinc-100 placeholder-zinc-700 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50 transition-all"
                placeholder="••••••••"
                required
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-3 text-zinc-600 hover:text-zinc-400 transition-colors"
              >
                {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
              </button>
            </div>
          </div>
          
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-blue-600 hover:bg-blue-500 text-white font-bold py-3 px-4 rounded-xl transition-all shadow-[0_0_20px_rgba(59,130,246,0.3)] hover:shadow-[0_0_30px_rgba(59,130,246,0.5)] active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? (
              <div className="flex items-center justify-center gap-2">
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Authorizing...
              </div>
            ) : 'Sign In'}
          </button>
        </form>
      </div>
    </div>
  )
}

export default Login
