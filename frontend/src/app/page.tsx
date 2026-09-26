'use client';

import { useEffect, useState } from 'react';
import { api } from '@/lib/api/client';
import { SystemSnapshot, Event, Incident } from '@/lib/api/types';
import { Activity, AlertCircle, AlertTriangle, CheckCircle2, Server, ShieldCheck } from 'lucide-react';
import Link from 'next/link';

export default function CommandCenter() {
  const [snapshot, setSnapshot] = useState<SystemSnapshot | null>(null);
  const [activeEvents, setActiveEvents] = useState<Event[]>([]);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      try {
        const [snap, eventsRes, incidentsRes] = await Promise.all([
          api.getSystemState(),
          api.getActiveEvents(),
          api.getIncidents(1, 5)
        ]);
        setSnapshot(snap);
        setActiveEvents(eventsRes);
        setIncidents(incidentsRes.items.filter(i => i.status !== 'resolved' && i.status !== 'closed'));
      } catch (error) {
        console.error("Failed to load command center data", error);
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
          Loading Command Center...
        </div>
      </div>
    );
  }

  const isHealthy = snapshot?.system_status === 'healthy';

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-white mb-2">Command Center</h1>
        <p className="text-zinc-400">High-level overview of SynapseOps system health and active intelligence operations.</p>
      </div>

      {/* Top Stats Row */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className={`p-6 rounded-xl border ${isHealthy ? 'bg-emerald-950/20 border-emerald-900/50' : 'bg-red-950/20 border-red-900/50'}`}>
          <div className="flex items-center gap-3 mb-2">
            {isHealthy ? (
              <CheckCircle2 className="h-6 w-6 text-emerald-500" />
            ) : (
              <AlertTriangle className="h-6 w-6 text-red-500" />
            )}
            <h3 className="font-semibold text-zinc-300">System Status</h3>
          </div>
          <p className={`text-2xl font-bold capitalize ${isHealthy ? 'text-emerald-400' : 'text-red-400'}`}>
            {snapshot?.system_status || 'Unknown'}
          </p>
        </div>

        <div className="p-6 rounded-xl border bg-zinc-900/50 border-zinc-800">
          <div className="flex items-center gap-3 mb-2">
            <Server className="h-5 w-5 text-blue-400" />
            <h3 className="font-semibold text-zinc-300">Services</h3>
          </div>
          <p className="text-2xl font-bold text-white">
            {Object.keys(snapshot?.services || {}).length}
          </p>
          {snapshot?.degraded_services && snapshot.degraded_services.length > 0 && (
            <p className="text-sm text-red-400 mt-1">{snapshot.degraded_services.length} degraded</p>
          )}
        </div>

        <div className="p-6 rounded-xl border bg-zinc-900/50 border-zinc-800">
          <div className="flex items-center gap-3 mb-2">
            <AlertCircle className="h-5 w-5 text-amber-400" />
            <h3 className="font-semibold text-zinc-300">Active Incidents</h3>
          </div>
          <p className="text-2xl font-bold text-white">
            {incidents.length}
          </p>
        </div>

        <div className="p-6 rounded-xl border bg-zinc-900/50 border-zinc-800">
          <div className="flex items-center gap-3 mb-2">
            <ShieldCheck className="h-5 w-5 text-purple-400" />
            <h3 className="font-semibold text-zinc-300">Active Events</h3>
          </div>
          <p className="text-2xl font-bold text-white">
            {activeEvents.length}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Active Incidents */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-bold text-white">Active Incidents</h2>
            <Link href="/incidents" className="text-sm text-blue-400 hover:text-blue-300">View All</Link>
          </div>
          
          {incidents.length === 0 ? (
            <div className="p-8 text-center border border-zinc-800 border-dashed rounded-xl text-zinc-500">
              No active incidents.
            </div>
          ) : (
            <div className="space-y-3">
              {incidents.map(incident => (
                <Link key={incident.id} href={`/incidents/${incident.id}`}>
                  <div className="p-4 bg-zinc-900/50 border border-zinc-800 rounded-xl hover:border-zinc-600 transition-colors cursor-pointer group">
                    <div className="flex justify-between items-start mb-2">
                      <h3 className="font-semibold text-zinc-200 group-hover:text-white transition-colors">{incident.title}</h3>
                      <span className={`text-xs px-2 py-1 rounded font-medium uppercase tracking-wider
                        ${incident.severity === 'critical' ? 'bg-red-950 text-red-400' : 
                          incident.severity === 'high' ? 'bg-orange-950 text-orange-400' :
                          incident.severity === 'medium' ? 'bg-amber-950 text-amber-400' : 
                          'bg-zinc-800 text-zinc-400'}`}>
                        {incident.severity}
                      </span>
                    </div>
                    <div className="flex gap-4 text-sm text-zinc-500">
                      <span>Status: <span className="text-zinc-300 capitalize">{incident.status}</span></span>
                      <span>Services: <span className="text-zinc-300">{incident.affected_services.join(', ') || 'None'}</span></span>
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>

        {/* Recent Events */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-bold text-white">Recent Operational Events</h2>
            <Link href="/events" className="text-sm text-blue-400 hover:text-blue-300">View All</Link>
          </div>

          {activeEvents.length === 0 ? (
            <div className="p-8 text-center border border-zinc-800 border-dashed rounded-xl text-zinc-500">
              No active events.
            </div>
          ) : (
            <div className="space-y-3">
              {activeEvents.slice(0, 5).map(event => (
                <div key={event.id} className="p-3 bg-zinc-900/30 border border-zinc-800/50 rounded-lg flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className={`h-2 w-2 rounded-full ${event.severity === 'error' ? 'bg-red-500' : event.severity === 'warning' ? 'bg-amber-500' : 'bg-blue-500'}`} />
                    <span className="text-sm font-medium text-zinc-300">{event.service_id}</span>
                    <span className="text-sm text-zinc-500">{event.event_type}</span>
                  </div>
                  <span className="text-xs text-zinc-600 font-mono">
                    {new Date(event.created_at).toLocaleTimeString()}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
