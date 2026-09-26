'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { api } from '@/lib/api/client';
import { Incident, Anomaly } from '@/lib/api/types';
import { AlertTriangle, Activity, Database, Network, Server, Hash, Clock, Box } from 'lucide-react';
import Link from 'next/link';

export default function IncidentDetailPage() {
  const params = useParams();
  const id = params.id as string;
  
  const [incident, setIncident] = useState<Incident | null>(null);
  const [anomalies, setAnomalies] = useState<Anomaly[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      setLoading(true);
      try {
        const [incData, anomData] = await Promise.all([
          api.getIncident(id),
          api.getAnomalies(1, 100) // Simple fetch to filter correlated
        ]);
        setIncident(incData);
        setAnomalies(anomData.items.filter(a => a.incident_id === id));
      } catch (error) {
        console.error("Failed to load incident detail", error);
      } finally {
        setLoading(false);
      }
    }
    
    if (id) fetchData();
  }, [id]);

  if (loading || !incident) {
    return (
      <div className="p-8 flex items-center justify-center min-h-screen">
        <div className="text-zinc-400 flex items-center gap-2">
          <Activity className="h-5 w-5 animate-pulse" />
          Loading Incident Details...
        </div>
      </div>
    );
  }

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      <div className="flex items-center gap-2 text-sm text-zinc-500 mb-6">
        <Link href="/incidents" className="hover:text-zinc-300">Incidents</Link>
        <span>/</span>
        <span className="text-zinc-300 font-mono">{incident.id.split('-')[0]}</span>
      </div>

      <div className="flex flex-col md:flex-row md:items-start justify-between gap-6">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <span className={`px-2 py-1 rounded text-xs font-bold uppercase tracking-wider ${
              incident.severity === 'critical' ? 'bg-red-950/50 text-red-400 border border-red-900/50' : 
              incident.severity === 'high' ? 'bg-orange-950/50 text-orange-400 border border-orange-900/50' :
              incident.severity === 'medium' ? 'bg-amber-950/50 text-amber-400 border border-amber-900/50' : 
              'bg-zinc-800 text-zinc-400 border border-zinc-700'
            }`}>
              {incident.severity}
            </span>
            <span className="px-2 py-1 rounded text-xs font-bold uppercase tracking-wider bg-blue-950/30 text-blue-400 border border-blue-900/50">
              {incident.status}
            </span>
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-white mb-2">{incident.title}</h1>
          <p className="text-zinc-400 max-w-3xl">{incident.description || 'No detailed description provided.'}</p>
        </div>
        
        <div className="flex flex-col gap-2 min-w-[250px]">
          <div className="p-4 bg-zinc-900/50 border border-zinc-800 rounded-xl space-y-3">
            <div className="flex justify-between text-sm">
              <span className="text-zinc-500 flex items-center gap-1"><Clock className="h-4 w-4" /> Detected</span>
              <span className="text-zinc-300 font-mono text-xs">{new Date(incident.detected_at).toLocaleString()}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-zinc-500 flex items-center gap-1"><Hash className="h-4 w-4" /> Incident ID</span>
              <span className="text-zinc-300 font-mono text-xs">{incident.id.split('-')[0]}</span>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 pt-6">
        {/* Left Column - Intelligence */}
        <div className="lg:col-span-2 space-y-6">
          
          <div className="p-6 bg-zinc-900/50 border border-zinc-800 rounded-xl">
            <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <Network className="h-5 w-5 text-blue-400" /> Affected Services
            </h2>
            <div className="flex flex-wrap gap-2">
              {incident.affected_services.map(svc => (
                <div key={svc} className="flex items-center gap-2 bg-zinc-800 px-3 py-1.5 rounded-md border border-zinc-700">
                  <Server className="h-4 w-4 text-zinc-400" />
                  <span className="text-sm font-medium text-zinc-300">{svc}</span>
                </div>
              ))}
              {incident.affected_services.length === 0 && <span className="text-zinc-500 text-sm">None</span>}
            </div>
          </div>

          <div className="p-6 bg-zinc-900/50 border border-zinc-800 rounded-xl">
            <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <Activity className="h-5 w-5 text-emerald-400" /> Correlated Anomalies ({anomalies.length})
            </h2>
            <div className="space-y-3">
              {anomalies.length === 0 ? (
                <p className="text-sm text-zinc-500 italic">No anomalies correlated with this incident.</p>
              ) : (
                anomalies.map(anomaly => (
                  <div key={anomaly.id} className="p-3 bg-zinc-950 border border-zinc-800/50 rounded-lg flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className={`h-2 w-2 rounded-full ${anomaly.severity === 'high' ? 'bg-red-500' : 'bg-amber-500'}`} />
                      <span className="text-sm font-medium text-zinc-300">{anomaly.service_name}</span>
                      <span className="text-sm text-zinc-500 capitalize">{anomaly.anomaly_type.replace('_', ' ')}</span>
                    </div>
                    {anomaly.observed_value !== null && (
                      <span className="text-xs text-zinc-500 font-mono">
                        Val: {anomaly.observed_value.toFixed(2)}
                      </span>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>

        </div>

        {/* Right Column - Timeline & Navigation */}
        <div className="space-y-6">
          <div className="p-6 bg-zinc-900/50 border border-zinc-800 rounded-xl">
            <h2 className="text-lg font-semibold text-white mb-4">Intelligence Tools</h2>
            <div className="space-y-2 flex flex-col">
              <Link href="/reasoning" className="p-3 bg-zinc-800/50 hover:bg-zinc-800 border border-zinc-700 rounded-lg text-sm text-zinc-200 font-medium transition-colors text-center">
                View AI Reasoning
              </Link>
              <Link href="/recovery" className="p-3 bg-zinc-800/50 hover:bg-zinc-800 border border-zinc-700 rounded-lg text-sm text-zinc-200 font-medium transition-colors text-center">
                View Recovery Plans
              </Link>
            </div>
          </div>

          <div className="p-6 bg-zinc-900/50 border border-zinc-800 rounded-xl">
            <h2 className="text-lg font-semibold text-white mb-4">Incident Timeline</h2>
            <div className="relative pl-4 border-l border-zinc-800 space-y-6">
              <div className="relative">
                <div className="absolute -left-[21px] top-1 h-2 w-2 rounded-full bg-amber-500" />
                <p className="text-sm font-medium text-zinc-300">Incident Detected</p>
                <p className="text-xs text-zinc-500 font-mono mt-1">{new Date(incident.detected_at).toLocaleString()}</p>
              </div>
              
              {incident.probable_root_cause && (
                <div className="relative">
                  <div className="absolute -left-[21px] top-1 h-2 w-2 rounded-full bg-blue-500" />
                  <p className="text-sm font-medium text-zinc-300">Root Cause Identified</p>
                  <p className="text-xs text-zinc-400 mt-1">{incident.probable_root_cause}</p>
                </div>
              )}

              {incident.status === 'resolved' && incident.resolved_at && (
                <div className="relative">
                  <div className="absolute -left-[21px] top-1 h-2 w-2 rounded-full bg-emerald-500" />
                  <p className="text-sm font-medium text-emerald-400">Incident Resolved</p>
                  <p className="text-xs text-zinc-500 font-mono mt-1">{new Date(incident.resolved_at).toLocaleString()}</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
