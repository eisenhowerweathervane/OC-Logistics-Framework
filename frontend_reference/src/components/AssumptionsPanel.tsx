import React from 'react';
import { ChevronDown, ChevronUp, Info } from 'lucide-react';
import { Assumptions } from '../types';

interface Props {
  assumptions: Assumptions;
  setAssumptions: (a: Assumptions) => void;
  isOpen: boolean;
  setIsOpen: (o: boolean) => void;
}

export default function AssumptionsPanel({ assumptions, setAssumptions, isOpen, setIsOpen }: Props) {
  const handleChange = (key: keyof Assumptions, value: number) => {
    setAssumptions({ ...assumptions, [key]: value });
  };

  const fuelCpm = assumptions.fuelPrice / assumptions.mpg;
  const totalCpm = fuelCpm + assumptions.driverPay + assumptions.truckLease + assumptions.insurance + assumptions.maintReserve + assumptions.overhead;
  const floorRpm = totalCpm / (1 - assumptions.minMargin / 100) / (1 - assumptions.factoringFee / 100);

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden mb-6">
      <button 
        onClick={() => setIsOpen(!isOpen)}
        className="w-full px-6 py-4 flex items-center justify-between hover:bg-slate-800/50 transition-colors"
      >
        <div className="flex items-center gap-3">
          <h2 className="text-lg font-semibold text-white">Operating Assumptions</h2>
          <div className="px-3 py-1 bg-amber-500/10 border border-amber-500/20 rounded-full">
            <span className="text-xs font-bold text-amber-500 uppercase tracking-wider">
              Dynamic Floor: ${floorRpm.toFixed(2)}/mi
            </span>
          </div>
        </div>
        {isOpen ? <ChevronUp className="text-slate-400" /> : <ChevronDown className="text-slate-400" />}
      </button>

      {isOpen && (
        <div className="px-6 pb-6 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 border-t border-slate-800 pt-6">
          <div className="space-y-4">
            <h3 className="text-xs font-bold text-slate-500 uppercase tracking-widest">Fuel & Efficiency</h3>
            <Input label="Fuel Price ($/gal)" value={assumptions.fuelPrice} onChange={(v) => handleChange('fuelPrice', v)} step={0.01} />
            <Input label="MPG" value={assumptions.mpg} onChange={(v) => handleChange('mpg', v)} step={0.1} />
          </div>

          <div className="space-y-4">
            <h3 className="text-xs font-bold text-slate-500 uppercase tracking-widest">Fixed Costs ($/mi)</h3>
            <Input label="Driver Pay" value={assumptions.driverPay} onChange={(v) => handleChange('driverPay', v)} step={0.01} />
            <Input label="Truck Lease" value={assumptions.truckLease} onChange={(v) => handleChange('truckLease', v)} step={0.01} />
            <Input label="Insurance" value={assumptions.insurance} onChange={(v) => handleChange('insurance', v)} step={0.01} />
            <Input label="Overhead" value={assumptions.overhead} onChange={(v) => handleChange('overhead', v)} step={0.01} />
          </div>

          <div className="space-y-4">
            <h3 className="text-xs font-bold text-slate-500 uppercase tracking-widest">Business Rules</h3>
            <Input label="Factoring Fee (%)" value={assumptions.factoringFee} onChange={(v) => handleChange('factoringFee', v)} step={0.1} />
            <Input label="Min Margin (%)" value={assumptions.minMargin} onChange={(v) => handleChange('minMargin', v)} step={1} />
            <Input label="Target Margin (%)" value={assumptions.targetMargin} onChange={(v) => handleChange('targetMargin', v)} step={1} />
            <Input label="Max Deadhead (%)" value={assumptions.maxDeadhead} onChange={(v) => handleChange('maxDeadhead', v)} step={1} />
          </div>

          <div className="space-y-4">
            <h3 className="text-xs font-bold text-slate-500 uppercase tracking-widest">Operations</h3>
            <Input label="Avg Speed (mph)" value={assumptions.avgSpeed} onChange={(v) => handleChange('avgSpeed', v)} step={1} />
            <Input label="Load/Unload (hrs)" value={assumptions.loadUnloadTime} onChange={(v) => handleChange('loadUnloadTime', v)} step={0.5} />
            <Input label="Detention Rate ($/hr)" value={assumptions.detentionRate} onChange={(v) => handleChange('detentionRate', v)} step={5} />
          </div>
        </div>
      )}
    </div>
  );
}

function Input({ label, value, onChange, step = 1 }: { label: string; value: number; onChange: (v: number) => void; step?: number }) {
  return (
    <div className="space-y-1.5">
      <label className="block text-xs font-medium text-slate-400">{label}</label>
      <input 
        type="number" 
        value={value} 
        onChange={(e) => onChange(parseFloat(e.target.value) || 0)}
        step={step}
        className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-amber-500 transition-colors"
      />
    </div>
  );
}
