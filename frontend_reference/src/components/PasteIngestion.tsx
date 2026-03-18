import React, { useState } from 'react';
import { ingestPaste, ingestComplete } from '../services/api';
import { ParsedLoadResult } from '../types';
import { ClipboardPaste, AlertTriangle, Check, Loader2, X } from 'lucide-react';

interface PasteIngestionProps {
  onLoadsSaved: () => void;
}

type Phase = 'input' | 'parsing' | 'results' | 'saved';

interface SaveState {
  [index: number]: 'unsaved' | 'saving' | 'saved' | 'error';
}

export default function PasteIngestion({ onLoadsSaved }: PasteIngestionProps) {
  const [phase, setPhase] = useState<Phase>('input');
  const [pasteText, setPasteText] = useState('');
  const [parsedLoads, setParsedLoads] = useState<ParsedLoadResult[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [expandedGapFill, setExpandedGapFill] = useState<Set<number>>(new Set());
  const [gapFills, setGapFills] = useState<Record<number, Record<string, string>>>({});
  const [saveState, setSaveState] = useState<SaveState>({});
  const [savedLoadIds, setSavedLoadIds] = useState<Record<number, string>>({});

  const handleParse = async () => {
    if (!pasteText.trim()) return;

    setError(null);
    setPhase('parsing');

    try {
      const report = await ingestPaste(pasteText);
      setParsedLoads(report.loads);
      setSaveState(
        Object.fromEntries(report.loads.map((_, i) => [i, 'unsaved' as const]))
      );
      setPhase('results');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to parse pasted text');
      setPhase('input');
    }
  };

  const toggleGapFill = (index: number) => {
    setExpandedGapFill(prev => {
      const next = new Set(prev);
      if (next.has(index)) {
        next.delete(index);
      } else {
        next.add(index);
      }
      return next;
    });
  };

  const updateGapFill = (loadIndex: number, field: string, value: string) => {
    setGapFills(prev => ({
      ...prev,
      [loadIndex]: {
        ...(prev[loadIndex] || {}),
        [field]: value,
      },
    }));
  };

  const saveLoad = async (index: number) => {
    const load = parsedLoads[index];
    const fills = gapFills[index] || {};

    setSaveState(prev => ({ ...prev, [index]: 'saving' }));

    try {
      const result = await ingestComplete(load, fills, true);
      setSaveState(prev => ({ ...prev, [index]: 'saved' }));
      setSavedLoadIds(prev => ({ ...prev, [index]: result.loadId || result.id || `#${index + 1}` }));
    } catch {
      setSaveState(prev => ({ ...prev, [index]: 'error' }));
    }
  };

  const saveAll = async () => {
    const indicesToSave = parsedLoads
      .map((load, i) => ({ load, i }))
      .filter(({ load, i }) => saveState[i] === 'unsaved' && !load.duplicateOf);

    const skippedDuplicates = parsedLoads.filter(
      (load, i) => saveState[i] === 'unsaved' && load.duplicateOf
    ).length;

    await Promise.all(indicesToSave.map(({ i }) => saveLoad(i)));

    if (skippedDuplicates > 0) {
      setError(`Saved ${indicesToSave.length} load(s). Skipped ${skippedDuplicates} duplicate(s).`);
    }

    onLoadsSaved();
  };

  const allSaved = parsedLoads.length > 0 && parsedLoads.every((_, i) => saveState[i] === 'saved');

  const handleReset = () => {
    setPhase('input');
    setPasteText('');
    setParsedLoads([]);
    setError(null);
    setExpandedGapFill(new Set());
    setGapFills({});
    setSaveState({});
    setSavedLoadIds({});
  };

  const formatRoute = (load: ParsedLoadResult) => {
    const origin = [load.originCity, load.originState].filter(Boolean).join(', ');
    const dest = [load.destinationCity, load.destinationState].filter(Boolean).join(', ');
    return { origin: origin || 'Unknown', dest: dest || 'Unknown' };
  };

  return (
    <div className="bg-slate-900 rounded-2xl border border-slate-800 overflow-hidden">
      {/* Header */}
      <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-900/50">
        <h2 className="text-lg font-bold text-white flex items-center gap-2">
          <ClipboardPaste size={18} className="text-amber-500" />
          Import Loads from DAT
        </h2>
        {phase !== 'input' && (
          <button
            onClick={handleReset}
            className="text-slate-500 hover:text-white transition-colors"
          >
            <X size={20} />
          </button>
        )}
      </div>

      <div className="p-6 space-y-6">
        {/* Error message */}
        {error && (
          <div className="flex items-center gap-2 px-4 py-3 bg-red-500/10 border border-red-500/30 rounded-lg">
            <AlertTriangle size={16} className="text-red-500 shrink-0" />
            <p className="text-sm text-red-400">{error}</p>
          </div>
        )}

        {/* Step 1: Paste Input */}
        {(phase === 'input' || phase === 'parsing') && (
          <div className="space-y-4">
            <textarea
              value={pasteText}
              onChange={(e) => setPasteText(e.target.value)}
              placeholder="Paste load details from DAT dashboard..."
              rows={8}
              disabled={phase === 'parsing'}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-4 py-3 text-sm text-white placeholder-slate-600 focus:outline-none focus:border-amber-500 resize-y font-mono disabled:opacity-50"
            />
            {!pasteText.trim() && phase === 'input' && (
              <p className="text-xs text-slate-500">
                Paste load details from the DAT dashboard above
              </p>
            )}
            <div className="flex justify-end">
              <button
                onClick={handleParse}
                disabled={!pasteText.trim() || phase === 'parsing'}
                className="px-8 py-2.5 bg-amber-500 rounded-lg text-sm font-black text-black hover:bg-amber-400 transition-all flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {phase === 'parsing' ? (
                  <>
                    <Loader2 size={16} className="animate-spin" />
                    <span>PARSING...</span>
                  </>
                ) : (
                  <>
                    <ClipboardPaste size={16} />
                    <span>PARSE LOADS</span>
                  </>
                )}
              </button>
            </div>
          </div>
        )}

        {/* Step 2: Results */}
        {phase === 'results' && parsedLoads.length === 0 && (
          <div className="text-center py-12">
            <p className="text-slate-500 text-sm">No loads found in pasted text.</p>
          </div>
        )}

        {phase === 'results' && parsedLoads.length > 0 && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <p className="text-xs font-bold text-slate-500 uppercase tracking-widest">
                {parsedLoads.length} Load{parsedLoads.length !== 1 ? 's' : ''} Parsed
              </p>
              {parsedLoads.length > 1 && (
                <button
                  onClick={saveAll}
                  disabled={allSaved}
                  className="px-6 py-2 bg-amber-500 rounded-lg text-xs font-black text-black hover:bg-amber-400 transition-all disabled:opacity-50 disabled:cursor-not-allowed uppercase tracking-widest"
                >
                  {allSaved ? 'ALL SAVED' : 'SAVE ALL'}
                </button>
              )}
            </div>

            {parsedLoads.map((load, index) => {
              const { origin, dest } = formatRoute(load);
              const isGapFillOpen = expandedGapFill.has(index);
              const state = saveState[index] || 'unsaved';

              return (
                <div
                  key={index}
                  className={`bg-slate-950 border rounded-xl p-5 space-y-4 transition-colors ${
                    state === 'saved'
                      ? 'border-emerald-500/40'
                      : load.duplicateOf !== undefined
                      ? 'border-amber-500/40'
                      : 'border-slate-800'
                  }`}
                >
                  {/* Route header */}
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      {state === 'saved' && (
                        <Check size={18} className="text-emerald-500" />
                      )}
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-bold text-white">{origin}</span>
                          <span className="text-slate-600">&rarr;</span>
                          <span className="text-sm font-bold text-white">{dest}</span>
                        </div>
                        {state === 'saved' && savedLoadIds[index] && (
                          <p className="text-[10px] text-emerald-500 font-bold uppercase tracking-widest mt-1">
                            Saved as {savedLoadIds[index]}
                          </p>
                        )}
                      </div>
                    </div>

                    {state !== 'saved' && (
                      <button
                        onClick={() => saveLoad(index)}
                        disabled={state === 'saving'}
                        className="px-4 py-1.5 bg-amber-500 rounded-lg text-[10px] font-black text-black hover:bg-amber-400 transition-all uppercase tracking-widest disabled:opacity-50 flex items-center gap-1.5"
                      >
                        {state === 'saving' ? (
                          <>
                            <Loader2 size={12} className="animate-spin" />
                            <span>SAVING</span>
                          </>
                        ) : (
                          <span>SAVE LOAD</span>
                        )}
                      </button>
                    )}
                  </div>

                  {/* Details row */}
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <DetailItem
                      label="Rate"
                      value={load.rateTotal != null ? `$${load.rateTotal.toLocaleString()}` : null}
                    />
                    <DetailItem
                      label="Mileage"
                      value={load.mileage ? `${load.mileage} mi` : null}
                    />
                    <DetailItem label="Broker" value={load.brokerName || null} />
                    <DetailItem label="Pickup" value={load.pickupDate || null} />
                  </div>

                  {/* Missing fields */}
                  {load.missingOptional.length > 0 && (
                    <div className="flex items-center justify-between px-3 py-2 bg-amber-500/10 border border-amber-500/20 rounded-lg">
                      <div className="flex items-center gap-2">
                        <AlertTriangle size={14} className="text-amber-500 shrink-0" />
                        <p className="text-xs text-amber-400">
                          Missing: {load.missingOptional.join(', ')}
                        </p>
                      </div>
                      <button
                        onClick={() => toggleGapFill(index)}
                        className="text-[10px] font-black uppercase tracking-widest text-amber-500 hover:text-amber-400 transition-colors"
                      >
                        {isGapFillOpen ? 'HIDE' : 'FILL GAPS'}
                      </button>
                    </div>
                  )}

                  {/* Duplicate warning */}
                  {load.duplicateOf !== undefined && (
                    <div className="flex items-center gap-2 px-3 py-2 bg-amber-500/10 border border-amber-500/20 rounded-lg">
                      <AlertTriangle size={14} className="text-amber-500 shrink-0" />
                      <p className="text-xs text-amber-400">
                        {load.duplicateMessage || `Possible duplicate of load #${load.duplicateOf}`}
                      </p>
                    </div>
                  )}

                  {/* Gap-fill form */}
                  {isGapFillOpen && load.missingOptional.length > 0 && (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2 border-t border-slate-800">
                      {load.missingOptional.map((field) => (
                        <div key={field} className="space-y-1">
                          <label className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">
                            {field}
                          </label>
                          <input
                            type="text"
                            value={gapFills[index]?.[field] || ''}
                            onChange={(e) => updateGapFill(index, field, e.target.value)}
                            placeholder={`Enter ${field}`}
                            className="w-full bg-slate-900 border border-slate-800 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-600 focus:outline-none focus:border-amber-500"
                          />
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Save error */}
                  {state === 'error' && (
                    <div className="flex items-center gap-2 px-3 py-2 bg-red-500/10 border border-red-500/30 rounded-lg">
                      <X size={14} className="text-red-500 shrink-0" />
                      <p className="text-xs text-red-400">
                        Failed to save. Try again.
                      </p>
                    </div>
                  )}
                </div>
              );
            })}

            {/* Save All (bottom) */}
            {parsedLoads.length > 1 && (
              <div className="pt-4 border-t border-slate-800 flex justify-end">
                <button
                  onClick={saveAll}
                  disabled={allSaved}
                  className="px-8 py-2.5 bg-amber-500 rounded-lg text-sm font-black text-black hover:bg-amber-400 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                >
                  {allSaved ? (
                    <>
                      <Check size={16} />
                      <span>ALL SAVED</span>
                    </>
                  ) : (
                    <span>SAVE ALL LOADS</span>
                  )}
                </button>
              </div>
            )}

            {/* Post-save confirmation */}
            {allSaved && (
              <div className="flex items-center gap-2 px-4 py-3 bg-emerald-500/10 border border-emerald-500/30 rounded-lg">
                <Check size={16} className="text-emerald-500 shrink-0" />
                <p className="text-sm text-emerald-400">
                  All loads saved successfully.
                </p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function DetailItem({ label, value }: { label: string; value: string | null }) {
  return (
    <div>
      <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-1">
        {label}
      </p>
      {value ? (
        <p className="text-sm font-bold text-white">{value}</p>
      ) : (
        <p className="text-sm font-bold text-amber-500">Missing</p>
      )}
    </div>
  );
}
