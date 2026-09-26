'use client';

import { useState } from 'react';
import { api } from '@/lib/api/client';
import { ExecutionResult } from '@/lib/api/types';
import { PlaySquare, CheckCircle2, AlertTriangle, Activity, Database } from 'lucide-react';
import Link from 'next/link';

export default function ExecutionPage() {
  // For a real app, we would load the approved plan from global state or context.
  // Here, we provide a placeholder state that represents waiting for execution.
  const [results, setResults] = useState<ExecutionResult[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // In a real flow, this component receives the plan and approvalId from the recovery page context
  // Due to stateless demo constraints, we will mock the presentation of an execution flow if there are no results yet.
  
  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-white mb-2 flex items-center gap-3">
          <PlaySquare className="h-8 w-8 text-blue-500" />
          Execution Center
        </h1>
        <p className="text-zinc-400">Strictly bounded execution of authorized recovery plans.</p>
      </div>

      {!results && !loading && !error && (
        <div className="p-12 text-center border border-zinc-800 rounded-xl bg-zinc-900/50">
          <PlaySquare className="h-12 w-12 text-zinc-500 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-white mb-2">No Active Execution</h2>
          <p className="text-zinc-400 mb-6 max-w-md mx-auto">
            Executions are triggered from an authorized recovery plan in the Recovery Center.
          </p>
          <Link 
            href="/recovery"
            className="inline-block px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md font-medium transition-colors"
          >
            Go to Recovery Center
          </Link>
        </div>
      )}

      {loading && (
        <div className="p-12 text-center border border-zinc-800 rounded-xl bg-zinc-900/50 flex flex-col items-center">
          <Activity className="h-8 w-8 animate-pulse text-zinc-400 mb-4" />
          <p className="text-zinc-400 font-mono text-sm">Executing authorized recovery actions...</p>
        </div>
      )}

      {error && (
        <div className="p-4 bg-red-950/50 border border-red-900 text-red-400 rounded-lg flex items-center gap-2">
          <AlertTriangle className="h-5 w-5" />
          {error}
        </div>
      )}

      {results && !loading && (
        <div className="space-y-6">
          <h2 className="text-xl font-bold text-white">Execution Results</h2>
          <div className="grid grid-cols-1 gap-4">
            {results.map((res, i) => (
              <div key={res.execution_id || i} className="p-6 bg-zinc-900/50 border border-zinc-800 rounded-xl space-y-4">
                <div className="flex justify-between items-start">
                  <div className="flex items-center gap-3">
                    {res.status === 'succeeded' ? (
                      <CheckCircle2 className="h-6 w-6 text-emerald-500" />
                    ) : res.status === 'failed' ? (
                      <AlertTriangle className="h-6 w-6 text-red-500" />
                    ) : (
                      <Activity className="h-6 w-6 text-blue-500" />
                    )}
                    <div>
                      <h3 className="text-lg font-semibold text-white capitalize">{res.status}</h3>
                      <p className="text-sm font-mono text-zinc-500">Exec ID: {res.execution_id}</p>
                    </div>
                  </div>
                  
                  <span className={`px-2 py-1 rounded text-xs font-bold uppercase tracking-wider ${
                    res.status === 'succeeded' ? 'bg-emerald-950/30 text-emerald-400 border border-emerald-900/50' : 
                    res.status === 'failed' ? 'bg-red-950/30 text-red-400 border border-red-900/50' :
                    'bg-blue-950/30 text-blue-400 border border-blue-900/50'
                  }`}>
                    {res.status}
                  </span>
                </div>

                {res.error_message && (
                  <div className="p-3 bg-red-950/20 border border-red-900/30 rounded text-sm text-red-300 font-mono">
                    {res.error_message}
                  </div>
                )}
                
                <div className="pt-4 border-t border-zinc-800 flex items-center gap-4 text-sm text-zinc-400">
                  <span>Started: {new Date(res.started_at).toLocaleString()}</span>
                  {res.completed_at && <span>Completed: {new Date(res.completed_at).toLocaleString()}</span>}
                </div>
              </div>
            ))}
          </div>

          <div className="mt-8 flex justify-end">
            <Link href="/verification" className="px-6 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-md font-medium transition-colors flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4" /> Proceed to Verification
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}
