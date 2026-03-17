import React from 'react';
import { Truck, Clock, Play, Plus, RefreshCw } from 'lucide-react';
import { CITIES } from '../constants';

interface Props {
  truckLocation: string;
  setTruckLocation: (l: string) => void;
  hosRemaining: number;
  setHosRemaining: (h: number) => void;
  daysAway: number;
  setDaysAway: (d: number) => void;
  homeBase: string;
  setHomeBase: (h: string) => void;
  onRunOptimizer: () => void;
  onAddLoad: () => void;
  onGenerateLoads: () => void;
}

export default function ControlBar({ 
  truckLocation, setTruckLocation, 
  hosRemaining, setHosRemaining, 
  daysAway, setDaysAway,
  homeBase, setHomeBase,
  onRunOptimizer, onAddLoad, onGenerateLoads 
}: Props) {
  return (
    <div className="sticky top-0 z-50 bg-slate-950/80 backdrop-blur-md border-b border-slate-800 px-6 py-4 flex flex-wrap items-center justify-between gap-4">
      <div className="flex items-center gap-8">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-amber-500 rounded-lg flex items-center justify-center">
            <Truck className="text-black" size={24} />
          </div>
          <div>
            <h1 className="text-xl font-black text-white tracking-tighter uppercase font-display">Stratus</h1>
            <p className="text-[10px] font-bold text-amber-500 tracking-[0.2em] uppercase leading-none">Intelligence</p>
          </div>
        </div>

        <div className="h-8 w-px bg-slate-800 hidden md:block" />

        <div className="flex items-center gap-6">
          <div className="space-y-1">
            <label className="block text-[10px] font-bold text-slate-500 uppercase tracking-widest">Truck Location</label>
            <select 
              value={truckLocation}
              onChange={(e) => setTruckLocation(e.target.value)}
              className="bg-transparent text-sm font-semibold text-white focus:outline-none cursor-pointer"
            >
              {CITIES.map(c => <option key={c.name} value={c.name} className="bg-slate-900">{c.name}</option>)}
            </select>
          </div>

          <div className="space-y-1">
            <label className="block text-[10px] font-bold text-slate-500 uppercase tracking-widest">HOS Remaining</label>
            <div className="flex items-center gap-2">
              <Clock size={14} className="text-slate-400" />
              <input 
                type="number" 
                value={hosRemaining}
                onChange={(e) => setHosRemaining(parseFloat(e.target.value) || 0)}
                step={0.5}
                min={0}
                max={14}
                className="bg-transparent w-12 text-sm font-semibold text-white focus:outline-none"
              />
              <span className="text-[10px] font-bold text-slate-500 uppercase">hrs</span>
            </div>
          </div>

          <div className="space-y-1">
            <label className="block text-[10px] font-bold text-slate-500 uppercase tracking-widest">Days Away</label>
            <select 
              value={daysAway}
              onChange={(e) => setDaysAway(parseInt(e.target.value))}
              className="bg-transparent text-sm font-semibold text-white focus:outline-none cursor-pointer"
            >
              {[0, 1, 2, 3, 4, 5].map(d => (
                <option key={d} value={d} className="bg-slate-900">
                  {d === 0 ? 'Return Today' : `${d} Night${d > 1 ? 's' : ''} Out`}
                </option>
              ))}
            </select>
          </div>

          <div className="space-y-1">
            <label className="block text-[10px] font-bold text-slate-500 uppercase tracking-widest">Home Base</label>
            <select 
              value={homeBase}
              onChange={(e) => setHomeBase(e.target.value)}
              className="bg-transparent text-sm font-semibold text-white focus:outline-none cursor-pointer"
            >
              {CITIES.map(c => <option key={c.name} value={c.name} className="bg-slate-900">{c.name}</option>)}
            </select>
          </div>
        </div>
      </div>

      <div className="flex items-center gap-3">
        <button 
          onClick={onGenerateLoads}
          className="p-2.5 bg-slate-900 border border-slate-800 rounded-lg text-slate-400 hover:text-white hover:border-slate-700 transition-all"
          title="Generate New Loads"
        >
          <RefreshCw size={20} />
        </button>
        <button 
          onClick={onAddLoad}
          className="flex items-center gap-2 px-4 py-2.5 bg-slate-900 border border-slate-800 rounded-lg text-sm font-bold text-white hover:bg-slate-800 transition-all"
        >
          <Plus size={18} />
          <span>Add Load</span>
        </button>
        <button 
          onClick={onRunOptimizer}
          className="flex items-center gap-2 px-6 py-2.5 bg-amber-500 rounded-lg text-sm font-black text-black hover:bg-amber-400 transition-all shadow-lg shadow-amber-500/20"
        >
          <Play size={18} fill="currentColor" />
          <span>RUN OPTIMIZER</span>
        </button>
      </div>
    </div>
  );
}
