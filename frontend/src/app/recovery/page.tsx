'use client';

import { useState } from 'react';
import { api } from '@/lib/api/client';
import { RecoveryPlan, PolicyDecision, ApprovalRequestResponse } from '@/lib/api/types';
import { ShieldCheck, Activity, AlertTriangle, PlaySquare, FileCheck } from 'lucide-react';
import Link from 'next/link';

export default function RecoveryPage() {
  const [plan, setPlan] = useState<RecoveryPlan | null>(null);
  const [policy, setPolicy] = useState<PolicyDecision | null>(null);
  const [approval, setApproval] = useState<ApprovalRequestResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const generatePlan = async () => {
    setLoading(true);
    setError(null);
    try {
      const reasoning = await api.getIncidentReasoning();
      const generatedPlan = await api.createRecoveryPlan(reasoning);
      setPlan(generatedPlan);
      
      const evalPolicy = await api.evaluatePolicy(generatedPlan);
      setPolicy(evalPolicy);
    } catch (e: any) {
      setError(e.message || "Failed to generate plan");
    } finally {
      setLoading(false);
    }
  };

  const requestApproval = async () => {
    if (!plan) return;
    setLoading(true);
    try {
      const app = await api.requestApproval(plan);
      setApproval(app);
    } catch (e: any) {
      setError(e.message || "Failed to request approval");
    } finally {
      setLoading(false);
    }
  };

  const approvePlan = async () => {
    if (!plan || !approval) return;
    setLoading(true);
    try {
      const updated = await api.approvePlan(approval.approval_id, plan);
      setApproval(updated);
    } catch (e: any) {
      setError(e.message || "Failed to approve plan");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-white mb-2 flex items-center gap-3">
          <ShieldCheck className="h-8 w-8 text-blue-500" />
          Recovery & Safety Operations
        </h1>
        <p className="text-zinc-400">View, evaluate, and authorize recovery plans.</p>
      </div>

      {!plan && !loading && (
        <div className="p-12 text-center border border-zinc-800 rounded-xl bg-zinc-900/50">
          <ShieldCheck className="h-12 w-12 text-blue-500 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-white mb-2">No Active Plan</h2>
          <p className="text-zinc-400 mb-6 max-w-md mx-auto">
            Generate a recovery plan from the latest AI incident reasoning to begin the safety and authorization workflow.
          </p>
          <button 
            onClick={generatePlan}
            className="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md font-medium transition-colors"
          >
            Generate Recovery Plan
          </button>
        </div>
      )}

      {loading && (
        <div className="p-12 text-center border border-zinc-800 rounded-xl bg-zinc-900/50 flex flex-col items-center">
          <Activity className="h-8 w-8 animate-pulse text-zinc-400 mb-4" />
          <p className="text-zinc-400">Processing safety operation...</p>
        </div>
      )}

      {error && (
        <div className="p-4 bg-red-950/50 border border-red-900 text-red-400 rounded-lg flex items-center gap-2">
          <AlertTriangle className="h-5 w-5" />
          {error}
        </div>
      )}

      {plan && !loading && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          
          <div className="space-y-6">
            <div className="p-6 bg-zinc-900/50 border border-zinc-800 rounded-xl">
              <div className="flex justify-between items-start mb-6">
                <h2 className="text-xl font-bold text-white">Recovery Plan</h2>
                <span className={`px-2 py-1 rounded text-xs font-bold uppercase tracking-wider ${
                  plan.risk_classification?.level === 'critical' || plan.risk_classification?.level === 'high' ? 'bg-red-950/50 text-red-400 border border-red-900/50' : 
                  'bg-blue-950/50 text-blue-400 border border-blue-900/50'
                }`}>
                  Risk: {plan.risk_classification?.level || 'unknown'}
                </span>
              </div>
              
              <div className="space-y-4">
                <div>
                  <span className="text-xs text-zinc-500 uppercase font-semibold tracking-wider">Target Component</span>
                  <p className="text-lg font-mono text-zinc-200">{plan.target_service}</p>
                </div>
                <div>
                  <span className="text-xs text-zinc-500 uppercase font-semibold tracking-wider">Action</span>
                  <p className="text-lg font-mono text-zinc-200 capitalize">{plan.action?.action_type?.replace('_', ' ') ?? 'N/A'}</p>
                </div>
                
                <div className="pt-4 border-t border-zinc-800">
                  <span className="text-xs text-zinc-500 uppercase font-semibold tracking-wider mb-2 block">Blast Radius</span>
                  <p className="text-sm text-zinc-300">{plan.risk_classification?.blast_radius || 'Unknown'}</p>
                </div>

                <div className="pt-4 border-t border-zinc-800">
                  <span className="text-xs text-zinc-500 uppercase font-semibold tracking-wider mb-2 block">Verification Conditions</span>
                  <ul className="space-y-2">
                    {(plan.verification_conditions || []).map((vc, i) => (
                      <li key={i} className="text-sm text-zinc-400 font-mono bg-zinc-950 p-2 rounded border border-zinc-800">
                        {vc.metric} {vc.operator} {vc.target_value} (Timeout: {vc.timeout_seconds}s)
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>
          </div>

          <div className="space-y-6">
            {policy && (
              <div className="p-6 bg-zinc-900/50 border border-zinc-800 rounded-xl space-y-4">
                <h2 className="text-lg font-bold text-white flex items-center gap-2">
                  <FileCheck className="h-5 w-5 text-emerald-500" />
                  Policy Evaluation
                </h2>
                
                <div className="flex items-center gap-3 p-4 rounded-lg bg-zinc-950 border border-zinc-800">
                  <span className="text-sm font-medium text-zinc-400">Decision:</span>
                  <span className={`text-sm font-bold uppercase tracking-wider ${
                    policy.decision === 'allow' ? 'text-emerald-400' :
                    policy.decision === 'deny' ? 'text-red-400' : 'text-amber-400'
                  }`}>
                    {policy.decision.replace('_', ' ')}
                  </span>
                </div>

                <ul className="space-y-2">
                  {policy.reasons.map((r, i) => (
                    <li key={i} className="text-sm text-zinc-400 flex items-center gap-2">
                      <div className="h-1.5 w-1.5 rounded-full bg-zinc-500" />
                      {r}
                    </li>
                  ))}
                </ul>

                {!approval && policy.decision === 'requires_approval' && (
                  <button 
                    onClick={requestApproval}
                    className="w-full mt-4 px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white rounded-md font-medium transition-colors"
                  >
                    Request Authorization
                  </button>
                )}
                
                {!approval && policy.decision === 'allow' && (
                  <Link href={`/execution?plan=${plan.plan_id}`} className="block text-center w-full mt-4 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-md font-medium transition-colors">
                    Proceed to Execution
                  </Link>
                )}
              </div>
            )}

            {approval && (
              <div className="p-6 bg-zinc-900/50 border border-zinc-800 rounded-xl space-y-4">
                <h2 className="text-lg font-bold text-white flex items-center gap-2">
                  <ShieldCheck className="h-5 w-5 text-purple-500" />
                  Authorization Status
                </h2>
                
                <div className="flex items-center gap-3 p-4 rounded-lg bg-zinc-950 border border-zinc-800">
                  <span className="text-sm font-medium text-zinc-400">Status:</span>
                  <span className={`text-sm font-bold uppercase tracking-wider ${
                    approval.status === 'approved' ? 'text-emerald-400' :
                    approval.status === 'rejected' ? 'text-red-400' : 'text-amber-400'
                  }`}>
                    {approval.status}
                  </span>
                </div>

                {approval.status === 'pending' && (
                  <div className="pt-4 space-y-3">
                    <p className="text-xs text-amber-500 uppercase font-semibold">Separation of Duties Active</p>
                    <p className="text-sm text-zinc-300">
                      As <span className="font-mono bg-zinc-800 px-1">synapse.admin</span>, you can approve this request.
                    </p>
                    <button 
                      onClick={approvePlan}
                      className="w-full px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-md font-medium transition-colors"
                    >
                      Authorize Plan Execution
                    </button>
                  </div>
                )}

                {approval.status === 'approved' && (
                  <div className="pt-4">
                    <Link href={`/execution?approval_id=${approval.approval_id}`} className="block text-center w-full px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md font-medium transition-colors flex items-center justify-center gap-2">
                      <PlaySquare className="h-4 w-4" /> Go to Execution Center
                    </Link>
                  </div>
                )}
              </div>
            )}
          </div>

        </div>
      )}
    </div>
  );
}
