'use client';

import { useEffect, useState } from 'react';
import { api } from '@/lib/api/client';
import { ServiceState, SystemSnapshot } from '@/lib/api/types';
import { Server, Activity, AlertTriangle, CheckCircle2 } from 'lucide-react';

export default function InfrastructurePage() {
  const [snapshot, setSnapshot] = useState<SystemSnapshot | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      try {
        const snap = await api.getSystemState();
        setSnapshot(snap);
      } catch (error) {
        console.error("Failed to load infrastructure data", error);
      } finally {
        setLoading(false);
      }
    }
    
    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="p-8 flex items-center justify-center min-h-screen">
        <div className="text-zinc-400 flex items-center gap-2">
          <Activity className="h-5 w-5 animate-pulse" />
          Loading Infrastructure State...
        </div>
      </div>
    );
  }

  const services = Object.values(snapshot?.services || {});

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-white mb-2">Infrastructure</h1>
        <p className="text-zinc-400">Real-time health and telemetry of SynapseOps managed services.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {services.map((svc: ServiceState) => (
          <div key={svc.service_id} className="p-6 bg-zinc-900/50 border border-zinc-800 rounded-xl space-y-4">
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-3">
                <Server className="h-6 w-6 text-zinc-400" />
                <h2 className="text-xl font-semibold text-zinc-100">{svc.service_id}</h2>
              </div>
              
              {svc.status === 'healthy' ? (
                <div className="flex items-center gap-1 text-emerald-400 bg-emerald-950/30 px-2 py-1 rounded text-xs font-semibold uppercase tracking-wider border border-emerald-900/50">
                  <CheckCircle2 className="h-3 w-3" /> Healthy
                </div>
              ) : svc.status === 'degraded' ? (
                <div className="flex items-center gap-1 text-amber-400 bg-amber-950/30 px-2 py-1 rounded text-xs font-semibold uppercase tracking-wider border border-amber-900/50">
                  <AlertTriangle className="h-3 w-3" /> Degraded
                </div>
              ) : (
                <div className="flex items-center gap-1 text-red-400 bg-red-950/30 px-2 py-1 rounded text-xs font-semibold uppercase tracking-wider border border-red-900/50">
                  <AlertTriangle className="h-3 w-3" /> Unavailable
                </div>
              )}
            </div>

            {svc.active_failures && svc.active_failures.length > 0 && (
              <div className="bg-red-950/30 border border-red-900/30 p-3 rounded-lg">
                <p className="text-xs font-semibold text-red-400 uppercase tracking-wider mb-2">Active Failures</p>
                <div className="flex flex-wrap gap-2">
                  {svc.active_failures.map(f => (
                    <span key={f} className="text-xs bg-red-900/50 text-red-200 px-2 py-1 rounded">{f}</span>
                  ))}
                </div>
              </div>
            )}

            <div className="space-y-3 pt-2">
              <p className="text-xs font-semibold text-zinc-500 uppercase tracking-wider">Telemetry</p>
              <div className="grid grid-cols-2 gap-4">
                {Object.entries(svc.metrics || {}).map(([key, value]) => (
                  <div key={key}>
                    <p className="text-xs text-zinc-500 capitalize">{key.replace(/_/g, ' ')}</p>
                    <p className="text-sm font-mono text-zinc-300">
                      {typeof value === 'number' ? (value % 1 === 0 ? value : value.toFixed(2)) : value}
                    </p>
                  </div>
                ))}
              </div>
            </div>
            
            <div className="pt-4 border-t border-zinc-800 text-xs text-zinc-600 text-right">
              Last updated: {new Date(svc.last_updated).toLocaleTimeString()}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
