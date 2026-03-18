import React, { useState } from 'react';
import { updateLoadOutcome, submitLoadFeedback } from '../services/api';
import { LoadFeedback } from '../types';
import { X, Check, XCircle, Clock, SkipForward, MessageSquare } from 'lucide-react';

interface LoadFeedbackModalProps {
  isOpen: boolean;
  onClose: () => void;
  load: any;
  onFeedbackSubmitted: () => void;
}

type Outcome = 'booked' | 'passed' | 'expired' | 'skipped' | null;

const OUTCOME_OPTIONS: { key: Outcome; label: string; icon: React.ReactNode; color: string }[] = [
  { key: 'booked',  label: 'Booked',  icon: <Check size={18} />,       color: 'bg-emerald-600 hover:bg-emerald-500 text-white' },
  { key: 'passed',  label: 'Passed',  icon: <XCircle size={18} />,     color: 'bg-red-600 hover:bg-red-500 text-white' },
  { key: 'expired', label: 'Expired', icon: <Clock size={18} />,       color: 'bg-orange-600 hover:bg-orange-500 text-white' },
  { key: 'skipped', label: 'Skipped', icon: <SkipForward size={18} />, color: 'bg-slate-600 hover:bg-slate-500 text-white' },
];

export default function LoadFeedbackModal({ isOpen, onClose, load, onFeedbackSubmitted }: LoadFeedbackModalProps) {
  const [outcome, setOutcome] = useState<Outcome>(null);
  const [actualDwellHours, setActualDwellHours] = useState(0);
  const [actualRatePaid, setActualRatePaid] = useState(load?.rate ?? 0);
  const [actualTollCost, setActualTollCost] = useState(0);
  const [detentionHours, setDetentionHours] = useState(0);
  const [ontimePickup, setOntimePickup] = useState(true);
  const [issues, setIssues] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);

  if (!isOpen) return null;

  const handleOutcomeSelect = async (selected: Outcome) => {
    if (!selected) return;
    setOutcome(selected);

    if (selected !== 'booked') {
      setSubmitting(true);
      try {
        await updateLoadOutcome(load.id, selected);
        setSuccess(true);
        setTimeout(() => {
          onFeedbackSubmitted();
          onClose();
        }, 1500);
      } catch {
        setSubmitting(false);
      }
    }
  };

  const handleSubmitFeedback = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await updateLoadOutcome(load.id, 'booked');
      const feedback: LoadFeedback = {
        actualDwellHours,
        actualRatePaid,
        actualTollCost,
        detentionHours,
        ontimePickup,
        issues,
      };
      await submitLoadFeedback(load.id, feedback);
      setSuccess(true);
      setTimeout(() => {
        onFeedbackSubmitted();
        onClose();
      }, 1500);
    } catch {
      setSubmitting(false);
    }
  };

  if (success) {
    return (
      <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
        <div className="absolute inset-0 bg-black/80 backdrop-blur-sm" />
        <div className="relative bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-md shadow-2xl p-10 text-center">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-emerald-500/20 mb-4">
            <Check size={32} className="text-emerald-400" />
          </div>
          <h3 className="text-xl font-bold text-white mb-1">Feedback Submitted</h3>
          <p className="text-slate-400 text-sm">Load outcome recorded successfully.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/80 backdrop-blur-sm" onClick={onClose} />

      <div className="relative bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-2xl shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between">
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <MessageSquare size={20} className="text-amber-400" />
            Load Feedback
          </h2>
          <button onClick={onClose} className="text-slate-500 hover:text-white transition-colors">
            <X size={24} />
          </button>
        </div>

        <div className="p-6 space-y-6">
          {/* Outcome Selection */}
          <div className="space-y-3">
            <label className="text-xs font-bold text-slate-500 uppercase tracking-widest">
              How did this load go?
            </label>
            <div className="grid grid-cols-4 gap-3">
              {OUTCOME_OPTIONS.map((opt) => (
                <button
                  key={opt.key}
                  type="button"
                  disabled={submitting}
                  onClick={() => handleOutcomeSelect(opt.key)}
                  className={`flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg text-sm font-bold transition-all ${
                    outcome === opt.key
                      ? opt.color + ' ring-2 ring-white/30'
                      : 'bg-slate-800 text-slate-400 hover:text-white hover:bg-slate-700'
                  }`}
                >
                  {opt.icon}
                  <span>{opt.label}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Feedback Form — only when booked */}
          {outcome === 'booked' && (
            <form onSubmit={handleSubmitFeedback} className="space-y-6">
              <div className="pt-4 border-t border-slate-800">
                <label className="text-xs font-bold text-slate-500 uppercase tracking-widest">
                  Post-Load Details
                </label>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <NumericInput label="Actual Dwell Time (hours)" value={actualDwellHours} onChange={setActualDwellHours} step={0.5} />
                <NumericInput label="Actual Rate Paid ($)" value={actualRatePaid} onChange={setActualRatePaid} />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <NumericInput label="Actual Toll Cost ($)" value={actualTollCost} onChange={setActualTollCost} />
                <NumericInput label="Detention Hours" value={detentionHours} onChange={setDetentionHours} step={0.5} />
              </div>

              {/* On-Time Pickup toggle */}
              <div className="space-y-2">
                <label className="text-xs font-bold text-slate-500 uppercase tracking-widest">On-Time Pickup?</label>
                <div className="flex gap-3">
                  <button
                    type="button"
                    onClick={() => setOntimePickup(true)}
                    className={`px-6 py-2 rounded-lg text-sm font-bold transition-all ${
                      ontimePickup
                        ? 'bg-emerald-600 text-white ring-2 ring-emerald-400/40'
                        : 'bg-slate-800 text-slate-400 hover:text-white hover:bg-slate-700'
                    }`}
                  >
                    Yes
                  </button>
                  <button
                    type="button"
                    onClick={() => setOntimePickup(false)}
                    className={`px-6 py-2 rounded-lg text-sm font-bold transition-all ${
                      !ontimePickup
                        ? 'bg-red-600 text-white ring-2 ring-red-400/40'
                        : 'bg-slate-800 text-slate-400 hover:text-white hover:bg-slate-700'
                    }`}
                  >
                    No
                  </button>
                </div>
              </div>

              {/* Issues / Notes */}
              <div className="space-y-2">
                <label className="text-xs font-bold text-slate-500 uppercase tracking-widest">Issues / Notes</label>
                <textarea
                  value={issues}
                  onChange={(e) => setIssues(e.target.value)}
                  rows={3}
                  placeholder="Any issues, delays, or notes about this load..."
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg px-4 py-2.5 text-white placeholder-slate-600 focus:outline-none focus:ring-2 focus:ring-amber-500 focus:border-amber-500 resize-none"
                />
              </div>

              {/* Submit */}
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
                  disabled={submitting}
                  className="px-8 py-2.5 bg-amber-500 rounded-lg text-sm font-black text-black hover:bg-amber-400 transition-all flex items-center gap-2 disabled:opacity-50"
                >
                  <Check size={18} />
                  <span>SUBMIT FEEDBACK</span>
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}

function NumericInput({ label, value, onChange, step = 1 }: { label: string; value: number; onChange: (v: number) => void; step?: number }) {
  return (
    <div className="space-y-2">
      <label className="text-xs font-bold text-slate-500 uppercase tracking-widest">{label}</label>
      <input
        type="number"
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value) || 0)}
        step={step}
        className="w-full bg-slate-950 border border-slate-700 rounded-lg px-4 py-2.5 text-white focus:outline-none focus:ring-2 focus:ring-amber-500 focus:border-amber-500"
      />
    </div>
  );
}
