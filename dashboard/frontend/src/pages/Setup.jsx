import React, { useState } from 'react'
import { 
  Book, 
  Terminal, 
  Server, 
  Laptop, 
  Settings, 
  HelpCircle, 
  FileText,
  Copy,
  Check,
  ChevronRight,
  AlertCircle
} from 'lucide-react'

const CopyButton = ({ text }) => {
  const [copied, setCopied] = useState(false)

  const handleCopy = () => {
    navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <button 
      onClick={handleCopy}
      className="absolute top-2 right-2 p-1.5 rounded-md text-zinc-400 hover:text-white hover:bg-zinc-800 transition-all"
      title="Copy to clipboard"
    >
      {copied ? <Check size={16} className="text-emerald-400" /> : <Copy size={16} />}
    </button>
  )
}

const CodeBlock = ({ command, label }) => (
  <div className="mt-3 mb-4 group relative">
    {label && <div className="text-xs font-mono text-zinc-500 mb-1 ml-1">{label}</div>}
    <div className="bg-black/80 border border-zinc-800 rounded-lg p-4 font-mono text-sm text-zinc-200 overflow-x-auto shadow-inner relative">
      <span className="select-none text-blue-500 mr-2">$</span>
      {command}
      <CopyButton text={command} />
    </div>
  </div>
)

const SectionHeader = ({ icon: Icon, title, description }) => (
  <div className="flex items-start gap-4 mb-6 pb-4 border-b border-zinc-800/60">
    <div className="p-3 bg-blue-500/10 rounded-xl border border-blue-500/20 text-blue-400">
      <Icon size={24} />
    </div>
    <div>
      <h2 className="text-xl font-bold text-white tracking-tight">{title}</h2>
      <p className="text-zinc-400 text-sm mt-1">{description}</p>
    </div>
  </div>
)

const Step = ({ number, title, children }) => (
  <div className="flex gap-4 relative pb-8 last:pb-0">
    <div className="flex-shrink-0 flex flex-col items-center">
      <div className="w-8 h-8 rounded-full bg-zinc-900 border border-zinc-700 flex items-center justify-center text-sm font-bold text-blue-400 shadow-[0_0_10px_rgba(59,130,246,0.2)] z-10 relative">
        {number}
      </div>
      <div className="w-px h-full bg-zinc-800 absolute top-8 bottom-0 -z-0" />
    </div>
    <div className="flex-1 pt-1">
      <h3 className="text-base font-medium text-zinc-200 mb-2">{title}</h3>
      <div className="text-zinc-400 text-sm leading-relaxed">
        {children}
      </div>
    </div>
  </div>
)

const ConfigItem = ({ name, description }) => (
  <div className="flex items-start gap-3 p-3 rounded-lg hover:bg-zinc-800/50 transition-colors border border-transparent hover:border-zinc-800 group">
    <div className="mt-1 text-blue-500 group-hover:translate-x-0.5 transition-transform">
      <ChevronRight size={16} />
    </div>
    <div>
      <div className="font-mono text-sm font-medium text-zinc-200 bg-zinc-900 px-1.5 py-0.5 rounded inline-block mb-1">{name}</div>
      <div className="text-sm text-zinc-500 mt-0.5">{description}</div>
    </div>
  </div>
)

