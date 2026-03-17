import React from 'react';
import { ArrowRight, TrendingUp, DollarSign, Clock, MapPin, AlertCircle } from 'lucide-react';
import { OptimizedChain, ScoredLoad, Assumptions } from '../types';
import { motion } from 'motion/react';

interface Props {
  chain: OptimizedChain | null;
  assumptions: Assumptions;
}

export default function OptimizedChainView({ chain, assumptions }: Props) {
  if (!chain || chain.legs.length === 0) {
    return (
      <div className="bg-slate-900/50 border-2 border-dashed border-slate-800 rounded-2xl p-12 text-center">
        <div className="w-16 h-16 bg-slate-800 rounded-full flex items-center justify-center mx-auto mb-4">
          <AlertCircle className="text-slate-600" size={32} />
        </div>
        <h3 className="text-xl font-bold text-white mb-2">No Optimized Route Yet</h3>
        <p className="text-slate-500 max-w-md mx-auto">Click "Run Optimizer" to find the most profitable sequence of loads for today's HOS window.</p>
      </div>
    );
  }

  const { summary } = chain;

  const fuelCpm = assumptions.fuelPrice / assumptions.mpg;
  const totalCpm = fuelCpm + assumptions.driverPay + assumptions.truckLease + assumptions.insurance + assumptions.maintReserve + assumptions.overhead;

  return (
    <div className="space-y-6 mb-12">
      {/* Summary Bar */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-4">
        <StatCard label="Total Profit" value={`${summary.totalProfit.toLocaleString()}`} icon={<TrendingUp size={14} />} highlight />
        <StatCard label="Revenue" value={`${summary.totalRevenue.toLocaleString()}`} icon={<DollarSign size={14} />} />
        <StatCard label="Loads" value={summary.numLoads.toString()} />
        <StatCard label="Deadhead" value={`${summary.totalDeadhead} mi (${summary.deadheadPct.toFixed(1)}%)`} />
        <StatCard label="HOS Used" value={`${summary.totalHours.toFixed(1)} hrs`} />
        <StatCard label="Avg Margin" value={`${summary.avgMargin.toFixed(1)}%`} />
        <StatCard label="Profit / Hr" value={`${summary.profitPerHour.toFixed(2)}`} highlight />
      </div>

      {/* Visual Chain */}
      <div className="relative">
        <div className="absolute left-8 top-0 bottom-0 w-0.5 bg-slate-800" />
        
        <div className="space-y-0">
          {chain.legs.map((leg, index) => {
            const deadheadCost = leg.deadhead * totalCpm;
            
            return (
              <React.Fragment key={leg.load?.id || `leg-${index}`}>
                {/* Deadhead Tile (if applicable) */}
                {leg.deadhead > 0 && (
                  <motion.div 
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    className="relative pl-20 py-4"
                  >
                    <div className="absolute left-7.5 top-1/2 -translate-y-1/2 w-1.5 h-1.5 bg-slate-700 rounded-full z-10" />
                    <div className="flex items-center gap-4 bg-slate-950/50 border border-slate-800/50 rounded-lg px-4 py-2 w-fit">
                      <div className="flex items-center gap-2 text-slate-500">
                        <Clock size={12} />
                        <span className="text-[10px] font-bold uppercase tracking-wider">Deadhead</span>
                      </div>
                      <div className="h-3 w-px bg-slate-800" />
                      <span className="text-xs font-bold text-slate-300">{leg.deadhead} miles</span>
                      <div className="h-3 w-px bg-slate-800" />
                      <span className="text-xs font-bold text-red-500/80">-${deadheadCost.toFixed(2)} cost</span>
                    </div>
                  </motion.div>
                )}

                <motion.div 
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: index * 0.1 }}
                  className="relative pl-20 pb-8"
                >
                  {/* Leg Number Bubble */}
                  <div className={`absolute left-4 top-0 w-8 h-8 ${leg.isReturnHome ? 'bg-red-500/20 border-red-500/50' : 'bg-slate-800 border-slate-700'} border-2 rounded-full flex items-center justify-center z-10`}>
                    <span className="text-xs font-bold text-white">{index + 1}</span>
                  </div>

                  <div className={`bg-slate-900 border ${leg.isReturnHome ? 'border-red-500/30 bg-red-500/5' : 'border-slate-800'} rounded-xl p-6 hover:border-slate-700 transition-colors shadow-xl shadow-black/20`}>
                    <div className="flex flex-wrap items-start justify-between gap-6">
                      <div className="space-y-4 flex-1 min-w-[300px]">
                        <div className="flex items-center gap-4">
                          <div className="flex items-center gap-2">
                            <MapPin size={16} className={leg.isReturnHome ? 'text-red-500' : 'text-amber-500'} />
                            <span className="text-lg font-bold text-white">{leg.load?.origin || leg.result?.origin}</span>
                          </div>
                          <ArrowRight className="text-slate-600" size={20} />
                          <div className="flex items-center gap-2">
                            <MapPin size={16} className="text-slate-400" />
                            <span className="text-lg font-bold text-white">{leg.load?.destination || leg.result?.destination}</span>
                          </div>
                          {leg.isReturnHome && (
                            <span className="px-2 py-0.5 bg-red-500 text-black text-[10px] font-black uppercase rounded tracking-wider">Return Home</span>
                          )}
                        </div>

                        <div className="flex flex-wrap gap-6 text-sm">
                          <div className="space-y-1">
                            <p className="text-slate-500 font-bold uppercase text-[10px] tracking-wider">Start</p>
                            <p className="text-white font-semibold">{new Date(leg.startTime).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</p>
                            <p className="text-[10px] text-slate-500">{new Date(leg.startTime).toLocaleDateString()}</p>
                          </div>
                          <div className="space-y-1">
                            <p className="text-slate-500 font-bold uppercase text-[10px] tracking-wider">End</p>
                            <p className="text-white font-semibold">{new Date(leg.endTime).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</p>
                            <p className="text-[10px] text-slate-500">{new Date(leg.endTime).toLocaleDateString()}</p>
                          </div>
                          {!leg.isReturnHome && (
                            <div className="space-y-1">
                              <p className="text-slate-500 font-bold uppercase text-[10px] tracking-wider">Loaded</p>
                              <p className="text-white font-semibold">{leg.load?.miles} mi</p>
                            </div>
                          )}
                          <div className="space-y-1">
                            <p className="text-slate-500 font-bold uppercase text-[10px] tracking-wider">Drive Time</p>
                            <p className="text-white font-semibold">{leg.result?.driveHours.toFixed(1)} hrs</p>
                          </div>
                        </div>
                      </div>

                      <div className="flex items-center gap-8">
                        {leg.isOvernight && (
                          <div className="flex flex-col items-center gap-1">
                            <div className="px-2 py-1 bg-indigo-500/20 border border-indigo-500/30 rounded text-[10px] font-bold text-indigo-400 uppercase tracking-wider">
                              Overnight
                            </div>
                          </div>
                        )}
                        <div className="text-right">
                          <p className="text-slate-500 font-bold uppercase text-[10px] tracking-wider mb-1">{leg.isReturnHome ? 'Return Cost' : 'Leg Profit'}</p>
                          <p className={`text-2xl font-black ${leg.isReturnHome ? 'text-red-500' : 'text-emerald-500'}`}>
                            {leg.isReturnHome ? '-' : ''}${Math.abs(leg.result?.profit || 0).toLocaleString()}
                          </p>
                          {!leg.isReturnHome && <p className="text-xs font-bold text-slate-400">{leg.result?.marginPct.toFixed(1)}% Margin</p>}
                        </div>

                        {!leg.isReturnHome && leg.result && (
                          <div className="flex flex-col items-center gap-2">
                            <ScoreBadge score={leg.result.score} />
                            <ActionBadge action={leg.result.action} />
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                </motion.div>
              </React.Fragment>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function StatCard({ label, value, icon, highlight }: { label: string; value: string; icon?: React.ReactNode; highlight?: boolean }) {
  return (
    <div className={`bg-slate-900 border ${highlight ? 'border-amber-500/30 bg-amber-500/5' : 'border-slate-800'} rounded-xl p-4`}>
      <div className="flex items-center gap-2 mb-1">
        {icon && <span className="text-slate-500">{icon}</span>}
        <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">{label}</p>
      </div>
      <p className={`text-lg font-black ${highlight ? 'text-amber-500' : 'text-white'}`}>{value}</p>
    </div>
  );
}

function ScoreBadge({ score }: { score: number }) {
  let color = 'bg-slate-800 text-slate-400';
  if (score >= 5) color = 'bg-emerald-500/20 text-emerald-500 border-emerald-500/30';
  else if (score >= 2) color = 'bg-yellow-500/20 text-yellow-500 border-yellow-500/30';
  else if (score >= 0) color = 'bg-orange-500/20 text-orange-500 border-orange-500/30';
  else color = 'bg-red-500/20 text-red-500 border-red-500/30';

  return (
    <div className={`px-3 py-1 rounded-full border text-xs font-black ${color}`}>
      SCORE: {score > 0 ? `+${score}` : score}
    </div>
  );
}

function ActionBadge({ action }: { action: ScoredLoad['action'] }) {
  let color = 'bg-slate-800 text-slate-400';
  if (action === 'BOOK IT') color = 'bg-emerald-500 text-black';
  else if (action === 'CONSIDER') color = 'bg-yellow-500 text-black';
  else if (action === 'NEGOTIATE') color = 'bg-orange-500 text-black';
  else color = 'bg-red-500 text-white';

  return (
    <div className={`px-4 py-1.5 rounded-lg text-[10px] font-black uppercase tracking-widest ${color}`}>
      {action}
    </div>
  );
}
