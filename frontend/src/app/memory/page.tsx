'use client';

import { useEffect, useState } from 'react';
import { api } from '@/lib/api/client';
import { Experience } from '@/lib/api/types';
import { Database, Activity, CheckCircle2, XCircle, HelpCircle } from 'lucide-react';
import Link from 'next/link';

export default function MemoryPage() {
  const [experiences, setExperiences] = useState<Experience[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      try {
        const data = await api.getExperiences(1, 50);
        setExperiences(data.items);
      } catch (error) {
        console.error("Failed to load memory experiences", error);
      } finally {
        setLoading(false);
      }
    }
    
    fetchData();
  }, []);

  const AssessmentIcon = ({ assessment }: { assessment: string }) => {
    switch (assessment) {
      case 'success': return <CheckCircle2 className="h-4 w-4 text-emerald-500" />;
      case 'failure': return <XCircle className="h-4 w-4 text-red-500" />;
      case 'partial': return <CheckCircle2 className="h-4 w-4 text-amber-500" />;
      default: return <HelpCircle className="h-4 w-4 text-zinc-500" />;
    }
  };

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-white mb-2 flex items-center gap-3">
          <Database className="h-8 w-8 text-cyan-500" />
          Episodic Memory
        </h1>
        <p className="text-zinc-400">Chronological ledger of autonomous operational experiences and outcomes.</p>
      </div>

      <div className="bg-zinc-900/50 border border-zinc-800 rounded-xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-zinc-800/50 text-zinc-400 uppercase tracking-wider text-xs border-b border-zinc-800">
              <tr>
                <th className="px-6 py-4 font-semibold">Timestamp</th>
                <th className="px-6 py-4 font-semibold">Target / Action</th>
                <th className="px-6 py-4 font-semibold">Environment</th>
                <th className="px-6 py-4 font-semibold">Expected vs Observed</th>
                <th className="px-6 py-4 font-semibold">Assessment</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800/50">
              {loading ? (
                <tr>
                  <td colSpan={5} className="px-6 py-12 text-center text-zinc-500">
                    <Activity className="h-5 w-5 animate-pulse inline mr-2" /> Loading Experiences...
                  </td>
                </tr>
              ) : experiences.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-6 py-12 text-center text-zinc-500">
                    No episodic memory data available.
                  </td>
                </tr>
              ) : (
                experiences.map(exp => (
                  <tr key={exp.experience_id} className="hover:bg-zinc-800/20 transition-colors">
                    <td className="px-6 py-4 whitespace-nowrap text-zinc-400 font-mono text-xs">
                      {new Date(exp.timestamp).toLocaleString()}
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex flex-col">
                        <span className="font-medium text-zinc-200">{exp.target_service}</span>
                        <span className="text-zinc-400 text-xs uppercase tracking-wider mt-1">{exp.action_type.replace('_', ' ')}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-2 py-1 rounded text-xs font-semibold uppercase tracking-wider ${
                        exp.is_simulated ? 'bg-blue-950/50 text-blue-400 border border-blue-900/50' : 'bg-red-950/50 text-red-400 border border-red-900/50'
                      }`}>
                        {exp.is_simulated ? 'Simulation' : 'Production'}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-zinc-300">
                      <div className="flex flex-col gap-1 text-xs">
                        <span className="text-zinc-500">Expected: {exp.expected_outcome || 'None'}</span>
                        <span>Observed: {exp.observed_outcome}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center gap-2 capitalize font-medium">
                        <AssessmentIcon assessment={exp.assessment} />
                        <span className={
                          exp.assessment === 'success' ? 'text-emerald-400' :
                          exp.assessment === 'failure' ? 'text-red-400' :
                          exp.assessment === 'partial' ? 'text-amber-400' :
                          'text-zinc-400'
                        }>{exp.assessment}</span>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
