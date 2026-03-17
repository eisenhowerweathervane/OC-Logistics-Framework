import React from 'react';
import { OptimizedChain } from '../types';
import { Zap, Shield, ArrowUpRight } from 'lucide-react';

interface Props {
  optimized: OptimizedChain | null;
  naive: OptimizedChain | null;
}

export default function ComparisonView({ optimized, naive }: Props) {
  if (!optimized || !naive) return null;

  const profitDelta = Math.round((optimized.summary.totalProfit - naive.summary.totalProfit) * 100) / 100;
  const dhSaved = Math.round(naive.summary.totalDeadhead - optimized.summary.totalDeadhead);
  const loadsDelta = optimized.summary.numLoads - naive.summary.numLoads;

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 mb-12">
      <div className="flex items-center gap-3 mb-6">
        <Zap className="text-amber-500" size={24} />
        <h2 className="text-xl font-bold text-white">Optimization Performance</h2>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
        <DeltaCard 
          label="Extra Daily Profit" 
          value={`$${profitDelta.toLocaleString()}`} 
          subtext="vs. manual dispatch"
          positive={profitDelta > 0}
        />
        <DeltaCard 
          label="Deadhead Saved" 
          value={`${dhSaved} miles`} 
          subtext="less empty driving"
          positive={dhSaved > 0}
        />
        <DeltaCard 
          label="Capacity Efficiency" 
          value={`${loadsDelta > 0 ? '+' : ''}${loadsDelta} Loads`} 
          subtext="extra volume handled"
          positive={loadsDelta >= 0}
        />
      </div>

      <div className="mt-8 pt-8 border-t border-slate-800 grid grid-cols-1 md:grid-cols-2 gap-12">
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-slate-500 uppercase tracking-widest">Optimized Chain</h3>
            <span className="text-xs font-bold text-emerald-500 bg-emerald-500/10 px-2 py-1 rounded">STRATUS AI</span>
          </div>
          <div className="space-y-2">
            <ProgressBar label="Profit" value={optimized.summary.totalProfit} max={Math.max(optimized.summary.totalProfit, naive.summary.totalProfit)} color="bg-emerald-500" />
            <ProgressBar label="Deadhead" value={optimized.summary.totalDeadhead} max={Math.max(optimized.summary.totalDeadhead, naive.summary.totalDeadhead)} color="bg-amber-500" inverse />
          </div>
        </div>

        <div className="space-y-4 opacity-50">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-slate-500 uppercase tracking-widest">Naive Baseline</h3>
            <span className="text-xs font-bold text-slate-400 bg-slate-800 px-2 py-1 rounded">Manual Pick</span>
          </div>
          <div className="space-y-2">
            <ProgressBar label="Profit" value={naive.summary.totalProfit} max={Math.max(optimized.summary.totalProfit, naive.summary.totalProfit)} color="bg-slate-500" />
            <ProgressBar label="Deadhead" value={naive.summary.totalDeadhead} max={Math.max(optimized.summary.totalDeadhead, naive.summary.totalDeadhead)} color="bg-slate-500" inverse />
          </div>
        </div>
      </div>
    </div>
  );
}

function DeltaCard({ label, value, subtext, positive }: { label: string; value: string; subtext: string; positive: boolean }) {
  return (
    <div className="space-y-1">
      <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">{label}</p>
      <div className="flex items-center gap-2">
        <p className={`text-3xl font-black ${positive ? 'text-emerald-500' : 'text-slate-300'}`}>{value}</p>
        {positive && <ArrowUpRight className="text-emerald-500" size={24} />}
      </div>
      <p className="text-xs text-slate-500">{subtext}</p>
    </div>
  );
}

function ProgressBar({ label, value, max, color, inverse }: { label: string; value: number; max: number; color: string; inverse?: boolean }) {
  const pct = max > 0 ? (value / max) * 100 : 0;
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-[10px] font-bold uppercase">
        <span className="text-slate-500">{label}</span>
        <span className="text-white">{value.toLocaleString()}</span>
      </div>
      <div className="h-1.5 bg-slate-800 rounded-full overflow-hidden">
        <div 
          className={`h-full ${color} transition-all duration-1000`} 
          style={{ width: `${pct}%` }} 
        />
      </div>
    </div>
  );
}
