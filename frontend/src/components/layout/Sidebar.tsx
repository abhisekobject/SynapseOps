'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { 
  LayoutDashboard, 
  Server, 
  AlertTriangle, 
  Activity, 
  Network, 
  Brain, 
  ShieldCheck, 
  PlaySquare, 
  CheckCircle2, 
  Database, 
  BookOpen,
  TestTube
} from 'lucide-react';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

const navItems = [
  { name: 'Overview', href: '/', icon: LayoutDashboard },
  { name: 'Infrastructure', href: '/infrastructure', icon: Server },
  { name: 'Events', href: '/events', icon: Activity },
  { name: 'Anomalies', href: '/anomalies', icon: AlertTriangle },
  { name: 'Incidents', href: '/incidents', icon: AlertTriangle },
  { name: 'Dependencies', href: '/dependencies', icon: Network },
  { name: 'AI Reasoning', href: '/reasoning', icon: Brain },
  { name: 'Recovery', href: '/recovery', icon: ShieldCheck },
  { name: 'Execution', href: '/execution', icon: PlaySquare },
  { name: 'Verification', href: '/verification', icon: CheckCircle2 },
  { name: 'Memory', href: '/memory', icon: Database },
  { name: 'Learning', href: '/learning', icon: BookOpen },
  { name: 'Simulation', href: '/simulation', icon: TestTube },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <div className="flex h-full w-64 flex-col bg-zinc-950 border-r border-zinc-800 text-zinc-300">
      <div className="p-6">
        <h1 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
          <Activity className="h-6 w-6 text-emerald-500" />
          SynapseOps
        </h1>
        <p className="text-xs text-zinc-500 mt-1 uppercase tracking-wider font-semibold">Operations Console</p>
      </div>

      <nav className="flex-1 space-y-1 px-3 py-4 overflow-y-auto">
        {navItems.map((item) => {
          const isActive = pathname === item.href || (item.href !== '/' && pathname.startsWith(item.href));
          return (
            <Link
              key={item.name}
              href={item.href}
              className={twMerge(
                clsx(
                  'group flex items-center rounded-md px-3 py-2 text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-zinc-800 text-white'
                    : 'text-zinc-400 hover:bg-zinc-800/50 hover:text-zinc-100'
                )
              )}
            >
              <item.icon
                className={twMerge(
                  clsx(
                    'mr-3 h-5 w-5 flex-shrink-0',
                    isActive ? 'text-zinc-300' : 'text-zinc-500 group-hover:text-zinc-300'
                  )
                )}
                aria-hidden="true"
              />
              {item.name}
            </Link>
          );
        })}
      </nav>
      
      <div className="p-4 border-t border-zinc-800">
        <div className="flex items-center gap-3">
          <div className="h-8 w-8 rounded-full bg-zinc-800 flex items-center justify-center">
            <span className="text-xs font-medium text-zinc-300">OP</span>
          </div>
          <div>
            <p className="text-sm font-medium text-white">System Operator</p>
            <p className="text-xs text-zinc-500">synapse.admin</p>
          </div>
        </div>
      </div>
    </div>
  );
}
