import React, { useEffect, useState } from 'react';
import { ShieldAlert, Lock, AlertTriangle, Fingerprint, Activity } from 'lucide-react';

export default function AccessDenied() {
  const [timestamp, setTimestamp] = useState(new Date());
  const [securityId] = useState(() => Math.random().toString(36).substring(2, 10).toUpperCase());

  useEffect(() => {
    const timer = setInterval(() => setTimestamp(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  return (
    <div className="min-h-screen bg-zinc-950 flex flex-col items-center justify-center p-4 relative overflow-hidden font-mono">
      {/* Background Gradients/Effects */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-red-500/50 to-transparent" />
        <div className="absolute bottom-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-red-500/50 to-transparent" />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-red-500/5 rounded-full blur-[120px]" />
        
        {/* Grid pattern overlay */}
        <div className="absolute inset-0 bg-[linear-gradient(rgba(24,24,27,0.9)_2px,transparent_2px),linear-gradient(90deg,rgba(24,24,27,0.9)_2px,transparent_2px)] bg-[size:40px_40px] [mask-image:radial-gradient(ellipse_80%_80%_at_50%_50%,black,transparent)] opacity-20" />
      </div>

      <div className="relative z-10 max-w-2xl w-full">
        {/* Main Card */}
        <div className="bg-zinc-900/50 backdrop-blur-xl border border-red-500/20 rounded-2xl p-8 md:p-12 shadow-[0_0_50px_rgba(239,68,68,0.1)] relative group">
          
          {/* Corner accents */}
          <div className="absolute -top-1 -left-1 w-8 h-8 border-t-2 border-l-2 border-red-500 rounded-tl-lg" />
          <div className="absolute -top-1 -right-1 w-8 h-8 border-t-2 border-r-2 border-red-500 rounded-tr-lg" />
          <div className="absolute -bottom-1 -left-1 w-8 h-8 border-b-2 border-l-2 border-red-500 rounded-bl-lg" />
          <div className="absolute -bottom-1 -right-1 w-8 h-8 border-b-2 border-r-2 border-red-500 rounded-br-lg" />

          {/* Icon Header */}
          <div className="flex flex-col items-center mb-8">
            <div className="relative mb-6">
              <div className="absolute inset-0 bg-red-500 blur-2xl opacity-20 animate-pulse" />
              <div className="relative bg-zinc-950 p-4 rounded-full border border-red-500/30 ring-4 ring-red-500/10">
                <ShieldAlert className="w-16 h-16 text-red-500 animate-[pulse_3s_ease-in-out_infinite]" />
              </div>
              <div className="absolute -bottom-2 left-1/2 -translate-x-1/2 bg-red-950/80 text-red-400 text-[10px] px-2 py-0.5 rounded border border-red-500/30 uppercase tracking-wider whitespace-nowrap">
                System Lockdown
              </div>
            </div>

            <h1 className="text-4xl md:text-5xl font-black text-transparent bg-clip-text bg-gradient-to-b from-white to-zinc-400 tracking-tighter mb-2 text-center">
              ACCESS DENIED
            </h1>
            <p className="text-red-400/80 font-medium tracking-widest text-sm uppercase flex items-center gap-2">
              <Lock className="w-3 h-3" />
              Security Protocol Enforced
            </p>
          </div>

          {/* Content */}
          <div className="space-y-6 text-center relative">
            <div className="bg-red-500/5 border border-red-500/10 rounded-xl p-6">
              <p className="text-zinc-300 text-lg leading-relaxed">
                This website has been blocked by your organization's security policy.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs text-zinc-500">
              <div className="bg-zinc-950/50 p-3 rounded-lg border border-zinc-800 flex items-center justify-between">
                <span className="flex items-center gap-2">
                  <Activity className="w-3 h-3 text-blue-500" />
                  TIMESTAMP
                </span>
                <span className="font-mono text-zinc-300">
                  {timestamp.toLocaleTimeString()}
                </span>
              </div>
              <div className="bg-zinc-950/50 p-3 rounded-lg border border-zinc-800 flex items-center justify-between">
                <span className="flex items-center gap-2">
                  <Fingerprint className="w-3 h-3 text-blue-500" />
                  SECURITY ID
                </span>
                <span className="font-mono text-zinc-300 tracking-wider">
                  #{securityId}
                </span>
              </div>
            </div>

            <div className="pt-6 border-t border-red-500/10">
              <div className="flex items-start gap-3 text-left">
                <AlertTriangle className="w-5 h-5 text-red-500/50 shrink-0 mt-0.5" />
                <p className="text-xs text-zinc-500 leading-relaxed">
                  <strong className="text-zinc-400 block mb-1">Violation Notice</strong>
                  Attempting to bypass security controls is a violation of corporate policy and has been logged. 
                  If you believe this site was blocked in error, please contact your IT administrator with the Security ID above.
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="mt-8 text-center">
          <p className="text-[10px] text-zinc-700 uppercase tracking-[0.2em]">
            Secure Endpoint Protection • v2.4.0
          </p>
        </div>
      </div>
    </div>
  );
}
