'use client';

import { useEffect, useState } from 'react';
import { api } from '@/lib/api/client';
import { AlertTriangle, Info } from 'lucide-react';

export function EnvironmentBanner() {
  const [env, setEnv] = useState<string>('unknown');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchEnv() {
      try {
        const health = await api.getHealth();
        setEnv(health.environment.toLowerCase());
      } catch (e) {
        console.error("Failed to fetch environment", e);
        setEnv('unknown');
      } finally {
        setLoading(false);
      }
    }
    fetchEnv();
  }, []);

  if (loading) {
    return <div className="h-10 bg-zinc-900 animate-pulse" />;
  }

  if (env === 'production' || env === 'real') {
    return (
      <div className="bg-red-950 border-b border-red-900 text-red-200 px-4 py-2 flex items-center justify-center gap-2 text-sm font-bold uppercase tracking-widest shadow-[0_0_15px_rgba(220,38,38,0.2)]">
        <AlertTriangle className="h-4 w-4" />
        Production Environment — Proceed with Caution
        <AlertTriangle className="h-4 w-4" />
      </div>
    );
  }

  if (env === 'simulation' || env === 'development') {
    return (
      <div className="bg-blue-950 border-b border-blue-900 text-blue-200 px-4 py-2 flex items-center justify-center gap-2 text-sm font-semibold uppercase tracking-wider">
        <Info className="h-4 w-4" />
        Simulation Environment — Safe to experiment
      </div>
    );
  }

  return (
    <div className="bg-zinc-800 border-b border-zinc-700 text-zinc-300 px-4 py-2 flex items-center justify-center gap-2 text-sm font-semibold uppercase tracking-wider">
      <Info className="h-4 w-4" />
      Unknown Environment
    </div>
  );
}
