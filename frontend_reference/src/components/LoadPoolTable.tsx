import React, { useState } from 'react';
import { ChevronDown, ChevronUp, ArrowRight, CheckCircle2, Filter, MessageSquarePlus } from 'lucide-react';
import { ScoredLoad } from '../types';

interface Props {
  loads: ScoredLoad[];
  includedInChain: string[];
  onToggleLoad: (id: string) => void;
  onFeedbackClick?: (load: ScoredLoad) => void;
}

type SortKey = 'score' | 'profit' | 'marginPct' | 'rpm' | 'miles';

export default function LoadPoolTable({ loads, includedInChain, onToggleLoad, onFeedbackClick }: Props) {
  const [sortKey, setSortKey] = useState<SortKey>('score');
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const sortedLoads = [...loads].sort((a, b) => {
    if (sortKey === 'score') return b.score - a.score;
    if (sortKey === 'profit') return b.profit - a.profit;
    if (sortKey === 'marginPct') return b.marginPct - a.marginPct;
    if (sortKey === 'rpm') return b.rpm - a.rpm;
    if (sortKey === 'miles') return b.miles - a.miles;
    return 0;
  });

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden">
      <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-900/50">
        <h2 className="text-lg font-bold text-white flex items-center gap-2">
          <Filter size={18} className="text-slate-500" />
          Available Load Pool
        </h2>
        <div className="flex items-center gap-4">
          <span className="text-xs font-bold text-slate-500 uppercase">Sort By:</span>
          <div className="flex bg-slate-950 rounded-lg p-1 border border-slate-800">
            {(['score', 'profit', 'marginPct', 'rpm', 'miles'] as SortKey[]).map(key => (
              <button
                key={key}
                onClick={() => setSortKey(key)}
                className={`px-3 py-1 text-[10px] font-black uppercase tracking-wider rounded-md transition-all ${
                  sortKey === key ? 'bg-amber-500 text-black' : 'text-slate-500 hover:text-white'
                }`}
              >
                {key === 'marginPct' ? 'Margin' : key}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="text-[10px] font-bold text-slate-500 uppercase tracking-widest border-b border-slate-800">
              <th className="px-6 py-4">Status</th>
              <th className="px-6 py-4">Load ID</th>
              <th className="px-6 py-4">Route</th>
              <th className="px-6 py-4">Commodity</th>
              <th className="px-6 py-4">Rate</th>
              <th className="px-6 py-4">Miles</th>
              <th className="px-6 py-4">Profit</th>
              <th className="px-6 py-4">Score</th>
              <th className="px-6 py-4 text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800">
            {sortedLoads.map(load => {
              const isIncluded = includedInChain.includes(load.id);
              const isExpanded = expandedId === load.id;

              return (
                <React.Fragment key={load.id}>
                  <tr 
                    onClick={() => setExpandedId(isExpanded ? null : load.id)}
                    className={`group cursor-pointer hover:bg-slate-800/50 transition-colors ${isIncluded ? 'bg-amber-500/5' : ''}`}
                  >
                    <td className="px-6 py-4">
                      {isIncluded ? (
                        <CheckCircle2 className="text-amber-500" size={18} />
                      ) : (
                        <div className="w-[18px] h-[18px] rounded-full border-2 border-slate-800 group-hover:border-slate-700" />
                      )}
                    </td>
                    <td className="px-6 py-4 font-mono text-xs text-slate-400">{load.id}</td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-bold text-white">{load.origin}</span>
                        <ArrowRight size={14} className="text-slate-600" />
                        <span className="text-sm font-bold text-white">{load.destination}</span>
                      </div>
                      <div className="flex flex-col mt-1">
                        <span className="text-[10px] text-slate-500 uppercase font-bold">PU: {new Date(load.pickupWindowStart).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                        <span className="text-[10px] text-slate-500 uppercase font-bold">DEL: {new Date(load.deliveryDeadline).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-xs text-slate-400">{load.commodity}</td>
                    <td className="px-6 py-4">
                      <p className="text-sm font-bold text-white">${load.rate.toLocaleString()}</p>
                      <p className="text-[10px] text-slate-500">${load.rpm.toFixed(2)}/mi</p>
                    </td>
                    <td className="px-6 py-4">
                      <p className="text-sm font-bold text-white">{load.miles} mi</p>
                      <p className="text-[10px] text-slate-500">+{load.deadheadMiles} DH</p>
                    </td>
                    <td className="px-6 py-4">
                      <p className={`text-sm font-bold ${load.profit > 0 ? 'text-emerald-500' : 'text-red-500'}`}>
                        ${load.profit.toLocaleString()}
                      </p>
                      <p className="text-[10px] text-slate-500">{load.marginPct.toFixed(1)}%</p>
                    </td>
                    <td className="px-6 py-4">
                      <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-black ${getScoreColor(load.score)}`}>
                        {load.score}
                      </div>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <div className="flex items-center justify-end gap-2">
                        {onFeedbackClick && (
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              onFeedbackClick(load);
                            }}
                            className="p-1.5 rounded-lg text-slate-500 hover:text-amber-400 hover:bg-slate-800 transition-all"
                            title="Submit Feedback"
                          >
                            <MessageSquarePlus size={14} />
                          </button>
                        )}
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            onToggleLoad(load.id);
                          }}
                          className={`px-3 py-1.5 rounded-lg text-[10px] font-black uppercase tracking-widest transition-all ${
                            isIncluded
                              ? 'bg-amber-500 text-black'
                              : 'bg-slate-800 text-slate-400 hover:text-white hover:bg-slate-700'
                          }`}
                        >
                          {isIncluded ? 'REMOVE' : 'ADD TO CHAIN'}
                        </button>
                      </div>
                    </td>
                  </tr>
                  {isExpanded && (
                    <tr>
                      <td colSpan={9} className="px-6 py-8 bg-slate-950/50 border-y border-slate-800">
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-12">
                          <div className="space-y-4">
                            <h4 className="text-xs font-bold text-slate-500 uppercase tracking-widest">Revenue Breakdown</h4>
                            <div className="space-y-2">
                              <LineItem label="Line Haul" value={load.rate} />
                              <LineItem label="Detention Revenue" value={load.detentionHours * 50} />
                              <LineItem label="Factoring Fee" value={-(load.rate * 0.03)} negative />
                              <div className="pt-2 border-t border-slate-800">
                                <LineItem label="Net Revenue" value={load.netRevenue} highlight />
                              </div>
                            </div>
                          </div>

                          <div className="space-y-4">
                            <h4 className="text-xs font-bold text-slate-500 uppercase tracking-widest">Cost Breakdown</h4>
                            <div className="space-y-2">
                              <LineItem label="Loaded Miles" value={load.miles} unit="mi" />
                              <LineItem label="Deadhead Miles" value={load.deadheadMiles} unit="mi" />
                              <LineItem label="Total Miles" value={load.totalMiles} unit="mi" />
                              <div className="pt-2 border-t border-slate-800">
                                <LineItem label="Total Operating Cost" value={load.totalCost} negative />
                              </div>
                            </div>
                          </div>

                          <div className="space-y-4">
                            <h4 className="text-xs font-bold text-slate-500 uppercase tracking-widest">Efficiency Metrics</h4>
                            <div className="grid grid-cols-2 gap-4">
                              <MetricBox label="All-in RPM" value={`$${load.allInRpm.toFixed(2)}`} />
                              <MetricBox label="Profit / Hr" value={`$${load.profitPerHour.toFixed(2)}`} />
                              <MetricBox label="Drive Time" value={`${load.driveHours.toFixed(1)} hrs`} />
                              <MetricBox label="Total Time" value={`${load.totalHours.toFixed(1)} hrs`} />
                            </div>
                          </div>
                        </div>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function LineItem({ label, value, negative, highlight, unit = '$' }: { label: string; value: number; negative?: boolean; highlight?: boolean; unit?: string }) {
  return (
    <div className="flex justify-between text-sm">
      <span className="text-slate-500">{label}</span>
      <span className={`font-bold ${highlight ? 'text-amber-500' : negative ? 'text-red-500' : 'text-white'}`}>
        {unit === '$' ? `${value < 0 ? '-' : ''}$${Math.abs(value).toLocaleString()}` : `${value.toLocaleString()} ${unit}`}
      </span>
    </div>
  );
}

function MetricBox({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-lg p-3">
      <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-1">{label}</p>
      <p className="text-sm font-black text-white">{value}</p>
    </div>
  );
}

function getScoreColor(score: number) {
  if (score >= 5) return 'bg-emerald-500 text-black';
  if (score >= 2) return 'bg-yellow-500 text-black';
  if (score >= 0) return 'bg-orange-500 text-black';
  return 'bg-red-500 text-white';
}
