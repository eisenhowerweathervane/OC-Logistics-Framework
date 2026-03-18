import React, { useEffect, useState, useCallback } from 'react';
import { getWatchlist, resolveWatchlist } from '../services/api';
import { WatchlistPlan, ScenarioBranch, WatchlistEntry, ScenarioRecommendation } from '../types';
import { Lock, Clock, AlertTriangle, ChevronRight, Zap, Timer, Coffee, OctagonAlert } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';

interface WatchlistViewProps {
  committedLoadIds: number[];
  availableLoads: any[];
  startCity: string;
  hosRemaining: number;
  maxDays: number;
  onLoadBooked: (loadId: number) => void;
}

type ScenarioKey = 'quick' | 'normal' | 'slow' | 'detention';

const SCENARIO_CONFIG: Record<ScenarioKey, { label: string; accent: string; bg: string; border: string; icon: React.ReactNode; description: string }> = {
  quick: {
    label: 'Quick',
    accent: 'text-emerald-500',
    bg: 'bg-emerald-500/10',
    border: 'border-emerald-500/30',
    icon: <Zap size={14} className="text-emerald-500" />,
    description: '< 1 hr dwell',
  },
  normal: {
    label: 'Normal',
    accent: 'text-blue-500',
    bg: 'bg-blue-500/10',
    border: 'border-blue-500/30',
    icon: <Timer size={14} className="text-blue-500" />,
    description: '1-2 hrs dwell',
  },
  slow: {
    label: 'Slow',
    accent: 'text-amber-500',
    bg: 'bg-amber-500/10',
    border: 'border-amber-500/30',
    icon: <Coffee size={14} className="text-amber-500" />,
    description: '2-3 hrs dwell',
  },
  detention: {
    label: 'Detention',
    accent: 'text-red-500',
    bg: 'bg-red-500/10',
    border: 'border-red-500/30',
    icon: <OctagonAlert size={14} className="text-red-500" />,
    description: '3+ hrs dwell',
  },
};

const DWELL_PRESETS = [
  { label: '< 1 hr', value: 0.75 },
  { label: '1-2 hrs', value: 1.5 },
  { label: '2-3 hrs', value: 2.5 },
  { label: '3+ hrs', value: 3.5 },
];