const Setup = () => {
  return (
    <div className="space-y-8 animate-fade-in max-w-7xl mx-auto">
      {/* Page Header */}
      <div className="flex flex-col gap-2 mb-8 border-b border-zinc-800 pb-6">
        <h1 className="text-3xl font-bold tracking-tight text-white flex items-center gap-4">
          <Book className="text-blue-500" size={32} />
          Setup Guide
        </h1>
        <p className="text-lg text-zinc-400 max-w-2xl">
          Complete installation instructions and documentation for deploying the SystemScheduler dashboard and agents.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Left Column - Main Installation Flow */}
        <div className="lg:col-span-7 space-y-8">
          
          {/* Quick Start Prerequisites */}
          <div className="bg-zinc-900/50 border border-zinc-800 rounded-2xl p-6 backdrop-blur-sm shadow-xl">
            <h3 className="text-sm font-bold text-amber-500 uppercase tracking-wider mb-4 flex items-center gap-2">
              <AlertCircle size={16} />
              Prerequisites
            </h3>
            <ul className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {[
                "Python 3.11+",
                "Node.js 18+",
                "AWS Account (S3 access)",
                "Windows 10/11 (for Agents)"
              ].map((item, i) => (
                <li key={i} className="flex items-center gap-2 text-zinc-300 text-sm bg-zinc-950/50 p-3 rounded-lg border border-zinc-800/50">
                  <Check size={14} className="text-emerald-500" />
                  {item}
                </li>
              ))}
            </ul>
          </div>

          {/* Dashboard Setup */}
          <div className="bg-zinc-900/50 backdrop-blur-sm border border-zinc-800 rounded-2xl p-8 shadow-xl">
            <SectionHeader 
              icon={Server} 
              title="Dashboard Setup" 
              description="Deploying the central management server" 
            />
            
            <div className="space-y-2">
              <Step number="1" title="Clone Repository">
                <p className="mb-2">Get the source code from the repository.</p>
                <CodeBlock command="git clone https://github.com/your-org/SystemScheduler.git" />
              </Step>

              <Step number="2" title="Install Backend Dependencies">
                <p className="mb-2">Set up the Python environment and required packages.</p>
                <CodeBlock command="pip install -r requirements.txt" />
              </Step>

              <Step number="3" title="Install Frontend Dependencies">
                <p className="mb-2">Navigate to the frontend directory and install Node packages.</p>
                <CodeBlock 
                  command="cd dashboard/frontend && npm install" 
                  label="Run from root directory"
                />
              </Step>

              <Step number="4" title="Start Backend Server">
                <p className="mb-2">Launch the FastAPI backend service.</p>
                <CodeBlock command="python -m dashboard.backend.main" />
              </Step>

              <Step number="5" title="Start Frontend Interface">
                <p className="mb-2">Run the React development server.</p>
                <CodeBlock command="npm run dev" />
              </Step>
              
              <Step number="6" title="Initial Access">
                <p>
                  Open your browser to <span className="text-blue-400 font-medium font-mono bg-blue-900/20 px-1 py-0.5 rounded">http://localhost:5173</span>. 
                  You will be prompted to create an admin account on the first run.
                </p>
              </Step>
            </div>
          </div>

          {/* Agent Installation */}
          <div className="bg-zinc-900/50 backdrop-blur-sm border border-zinc-800 rounded-2xl p-8 shadow-xl">
            <SectionHeader 
              icon={Laptop} 
              title="Agent Installation" 
              description="Deploying monitoring agents on Windows endpoints" 
            />

            <div className="space-y-2">
              <Step number="1" title="Prepare Agent Files">
                <p>Copy the <span className="font-mono text-zinc-300 bg-zinc-800 px-1 py-0.5 rounded">agent/</span> folder to the target Windows machine (e.g., <span className="font-mono text-zinc-300">C:\SystemScheduler</span>).</p>
              </Step>

              <Step number="2" title="Configuration">
                <p className="mb-2">Edit <span className="font-mono text-zinc-300 bg-zinc-800 px-1 py-0.5 rounded">config.yaml</span> with your S3 credentials and dashboard URL.</p>
              </Step>

              <Step number="3" title="Install Dependencies">
                <p className="mb-2">Run the installation script or install manually via pip.</p>
                <CodeBlock command="pip install -r requirements.txt" />
              </Step>

              <Step number="4" title="Run Agent">
                <p className="mb-2">Start the agent process. Ideally, configure this as a Windows Service using NSSM or similar tools for persistence.</p>
                <CodeBlock command="python agent_main.py" />
              </Step>
            </div>
          </div>
        </div>

        {/* Right Column - Reference & Info */}
        <div className="lg:col-span-5 space-y-8">
          
          {/* Configuration Reference */}
          <div className="bg-zinc-900/50 backdrop-blur-sm border border-zinc-800 rounded-2xl p-6 shadow-lg">
            <div className="flex items-center gap-3 mb-6 border-b border-zinc-800 pb-4">
              <Settings className="text-blue-400" size={20} />
              <h2 className="text-lg font-bold text-white">Configuration Reference</h2>
            </div>
            
            <div className="space-y-1 bg-zinc-950/30 rounded-xl p-2 border border-zinc-800/50">
              <ConfigItem 
                name="s3_bucket_settings" 
                description="AWS credentials and bucket name for log uploads" 
              />
              <ConfigItem 
                name="scan_paths" 
                description="Directories to monitor for file changes" 
              />
              <ConfigItem 
                name="usb_control" 
                description="Allow/Block policies for external storage devices" 
              />
              <ConfigItem 
                name="network_blocking" 
                description="IPs and Domains to block at the firewall level" 
              />
              <ConfigItem 
                name="dashboard_url" 
                description="URL of this management console for heartbeat check-ins" 
              />
            </div>
          </div>

          {/* API Documentation */}
          <div className="bg-gradient-to-br from-zinc-900 to-zinc-950 border border-zinc-800 rounded-2xl p-6 relative overflow-hidden shadow-lg group">
            <div className="absolute top-0 right-0 p-3 opacity-5 group-hover:opacity-10 transition-opacity">
              <FileText size={120} />
            </div>
            <div className="flex items-center gap-3 mb-4 relative z-10">
              <Terminal className="text-emerald-400" size={24} />
              <h2 className="text-lg font-bold text-white">API Documentation</h2>
            </div>
            <p className="text-zinc-400 text-sm mb-6 relative z-10 leading-relaxed">
              The backend provides a full REST API documented with Swagger/OpenAPI. 
              Useful for third-party integrations or custom agent development.
            </p>
            <a 
              href="http://localhost:8000/docs" 
              target="_blank" 
              rel="noreferrer"
              className="inline-flex items-center gap-2 bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 px-4 py-2 rounded-lg text-sm font-medium transition-colors border border-emerald-500/20 shadow-[0_0_15px_rgba(16,185,129,0.1)] hover:shadow-[0_0_20px_rgba(16,185,129,0.2)]"
            >
              View API Docs
              <ChevronRight size={14} />
            </a>
          </div>

          {/* Troubleshooting */}
          <div className="bg-zinc-900/50 backdrop-blur-sm border border-zinc-800 rounded-2xl p-6 shadow-lg">
            <div className="flex items-center gap-3 mb-6 border-b border-zinc-800 pb-4">
              <HelpCircle className="text-amber-400" size={20} />
              <h2 className="text-lg font-bold text-white">Troubleshooting</h2>
            </div>
            
            <div className="space-y-4">
              <div className="p-4 bg-zinc-950/50 rounded-lg border border-zinc-800">
                <h4 className="text-zinc-200 font-medium text-sm mb-1 flex items-center gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-red-500"></span>
                  Agent not connecting?
                </h4>
                <p className="text-xs text-zinc-400 leading-relaxed pl-3.5">
                  Verify the <code className="bg-black px-1 py-0.5 rounded text-zinc-300 font-mono">dashboard_url</code> in config.yaml is reachable from the agent machine. Check Windows Firewall settings.
                </p>
              </div>
              
              <div className="p-4 bg-zinc-950/50 rounded-lg border border-zinc-800">
                <h4 className="text-zinc-200 font-medium text-sm mb-1 flex items-center gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-amber-500"></span>
                  Database locked?
                </h4>
                <p className="text-xs text-zinc-400 leading-relaxed pl-3.5">
                  If using SQLite, ensure no other process is holding the lock. Restart the backend service to clear stale connections.
                </p>
              </div>

              <div className="mt-4 pt-4 border-t border-zinc-800">
                <h4 className="text-zinc-500 text-xs font-bold uppercase tracking-wider mb-3">Log Locations</h4>
                <ul className="space-y-2 text-xs font-mono text-zinc-300">
                  <li className="flex justify-between p-2 bg-zinc-900 rounded border border-zinc-800/50">
                    <span className="text-zinc-500">Backend:</span>
                    <span>backend.log</span>
                  </li>
                  <li className="flex justify-between p-2 bg-zinc-900 rounded border border-zinc-800/50">
                    <span className="text-zinc-500">Agent:</span>
                    <span>agent.log</span>
                  </li>
                </ul>
              </div>
            </div>
          </div>

        </div>
      </div>
    </div>
  )
}

export default Setup
