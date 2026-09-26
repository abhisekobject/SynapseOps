'use client';

import { Activity, CheckCircle2, ShieldAlert } from 'lucide-react';
import Link from 'next/link';

export default function VerificationPage() {
  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-white mb-2 flex items-center gap-3">
          <CheckCircle2 className="h-8 w-8 text-emerald-500" />
          Verification Center
        </h1>
        <p className="text-zinc-400">Continuous telemetry-based verification of recovery outcomes.</p>
      </div>

      <div className="p-12 text-center border border-zinc-800 rounded-xl bg-zinc-900/50">
        <ShieldAlert className="h-12 w-12 text-zinc-500 mx-auto mb-4" />
        <h2 className="text-xl font-semibold text-white mb-2">No Active Verifications</h2>
        <p className="text-zinc-400 mb-6 max-w-md mx-auto">
          Verification routines run automatically following plan execution. No active verification monitors are running.
        </p>
        <Link 
          href="/events"
          className="inline-block px-6 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-md font-medium transition-colors"
        >
          View System Events
        </Link>
      </div>

      <div className="p-4 bg-blue-950/20 border border-blue-900/50 rounded-lg text-sm text-blue-200">
        <strong>Backend Authority:</strong> Verification in SynapseOps is conducted autonomously by the Verification Engine against active telemetry. The dashboard reflects the results of verification via updated Incident and Event states.
      </div>
    </div>
  );
}
