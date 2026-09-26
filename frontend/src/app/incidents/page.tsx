'use client';

import { useEffect, useState } from 'react';
import { api } from '@/lib/api/client';
import { Incident } from '@/lib/api/types';
import { AlertTriangle, Activity, ChevronLeft, ChevronRight, Search } from 'lucide-react';
import Link from 'next/link';

export default function IncidentsPage() {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);

  useEffect(() => {
    async function fetchData() {
      setLoading(true);
      try {
        const data = await api.getIncidents(page, 20);
        setIncidents(data.items);
        setTotalPages(data.pages);
      } catch (error) {
        console.error("Failed to load incidents", error);
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
          Incident Center
        </h1>
        <p className="text-zinc-400">Central hub for tracking, investigating, and managing infrastructure incidents.</p>
      </div>

      <div className="bg-zinc-900/50 border border-zinc-800 rounded-xl overflow-hidden">
        <div className="p-4 border-b border-zinc-800 flex justify-between items-center bg-zinc-900">
          <div className="relative w-64">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-500" />
            <input 
              type="text" 
              placeholder="Filter incidents..." 
              className="w-full bg-zinc-950 border border-zinc-800 rounded-md py-2 pl-9 pr-4 text-sm text-zinc-300 focus:outline-none focus:border-blue-500"
              disabled
            />
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-zinc-800/50 text-zinc-400 uppercase tracking-wider text-xs border-b border-zinc-800">
              <tr>
                <th className="px-6 py-4 font-semibold">Incident ID</th>
                <th className="px-6 py-4 font-semibold">Severity</th>
                <th className="px-6 py-4 font-semibold">Title</th>
                <th className="px-6 py-4 font-semibold">Status</th>
                <th className="px-6 py-4 font-semibold">Affected Services</th>
                <th className="px-6 py-4 font-semibold">Created</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800/50">
              {loading ? (
                <tr>
                  <td colSpan={6} className="px-6 py-12 text-center text-zinc-500">
                    <Activity className="h-5 w-5 animate-pulse inline mr-2" /> Loading...
                  </td>
                </tr>
              ) : incidents.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-6 py-12 text-center text-zinc-500">
                    No incidents found.
                  </td>
                </tr>
              ) : (
                incidents.map(incident => (
                  <tr key={incident.id} className="hover:bg-zinc-800/20 transition-colors group">
                    <td className="px-6 py-4 whitespace-nowrap text-blue-400 font-mono text-xs">
                      <Link href={`/incidents/${incident.id}`} className="hover:underline">
                        {incident.id.split('-')[0]}...
                      </Link>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-2 py-1 rounded text-xs font-semibold uppercase tracking-wider ${
                        incident.severity === 'critical' ? 'bg-red-950/50 text-red-400 border border-red-900/50' : 
                        incident.severity === 'high' ? 'bg-orange-950/50 text-orange-400 border border-orange-900/50' :
                        incident.severity === 'medium' ? 'bg-amber-950/50 text-amber-400 border border-amber-900/50' : 
                        'bg-zinc-800 text-zinc-400 border border-zinc-700'
                      }`}>
                        {incident.severity}
                      </span>
                    </td>
                    <td className="px-6 py-4 font-medium text-zinc-200">
                      <Link href={`/incidents/${incident.id}`} className="hover:text-blue-400 transition-colors">
                        {incident.title}
                      </Link>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-2 py-1 rounded text-xs font-semibold uppercase tracking-wider ${
                        incident.status === 'resolved' ? 'bg-emerald-950/30 text-emerald-400' :
                        incident.status === 'recovering' ? 'bg-blue-950/30 text-blue-400' :
                        'bg-zinc-800 text-zinc-400'
                      }`}>
                        {incident.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-zinc-400">
                      {incident.affected_services.join(', ') || '-'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-zinc-500 font-mono text-xs">
                      {new Date(incident.detected_at).toLocaleString()}
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
