import React, { useState } from 'react';
import { X, Plus } from 'lucide-react';
import { CITIES, COMMODITIES } from '../constants';
import { Load } from '../types';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onAdd: (load: Load) => void;
}

export default function AddLoadModal({ isOpen, onClose, onAdd }: Props) {
  const [origin, setOrigin] = useState(CITIES[0].name);
  const [destination, setDestination] = useState(CITIES[1].name);
  const [miles, setMiles] = useState(250);
  const [rate, setRate] = useState(750);
  const [weight, setWeight] = useState(40000);
  const [commodity, setCommodity] = useState(COMMODITIES[0]);
  const [detentionHours, setDetentionHours] = useState(0);
  const [pickupTime, setPickupTime] = useState(new Date().toISOString().slice(0, 16));
  const [deliveryTime, setDeliveryTime] = useState(new Date(Date.now() + 8 * 3600000).toISOString().slice(0, 16));

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onAdd({
      id: `L-MAN-${Math.random().toString(36).substr(2, 4).toUpperCase()}`,
      origin,
      destination,
      miles,
      rate,
      weight,
      commodity,
      detentionHours,
      pickupWindowStart: new Date(pickupTime).toISOString(),
      deliveryDeadline: new Date(deliveryTime).toISOString()
    });
    onClose();
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/80 backdrop-blur-sm" onClick={onClose} />
      
      <div className="relative bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-2xl shadow-2xl overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between">
          <h2 className="text-xl font-bold text-white">Add Manual Load</h2>
          <button onClick={onClose} className="text-slate-500 hover:text-white transition-colors">
            <X size={24} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-2">
              <label className="text-xs font-bold text-slate-500 uppercase tracking-widest">Origin</label>
              <select 
                value={origin}
                onChange={(e) => setOrigin(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-4 py-2.5 text-white focus:outline-none focus:border-amber-500"
              >
                {CITIES.map(c => <option key={c.name} value={c.name}>{c.name}</option>)}
              </select>
            </div>
            <div className="space-y-2">
              <label className="text-xs font-bold text-slate-500 uppercase tracking-widest">Destination</label>
              <select 
                value={destination}
                onChange={(e) => setDestination(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-4 py-2.5 text-white focus:outline-none focus:border-amber-500"
              >
                {CITIES.map(c => <option key={c.name} value={c.name}>{c.name}</option>)}
              </select>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <Input label="Miles" value={miles} onChange={setMiles} />
            <Input label="Total Rate ($)" value={rate} onChange={setRate} />
            <Input label="Weight (lbs)" value={weight} onChange={setWeight} />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-2">
              <label className="text-xs font-bold text-slate-500 uppercase tracking-widest">Commodity</label>
              <select 
                value={commodity}
                onChange={(e) => setCommodity(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-4 py-2.5 text-white focus:outline-none focus:border-amber-500"
              >
                {COMMODITIES.map(c => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>
            <Input label="Est. Detention (hrs)" value={detentionHours} onChange={setDetentionHours} step={0.5} />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-2">
              <label className="text-xs font-bold text-slate-500 uppercase tracking-widest">Pickup Time</label>
              <input 
                type="datetime-local" 
                value={pickupTime}
                onChange={(e) => setPickupTime(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-4 py-2.5 text-white focus:outline-none focus:border-amber-500"
              />
            </div>
            <div className="space-y-2">
              <label className="text-xs font-bold text-slate-500 uppercase tracking-widest">Delivery Deadline</label>
              <input 
                type="datetime-local" 
                value={deliveryTime}
                onChange={(e) => setDeliveryTime(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-4 py-2.5 text-white focus:outline-none focus:border-amber-500"
              />
            </div>
          </div>

          <div className="pt-6 border-t border-slate-800 flex justify-end gap-3">
            <button 
              type="button"
              onClick={onClose}
              className="px-6 py-2.5 rounded-lg text-sm font-bold text-slate-400 hover:text-white transition-colors"
            >
              Cancel
            </button>
            <button 
              type="submit"
              className="px-8 py-2.5 bg-amber-500 rounded-lg text-sm font-black text-black hover:bg-amber-400 transition-all flex items-center gap-2"
            >
              <Plus size={18} />
              <span>ADD LOAD</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function Input({ label, value, onChange, step = 1 }: { label: string; value: number; onChange: (v: number) => void; step?: number }) {
  return (
    <div className="space-y-2">
      <label className="text-xs font-bold text-slate-500 uppercase tracking-widest">{label}</label>
      <input 
        type="number" 
        value={value} 
        onChange={(e) => onChange(parseFloat(e.target.value) || 0)}
        step={step}
        className="w-full bg-slate-950 border border-slate-800 rounded-lg px-4 py-2.5 text-white focus:outline-none focus:border-amber-500"
      />
    </div>
  );
}
