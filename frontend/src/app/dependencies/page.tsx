'use client';

import { useEffect, useState } from 'react';
import { api } from '@/lib/api/client';
import { DependencyGraphData } from '@/lib/api/types';
import { Network, ArrowRight, Server, Activity } from 'lucide-react';

export default function DependenciesPage() {
  const [graph, setGraph] = useState<DependencyGraphData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      try {
        const data = await api.getDependencies();
        setGraph(data);
      } catch (error) {
        console.error("Failed to load dependency graph", error);
      } finally {
        setLoading(false);
      }
    }
    
    fetchData();
  }, []);

  if (loading) {
    return (
      <div className="p-8 flex items-center justify-center min-h-screen">
        <div className="text-zinc-400 flex items-center gap-2">
          <Activity className="h-5 w-5 animate-pulse" />
          Loading Topology...
        </div>
      </div>
    );
  }

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-white mb-2 flex items-center gap-3">
          <Network className="h-8 w-8 text-emerald-500" />
          Dependency Topology
        </h1>
        <p className="text-zinc-400">Static architecture and direct dependencies of the simulated infrastructure.</p>
      </div>

      <div className="grid grid-cols-1 gap-6">
        {graph?.nodes.map(node => (
          <div key={node} className="p-6 bg-zinc-900/50 border border-zinc-800 rounded-xl flex flex-col md:flex-row gap-6 items-start md:items-center justify-between">
            
            <div className="flex items-center gap-4 flex-1">
              <div className="bg-zinc-800 p-4 rounded-xl border border-zinc-700">
                <Server className="h-8 w-8 text-blue-400" />
              </div>
              <div>
                <h3 className="text-xl font-bold text-white">{node}</h3>
                <p className="text-sm text-zinc-500">Service Component</p>
              </div>
            </div>

            <div className="flex flex-col gap-3 flex-1 w-full md:border-l md:border-zinc-800 md:pl-6">
              <div className="space-y-2">
                <p className="text-xs font-semibold text-zinc-500 uppercase tracking-wider">Depends On (Downstream)</p>
                {graph.edges[node] && graph.edges[node].length > 0 ? (
                  <div className="flex flex-wrap gap-2">
                    {graph.edges[node].map(dep => (
                      <div key={dep} className="flex items-center gap-2 bg-zinc-800/80 px-3 py-1.5 rounded-md border border-zinc-700/50">
                        <ArrowRight className="h-3 w-3 text-zinc-500" />
                        <span className="text-sm font-medium text-zinc-300">{dep}</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-zinc-600 italic">No external dependencies</p>
                )}
              </div>
            </div>
            
          </div>
        ))}
      </div>
      
      <div className="p-4 bg-blue-950/20 border border-blue-900/50 rounded-lg text-sm text-blue-200">
        <strong>Architecture Rule:</strong> The dependency topology defines the blast radius and directs the RCA engine. It establishes "A depends on B" but does not inherently claim causality.
      </div>
    </div>
  );
}
