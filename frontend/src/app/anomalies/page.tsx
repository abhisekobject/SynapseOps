'use client';

import { useEffect, useState } from 'react';
import { api } from '@/lib/api/client';
import { Anomaly } from '@/lib/api/types';
import { AlertTriangle, ChevronLeft, ChevronRight, Activity } from 'lucide-react';
import Link from 'next/link';

export default function AnomaliesPage() {
  const [anomalies, setAnomalies] = useState<Anomaly[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);

  useEffect(() => {
    async function fetchData() {
      setLoading(true);
      try {
        const data = await api.getAnomalies(page, 20);
        setAnomalies(data.items);
        setTotalPages(data.pages);
      } catch (error) {
        console.error("Failed to load anomalies", error);
      } finally {
        setLoading(false);
      }
    }
    
    fetchData();
  }, [page]);

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-white mb-2 flex items-center gap-3">
          <AlertTriangle className="h-8 w-8 text-amber-500" />
          Anomalies
        </h1>
        <p className="text-zinc-400">Detected deviations from expected system baseline. Anomalies are signals, not confirmed root causes.</p>
      </div>

      <div className="bg-zinc-900/50 border border-zinc-800 rounded-xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-zinc-800/50 text-zinc-400 uppercase tracking-wider text-xs border-b border-zinc-800">
              <tr>
                <th className="px-6 py-4 font-semibold">Detected At</th>
                <th className="px-6 py-4 font-semibold">Severity</th>
                <th className="px-6 py-4 font-semibold">Service</th>
                <th className="px-6 py-4 font-semibold">Type</th>
                <th className="px-6 py-4 font-semibold">Value vs Baseline</th>
                <th className="px-6 py-4 font-semibold">Status</th>
                <th className="px-6 py-4 font-semibold">Incident</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800/50">
              {loading ? (
                <tr>
                  <td colSpan={7} className="px-6 py-12 text-center text-zinc-500">
                    <Activity className="h-5 w-5 animate-pulse inline mr-2" /> Loading...
                  </td>
                </tr>
              ) : anomalies.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-6 py-12 text-center text-zinc-500">
                    No anomalies found.
                  </td>
                </tr>
              ) : (
                anomalies.map(anomaly => (
                  <tr key={anomaly.id} className="hover:bg-zinc-800/20 transition-colors">
                    <td className="px-6 py-4 whitespace-nowrap text-zinc-400 font-mono text-xs">
                      {new Date(anomaly.detected_at).toLocaleString()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-2 py-1 rounded text-xs font-semibold uppercase tracking-wider ${
                        anomaly.severity === 'high' ? 'bg-red-950/50 text-red-400 border border-red-900/50' : 
                        anomaly.severity === 'medium' ? 'bg-amber-950/50 text-amber-400 border border-amber-900/50' : 
                        'bg-blue-950/50 text-blue-400 border border-blue-900/50'
                      }`}>
                        {anomaly.severity}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap font-medium text-zinc-200">
                      {anomaly.service_name}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-zinc-400 capitalize">
                      {anomaly.anomaly_type.replace('_', ' ')}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {anomaly.observed_value !== null ? (
                        <div className="flex flex-col">
                          <span className="text-zinc-200 font-mono text-xs">Obs: {anomaly.observed_value.toFixed(2)}</span>
                          <span className="text-zinc-500 font-mono text-xs">Base: {anomaly.baseline_value?.toFixed(2) || 'N/A'}</span>
                        </div>
                      ) : (
                        <span className="text-zinc-500 italic">N/A</span>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap capitalize text-zinc-300">
                      {anomaly.status}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {anomaly.incident_id ? (
                        <Link href={`/incidents/${anomaly.incident_id}`} className="text-blue-400 hover:text-blue-300 text-xs font-mono">
                          {anomaly.incident_id.split('-')[0]}...
                        </Link>
                      ) : (
                        <span className="text-zinc-600">-</span>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
        
        {!loading && totalPages > 1 && (
          <div className="px-6 py-4 border-t border-zinc-800 flex items-center justify-between">
            <button 
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page === 1}
              className="flex items-center gap-1 text-sm text-zinc-400 hover:text-white disabled:opacity-50"
            >
              <ChevronLeft className="h-4 w-4" /> Previous
            </button>
            <span className="text-sm text-zinc-500">
              Page {page} of {totalPages}
            </span>
            <button 
              onClick={() => setPage(p => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
              className="flex items-center gap-1 text-sm text-zinc-400 hover:text-white disabled:opacity-50"
            >
              Next <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
