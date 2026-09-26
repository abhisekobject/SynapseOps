'use client';

import { useEffect, useState } from 'react';
import { api } from '@/lib/api/client';
import { OperationalKnowledge } from '@/lib/api/types';
import { BookOpen, Activity, Percent } from 'lucide-react';
import Link from 'next/link';

export default function LearningPage() {
  const [knowledge, setKnowledge] = useState<OperationalKnowledge[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      try {
        const data = await api.getOperationalKnowledge(1, 50);
        setKnowledge(data.items);
      } catch (error) {
        console.error("Failed to load operational knowledge", error);
      } finally {
        setLoading(false);
      }
    }
    
    fetchData();
  }, []);

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-white mb-2 flex items-center gap-3">
          <BookOpen className="h-8 w-8 text-indigo-500" />
          Operational Learning
        </h1>
        <p className="text-zinc-400">Aggregated historical knowledge and effectiveness of operational actions.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {loading ? (
          <div className="col-span-full p-12 text-center text-zinc-500">
            <Activity className="h-5 w-5 animate-pulse inline mr-2" /> Loading Knowledge...
          </div>
        ) : knowledge.length === 0 ? (
          <div className="col-span-full p-12 text-center border border-zinc-800 border-dashed rounded-xl text-zinc-500">
            No operational knowledge aggregated yet.
          </div>
        ) : (
          knowledge.map(k => (
            <div key={k.knowledge_id} className="p-6 bg-zinc-900/50 border border-zinc-800 rounded-xl space-y-4">
              <div className="flex justify-between items-start">
                <div>
                  <h3 className="text-lg font-bold text-white uppercase tracking-wide">{k.action.replace('_', ' ')}</h3>
                  <p className="text-sm font-mono text-zinc-400">Target: {k.target}</p>
                </div>
                <span className={`px-2 py-1 rounded text-xs font-bold uppercase tracking-wider ${
                  k.is_simulated ? 'bg-blue-950/50 text-blue-400 border border-blue-900/50' : 'bg-red-950/50 text-red-400 border border-red-900/50'
                }`}>
                  {k.is_simulated ? 'Simulated' : 'Production'}
                </span>
              </div>
              
              <div className="pt-4 border-t border-zinc-800 flex items-center justify-between">
                <div>
                  <p className="text-xs text-zinc-500 uppercase font-semibold">Effectiveness</p>
                  <div className="flex items-center gap-1 mt-1">
                    <span className="text-2xl font-bold text-indigo-400">
                      {k.observed_effectiveness !== null ? Math.round(k.observed_effectiveness * 100) : '--'}
                    </span>
                    <Percent className="h-4 w-4 text-indigo-500" />
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-xs text-zinc-500 uppercase font-semibold">Total Uses</p>
                  <p className="text-xl font-bold text-zinc-200 mt-1">{k.total_experiences}</p>
                </div>
              </div>

              <div className="flex justify-between text-xs font-medium pt-2">
                <span className="text-emerald-400 text-center w-full">{k.successful_outcomes} Success</span>
                <span className="text-amber-400 text-center w-full">{k.partial_outcomes} Partial</span>
                <span className="text-red-400 text-center w-full">{k.failed_outcomes} Failed</span>
              </div>

              <div className="pt-4 border-t border-zinc-800 text-xs text-zinc-500 text-right">
                Last updated: {new Date(k.last_updated).toLocaleDateString()}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
