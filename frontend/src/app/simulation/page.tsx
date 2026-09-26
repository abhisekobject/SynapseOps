'use client';

import { useEffect, useState } from 'react';
import { api } from '@/lib/api/client';
import { DependencyGraphData } from '@/lib/api/types';
import { TestTube, Play, Square, Activity, AlertTriangle, ShieldAlert } from 'lucide-react';
import Link from 'next/link';

export default function SimulationPage() {
  const [graph, setGraph] = useState<DependencyGraphData | null>(null);
  const [activeFailures, setActiveFailures] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  
  const [selectedService, setSelectedService] = useState<string>('gateway');
  const [selectedFailure, setSelectedFailure] = useState<string>('crash');
  const [isInjecting, setIsInjecting] = useState(false);

  const failureTypes = [
    { id: 'crash', name: 'Service Crash', desc: 'Service becomes completely unresponsive' },
    { id: 'cpu_pressure', name: 'CPU Pressure', desc: 'Simulates high CPU utilization' },
    { id: 'memory_pressure', name: 'Memory Pressure', desc: 'Reports escalating memory usage' },
    { id: 'latency', name: 'Network Latency', desc: 'Adds artificial delay to every request' },
    { id: 'error_rate_spike', name: 'Error Rate Spike', desc: 'Returns HTTP 500 for a % of requests' },
    { id: 'network_partition', name: 'Network Partition', desc: 'Cannot reach downstream dependencies' },
  ];

  const fetchData = async () => {
    try {
      const [graphData, failuresData] = await Promise.all([
        api.getDependencies(),
        api.getActiveFailures()
      ]);
      setGraph(graphData);
      setActiveFailures(failuresData);
      if (graphData.nodes.length > 0 && !selectedService) {
        setSelectedService(graphData.nodes[0] || 'gateway');
      }
    } catch (error) {
      console.error("Failed to load simulation data", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleInject = async () => {
    if (!selectedService || !selectedFailure) return;
    setIsInjecting(true);
    try {
      await api.injectFailure(selectedService, selectedFailure);
      await fetchData();
    } catch (e) {
      console.error("Injection failed", e);
      alert("Failed to inject failure. Check console.");
    } finally {
      setIsInjecting(false);
    }
  };

  const handleClear = async (service: string, failure: string) => {
    try {
      await api.clearFailure(service, failure);
      await fetchData();
    } catch (e) {
      console.error("Clear failed", e);
    }
  };

  if (loading && !graph) {
    return (
      <div className="p-8 flex items-center justify-center min-h-screen">
        <div className="text-zinc-400 flex items-center gap-2">
          <Activity className="h-5 w-5 animate-pulse" />
          Loading Simulation Control...
        </div>
      </div>
    );
  }

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-white mb-2 flex items-center gap-3">
          <TestTube className="h-8 w-8 text-blue-500" />
          Simulation Control
        </h1>
        <p className="text-zinc-400">Inject controlled failures to train models and verify recovery routines.</p>
      </div>

      <div className="bg-red-950/20 border border-red-900/50 p-4 rounded-lg flex gap-3 text-red-200">
        <ShieldAlert className="h-5 w-5 flex-shrink-0 mt-0.5 text-red-500" />
        <div className="text-sm">
          <p className="font-bold mb-1">Testing Environment Active</p>
          <p className="text-red-300">
            Failures injected here will trigger real anomalies and incidents in the system. The autonomous recovery engine will attempt to detect and resolve them.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        
        {/* Inject Failure Form */}
        <div className="p-6 bg-zinc-900/50 border border-zinc-800 rounded-xl space-y-6">
          <h2 className="text-xl font-bold text-white">Inject Failure</h2>
          
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-zinc-400 mb-2">Target Service</label>
              <select 
                value={selectedService} 
                onChange={e => setSelectedService(e.target.value)}
                className="w-full bg-zinc-950 border border-zinc-700 rounded-md p-3 text-zinc-200 focus:outline-none focus:border-blue-500"
              >
                {graph?.nodes.map(node => (
                  <option key={node} value={node}>{node}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-zinc-400 mb-2">Failure Profile</label>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {failureTypes.map(ft => (
                  <div 
                    key={ft.id}
                    onClick={() => setSelectedFailure(ft.id)}
                    className={`p-3 rounded-lg border cursor-pointer transition-colors ${
                      selectedFailure === ft.id ? 'bg-blue-900/20 border-blue-500/50' : 'bg-zinc-950 border-zinc-800 hover:border-zinc-700'
                    }`}
                  >
                    <p className={`font-semibold text-sm ${selectedFailure === ft.id ? 'text-blue-400' : 'text-zinc-300'}`}>
                      {ft.name}
                    </p>
                    <p className="text-xs text-zinc-500 mt-1">{ft.desc}</p>
                  </div>
                ))}
              </div>
            </div>
            
            <div className="pt-4">
              <button 
                onClick={handleInject}
                disabled={isInjecting || !selectedService}
                className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-red-600 hover:bg-red-700 text-white rounded-md font-medium transition-colors disabled:opacity-50"
              >
                {isInjecting ? (
                  <><Activity className="h-4 w-4 animate-spin" /> Injecting...</>
                ) : (
                  <><Play className="h-4 w-4" /> Execute Injection</>
                )}
              </button>
            </div>
          </div>
        </div>

        {/* Active Failures List */}
        <div className="p-6 bg-zinc-900/50 border border-zinc-800 rounded-xl space-y-6">
          <div className="flex justify-between items-center">
            <h2 className="text-xl font-bold text-white">Active Injections</h2>
            <Link href="/infrastructure" className="text-sm text-blue-400 hover:text-blue-300">View Telemetry</Link>
          </div>
          
          {activeFailures.length === 0 ? (
            <div className="p-8 text-center border border-zinc-800 border-dashed rounded-xl text-zinc-500">
              No active failures in the system.
            </div>
          ) : (
            <div className="space-y-3">
              {activeFailures.map((f, i) => (
                <div key={i} className="p-4 bg-zinc-950 border border-red-900/30 rounded-lg flex justify-between items-center">
                  <div className="flex items-center gap-3">
                    <AlertTriangle className="h-5 w-5 text-red-500" />
                    <div>
                      <p className="font-bold text-zinc-200">{f.target_service}</p>
                      <p className="text-xs text-red-400 uppercase tracking-wider font-mono mt-1">{f.failure_type}</p>
                    </div>
                  </div>
                  
                  <button 
                    onClick={() => handleClear(f.target_service, f.failure_type)}
                    className="p-2 hover:bg-zinc-800 rounded-md text-zinc-400 hover:text-white transition-colors"
                    title="Clear Failure"
                  >
                    <Square className="h-5 w-5" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

      </div>
    </div>
  );
}