export default function WatchlistView({
  committedLoadIds,
  availableLoads,
  startCity,
  hosRemaining,
  maxDays,
  onLoadBooked,
}: WatchlistViewProps) {
  const [watchlistPlan, setWatchlistPlan] = useState<WatchlistPlan | null>(null);
  const [resolvedScenario, setResolvedScenario] = useState<string | null>(null);
  const [recommendations, setRecommendations] = useState<any[]>([]);
  const [actualDwellHours, setActualDwellHours] = useState<number>(0);
  const [loading, setLoading] = useState(false);
  const [resolving, setResolving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showDwellInput, setShowDwellInput] = useState(false);
  const [manualDwell, setManualDwell] = useState('');
  const [activeScenarioTab, setActiveScenarioTab] = useState<ScenarioKey>('quick');
  const [completedLegIndex, setCompletedLegIndex] = useState<number | null>(null);

  const fetchWatchlist = useCallback(async () => {
    if (committedLoadIds.length === 0) return;
    setLoading(true);
    setError(null);
    try {
      const plan = await getWatchlist(committedLoadIds, startCity, hosRemaining, maxDays);
      setWatchlistPlan(plan);
    } catch (err) {
      setError('Failed to load watchlist plan. Please try again.');
    } finally {
      setLoading(false);
    }
  }, [committedLoadIds, startCity, hosRemaining, maxDays]);

  useEffect(() => {
    fetchWatchlist();
  }, [fetchWatchlist]);

  const handleMarkComplete = (index: number) => {
    setCompletedLegIndex(index);
    setShowDwellInput(true);
  };

  const handleDwellPreset = (hours: number) => {
    setActualDwellHours(hours);
    setManualDwell(hours.toString());
  };

  const handleResolve = async () => {
    if (!watchlistPlan || actualDwellHours <= 0) return;
    setResolving(true);
    setError(null);
    try {
      const result = await resolveWatchlist(actualDwellHours, watchlistPlan.scenarioTree);
      setRecommendations(result);

      // Determine which scenario matches
      if (actualDwellHours < 1) setResolvedScenario('quick');
      else if (actualDwellHours < 2) setResolvedScenario('normal');
      else if (actualDwellHours < 3) setResolvedScenario('slow');
      else setResolvedScenario('detention');

      setShowDwellInput(false);
    } catch (err) {
      setError('Failed to resolve watchlist. Please try again.');
    } finally {
      setResolving(false);
    }
  };

  // ---------- Empty / Loading states ----------
  if (committedLoadIds.length === 0) {
    return (
      <div className="bg-slate-900/50 border-2 border-dashed border-slate-800 rounded-2xl p-12 text-center">
        <div className="w-16 h-16 bg-slate-800 rounded-full flex items-center justify-center mx-auto mb-4">
          <Lock className="text-slate-600" size={32} />
        </div>
        <h3 className="text-xl font-bold text-white mb-2">No Committed Loads</h3>
        <p className="text-slate-500 max-w-md mx-auto">
          Book loads first, then use the Watchlist to plan ahead with scenario branches for dwell time outcomes.
        </p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-12 text-center">
        <div className="w-10 h-10 border-2 border-amber-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
        <p className="text-slate-400 font-semibold">Building watchlist scenario tree...</p>
      </div>
    );
  }

  if (error && !watchlistPlan) {
    return (
      <div className="bg-slate-900/50 border border-red-500/30 rounded-2xl p-12 text-center">
        <AlertTriangle className="text-red-500 mx-auto mb-4" size={32} />
        <p className="text-red-400 font-semibold">{error}</p>
      </div>
    );
  }

  const scenarioTree = watchlistPlan?.scenarioTree;
  const scenarioKeys: ScenarioKey[] = ['quick', 'normal', 'slow', 'detention'];

  return (
    <div className="space-y-8 mb-12">
      {/* ---------- COMMITTED LOADS SECTION ---------- */}
      <section>
        <div className="flex items-center gap-3 mb-4">
          <div className="flex items-center gap-2 px-3 py-1.5 bg-amber-500/10 border border-amber-500/30 rounded-lg">
            <Lock size={14} className="text-amber-500" />
            <span className="text-xs font-black text-amber-500 uppercase tracking-widest">Committed</span>
          </div>
          <div className="h-px flex-1 bg-slate-800" />
        </div>

        <div className="relative">
          <div className="absolute left-8 top-0 bottom-0 w-0.5 bg-slate-800" />

          <div className="space-y-0">
            {(watchlistPlan?.committed ?? []).map((load: any, index: number) => (
              <motion.div
                key={load.id ?? `committed-${index}`}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.08 }}
                className="relative pl-20 pb-6"
              >
                {/* Leg Bubble */}
                <div className="absolute left-4 top-0 w-8 h-8 bg-amber-500/20 border-2 border-amber-500/50 rounded-full flex items-center justify-center z-10">
                  <span className="text-xs font-bold text-white">{index + 1}</span>
                </div>

                <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 hover:border-slate-700 transition-colors shadow-xl shadow-black/20">
                  <div className="flex flex-wrap items-start justify-between gap-4">
                    <div className="space-y-3 flex-1 min-w-[260px]">
                      {/* Route */}
                      <div className="flex items-center gap-3">
                        <span className="text-lg font-bold text-white">{load.origin ?? 'Origin'}</span>
                        <ChevronRight size={18} className="text-slate-600" />
                        <span className="text-lg font-bold text-white">{load.destination ?? 'Destination'}</span>
                      </div>

                      {/* Details row */}
                      <div className="flex flex-wrap gap-5 text-sm">
                        {load.rate != null && (
                          <div className="space-y-0.5">
                            <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Rate</p>
                            <p className="text-white font-semibold">${Number(load.rate).toLocaleString()}</p>
                          </div>
                        )}
                        {load.miles != null && (
                          <div className="space-y-0.5">
                            <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Miles</p>
                            <p className="text-white font-semibold">{load.miles} mi</p>
                          </div>
                        )}
                        {load.pickupWindowStart && (
                          <div className="space-y-0.5">
                            <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Pickup</p>
                            <p className="text-white font-semibold">
                              {new Date(load.pickupWindowStart).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                            </p>
                          </div>
                        )}
                      </div>
                    </div>

                    <div className="flex items-center gap-4">
                      {/* Score badge */}
                      {load.score != null && <ScoreBadge score={load.score} />}

                      {/* Profit */}
                      {load.profit != null && (
                        <div className="text-right">
                          <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-1">Profit</p>
                          <p className={`text-xl font-black ${load.profit >= 0 ? 'text-emerald-500' : 'text-red-500'}`}>
                            ${Math.abs(load.profit).toLocaleString()}
                          </p>
                        </div>
                      )}

                      {/* Mark Complete */}
                      {completedLegIndex !== index && (
                        <button
                          onClick={() => handleMarkComplete(index)}
                          className="px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-xs font-bold text-slate-300 hover:bg-slate-700 hover:text-white transition-colors"
                        >
                          Mark Complete
                        </button>
                      )}
                      {completedLegIndex === index && (
                        <span className="px-3 py-1.5 bg-emerald-500/20 border border-emerald-500/30 rounded-lg text-[10px] font-black text-emerald-500 uppercase tracking-wider">
                          Completed
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ---------- DWELL TIME RESOLUTION ---------- */}
      <AnimatePresence>
        {showDwellInput && (
          <motion.section
            initial={{ opacity: 0, y: -10, height: 0 }}
            animate={{ opacity: 1, y: 0, height: 'auto' }}
            exit={{ opacity: 0, y: -10, height: 0 }}
            className="overflow-hidden"
          >
            <div className="bg-slate-900 border border-amber-500/30 rounded-2xl p-6 space-y-5">
              <div className="flex items-center gap-3">
                <Clock size={18} className="text-amber-500" />
                <h3 className="text-lg font-bold text-white">How long did unloading take?</h3>
              </div>

              {/* Preset buttons */}
              <div className="flex flex-wrap gap-3">
                {DWELL_PRESETS.map((preset) => (
                  <button
                    key={preset.label}
                    onClick={() => handleDwellPreset(preset.value)}
                    className={`px-4 py-2.5 rounded-lg text-sm font-bold border transition-colors ${
                      actualDwellHours === preset.value
                        ? 'bg-amber-500/20 border-amber-500/50 text-amber-500'
                        : 'bg-slate-800 border-slate-700 text-slate-300 hover:bg-slate-700 hover:text-white'
                    }`}
                  >
                    {preset.label}
                  </button>
                ))}
              </div>

              {/* Manual input */}
              <div className="flex items-center gap-3">
                <span className="text-sm text-slate-400 font-semibold">Or enter manually:</span>
                <input
                  type="number"
                  min={0}
                  step={0.25}
                  value={manualDwell}
                  onChange={(e) => {
                    setManualDwell(e.target.value);
                    const val = parseFloat(e.target.value);
                    if (!isNaN(val) && val > 0) setActualDwellHours(val);
                  }}
                  placeholder="Hours"
                  className="w-24 px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-white text-sm font-semibold focus:outline-none focus:border-amber-500"
                />
                <span className="text-sm text-slate-500">hours</span>
              </div>

              {error && <p className="text-sm text-red-400">{error}</p>}

              <button
                onClick={handleResolve}
                disabled={actualDwellHours <= 0 || resolving}
                className="px-6 py-3 bg-amber-500 text-black font-black text-sm uppercase tracking-wider rounded-xl hover:bg-amber-400 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
              >
                {resolving ? 'Resolving...' : 'Get Recommendations'}
              </button>
            </div>
          </motion.section>
        )}
      </AnimatePresence>

      {/* ---------- SCENARIO BRANCHES ---------- */}
      {scenarioTree && (
        <section>
          <div className="flex items-center gap-3 mb-4">
            <span className="text-xs font-black text-slate-500 uppercase tracking-widest">Scenario Branches</span>
            <div className="h-px flex-1 bg-slate-800" />
          </div>

          {/* Tabs */}
          <div className="flex gap-2 mb-6">
            {scenarioKeys.map((key) => {
              const cfg = SCENARIO_CONFIG[key];
              const isActive = activeScenarioTab === key;
              const isResolved = resolvedScenario === key;
              return (
                <button
                  key={key}
                  onClick={() => setActiveScenarioTab(key)}
                  className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-bold uppercase tracking-wider border transition-colors ${
                    isActive
                      ? `${cfg.bg} ${cfg.border} ${cfg.accent}`
                      : 'bg-slate-900 border-slate-800 text-slate-400 hover:border-slate-700'
                  } ${isResolved ? 'ring-2 ring-offset-2 ring-offset-slate-950 ring-amber-500' : ''}`}
                >
                  {cfg.icon}
                  {cfg.label}
                  {isResolved && (
                    <span className="ml-1 px-1.5 py-0.5 bg-amber-500 text-black text-[8px] font-black rounded uppercase">
                      Match
                    </span>
                  )}
                </button>
              );
            })}
          </div>

          {/* Active scenario panel */}
          {scenarioTree.scenarios && (
            <ScenarioPanel
              branch={scenarioTree.scenarios[activeScenarioTab]}
              config={SCENARIO_CONFIG[activeScenarioTab]}
              isResolved={resolvedScenario === activeScenarioTab}
              resolvedRecommendations={resolvedScenario === activeScenarioTab ? recommendations : null}
              onBook={onLoadBooked}
            />
          )}
        </section>
      )}

      {/* ---------- WATCHLIST TABLE ---------- */}
      {watchlistPlan && watchlistPlan.watchlist.length > 0 && (
        <section>
          <div className="flex items-center gap-3 mb-4">
            <span className="text-xs font-black text-slate-500 uppercase tracking-widest">Watchlist</span>
            <span className="text-[10px] font-bold text-slate-600 bg-slate-800 px-2 py-0.5 rounded-full">
              {watchlistPlan.watchlist.length} candidates
            </span>
            <div className="h-px flex-1 bg-slate-800" />
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-800">
                  <th className="text-left px-4 py-3 text-[10px] font-bold text-slate-500 uppercase tracking-widest">Route</th>
                  <th className="text-right px-4 py-3 text-[10px] font-bold text-slate-500 uppercase tracking-widest">Score</th>
                  <th className="text-right px-4 py-3 text-[10px] font-bold text-slate-500 uppercase tracking-widest">Profit</th>
                  <th className="text-center px-4 py-3 text-[10px] font-bold text-slate-500 uppercase tracking-widest">Scenarios</th>
                  <th className="text-right px-4 py-3 text-[10px] font-bold text-slate-500 uppercase tracking-widest">Pickup Deadline</th>
                  <th className="px-4 py-3" />
                </tr>
              </thead>
              <tbody>
                {watchlistPlan.watchlist.map((entry: WatchlistEntry, i: number) => {
                  const deadline = entry.pickupDeadline ? new Date(entry.pickupDeadline) : null;
                  const hoursUntilPickup = deadline ? (deadline.getTime() - Date.now()) / (1000 * 60 * 60) : null;
                  const isUrgent = hoursUntilPickup != null && hoursUntilPickup < 4;

                  return (
                    <motion.tr
                      key={entry.load?.id ?? i}
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      transition={{ delay: i * 0.03 }}
                      className="border-b border-slate-800/50 hover:bg-slate-800/30 transition-colors"
                    >
                      <td className="px-4 py-3">
                        <span className="font-bold text-white">
                          {entry.load?.origin ?? '???'}
                        </span>
                        <ChevronRight size={12} className="inline text-slate-600 mx-1" />
                        <span className="font-bold text-white">
                          {entry.load?.destination ?? '???'}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right">
                        {entry.score != null ? <ScoreBadge score={entry.score} /> : <span className="text-slate-600">--</span>}
                      </td>
                      <td className="px-4 py-3 text-right">
                        {entry.profit != null ? (
                          <span className={`font-black ${entry.profit >= 0 ? 'text-emerald-500' : 'text-red-500'}`}>
                            ${Math.abs(entry.profit).toLocaleString()}
                          </span>
                        ) : (
                          <span className="text-slate-600">--</span>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex flex-wrap justify-center gap-1">
                          {entry.scenarios.map((s) => {
                            const key = s.toLowerCase() as ScenarioKey;
                            const cfg = SCENARIO_CONFIG[key];
                            if (!cfg) return null;
                            return (
                              <span
                                key={s}
                                className={`px-2 py-0.5 rounded text-[10px] font-bold border ${cfg.bg} ${cfg.border} ${cfg.accent}`}
                              >
                                {cfg.label}
                              </span>
                            );
                          })}
                        </div>
                      </td>
                      <td className="px-4 py-3 text-right">
                        {deadline ? (
                          <div className={`flex items-center justify-end gap-1.5 ${isUrgent ? 'text-red-500' : 'text-slate-300'}`}>
                            {isUrgent && <AlertTriangle size={12} />}
                            <span className="font-semibold text-xs">
                              {deadline.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                            </span>
                            {isUrgent && (
                              <span className="text-[10px] font-bold text-red-500 ml-1">
                                ({hoursUntilPickup!.toFixed(1)}h)
                              </span>
                            )}
                          </div>
                        ) : (
                          <span className="text-slate-600">--</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <button
                          onClick={() => entry.load?.id != null && onLoadBooked(entry.load.id)}
                          className="px-3 py-1.5 bg-slate-800 border border-slate-700 rounded-lg text-[10px] font-bold text-slate-300 uppercase tracking-wider hover:bg-emerald-500/20 hover:border-emerald-500/30 hover:text-emerald-500 transition-colors"
                        >
                          Book
                        </button>
                      </td>
                    </motion.tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  );
}

// =============================================================================
// Sub-components
// =============================================================================

function ScenarioPanel({
  branch,
  config,
  isResolved,
  resolvedRecommendations,
  onBook,
}: {
  branch: ScenarioBranch;
  config: (typeof SCENARIO_CONFIG)[ScenarioKey];
  isResolved: boolean;
  resolvedRecommendations: any[] | null;
  onBook: (loadId: number) => void;
}) {
  const recs = resolvedRecommendations ?? branch.recommendations;

  return (
    <motion.div
      key={config.label}
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
      className={`bg-slate-900 border rounded-2xl p-6 space-y-4 ${isResolved ? 'border-amber-500/40' : 'border-slate-800'}`}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          {config.icon}
          <h4 className={`text-sm font-black uppercase tracking-wider ${config.accent}`}>{config.label} Scenario</h4>
          <span className="text-xs text-slate-500 font-semibold">{config.description}</span>
        </div>
        <span className="text-xs text-slate-500 font-semibold">
          Dwell: <span className="text-white font-bold">{branch.dwellHours}h</span>
        </span>
      </div>

      {isResolved && (
        <div className="px-3 py-2 bg-amber-500/10 border border-amber-500/30 rounded-lg text-xs font-bold text-amber-500">
          This scenario matches your reported dwell time.
        </div>
      )}

      {recs.length === 0 ? (
        <p className="text-slate-500 text-sm py-4 text-center">No recommendations for this scenario.</p>
      ) : (
        <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
          {recs.map((rec: ScenarioRecommendation, i: number) => (
            <motion.div
              key={rec.load?.id ?? i}
              initial={{ opacity: 0, scale: 0.97 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: i * 0.05 }}
              className={`bg-slate-950 border ${config.border} rounded-xl p-4 space-y-3 hover:border-slate-600 transition-colors`}
            >
              {/* Route */}
              <div className="flex items-center gap-2">
                <span className="text-sm font-bold text-white">{rec.load?.origin ?? '???'}</span>
                <ChevronRight size={14} className="text-slate-600" />
                <span className="text-sm font-bold text-white">{rec.load?.destination ?? '???'}</span>
              </div>

              {/* Metrics row */}
              <div className="flex flex-wrap gap-4 text-xs">
                {rec.load?.rate != null && (
                  <div>
                    <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Rate</p>
                    <p className="text-white font-semibold">${Number(rec.load.rate).toLocaleString()}</p>
                  </div>
                )}
                <div>
                  <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Score</p>
                  <p className="text-white font-semibold">{rec.score > 0 ? `+${rec.score}` : rec.score}</p>
                </div>
                <div>
                  <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Profit</p>
                  <p className={`font-black ${rec.profit >= 0 ? 'text-emerald-500' : 'text-red-500'}`}>
                    ${Math.abs(rec.profit).toLocaleString()}
                  </p>
                </div>
              </div>

              {/* Chain summary */}
              {rec.chainSummary && (
                <div className="flex flex-wrap gap-3 text-[10px] text-slate-400">
                  {rec.chainSummary.totalProfit != null && (
                    <span>
                      Chain: <span className="text-emerald-500 font-bold">${rec.chainSummary.totalProfit.toLocaleString()}</span>
                    </span>
                  )}
                  {rec.chainSummary.numLoads != null && <span>{rec.chainSummary.numLoads} loads</span>}
                  {rec.chainSummary.totalHours != null && <span>{rec.chainSummary.totalHours.toFixed(1)}h</span>}
                </div>
              )}

              {/* Book button */}
              <button
                onClick={() => rec.load?.id != null && onBook(rec.load.id)}
                className={`w-full py-2 rounded-lg text-xs font-black uppercase tracking-wider border transition-colors ${config.bg} ${config.border} ${config.accent} hover:opacity-80`}
              >
                Book This Load
              </button>
            </motion.div>
          ))}
        </div>
      )}
    </motion.div>
  );
}

function ScoreBadge({ score }: { score: number }) {
  let color = 'bg-slate-800 text-slate-400';
  if (score >= 5) color = 'bg-emerald-500/20 text-emerald-500 border-emerald-500/30';
  else if (score >= 2) color = 'bg-yellow-500/20 text-yellow-500 border-yellow-500/30';
  else if (score >= 0) color = 'bg-orange-500/20 text-orange-500 border-orange-500/30';
  else color = 'bg-red-500/20 text-red-500 border-red-500/30';

  return (
    <span className={`inline-flex px-2.5 py-0.5 rounded-full border text-xs font-black ${color}`}>
      {score > 0 ? `+${score}` : score}
    </span>
  );
}
