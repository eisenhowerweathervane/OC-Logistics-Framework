import React, { useState, useEffect, useCallback } from 'react';
import { getLaneHistory, getBrokerHistory } from '../services/api';
import { LaneHistory, BrokerHistory } from '../types';
import { TrendingUp, TrendingDown, Minus, BarChart3, Users, ArrowUpDown } from 'lucide-react';

const US_STATES = [
  'AL','AK','AZ','AR','CA','CO','CT','DE','FL','GA','HI','ID','IL','IN','IA',
  'KS','KY','LA','ME','MD','MA','MI','MN','MS','MO','MT','NE','NV','NH','NJ',
  'NM','NY','NC','ND','OH','OK','OR','PA','RI','SC','SD','TN','TX','UT','VT',
  'VA','WA','WV','WI','WY',
];

type Tab = 'lanes' | 'brokers';
type LaneSortKey = 'lane' | 'avgRate' | 'avgMarginPct' | 'loadCount' | 'trendDirection' | 'lastSeen';
type BrokerSortKey = 'brokerName' | 'reliabilityGrade' | 'loadsCompleted' | 'avgDetentionHours' | 'ontimePickupPct' | 'rateAccuracyPct' | 'tonuCount';

const GRADE_COLORS: Record<string, string> = {
  A: 'bg-emerald-500 text-black',
  B: 'bg-green-500 text-black',
  C: 'bg-amber-500 text-black',
  D: 'bg-orange-500 text-black',
  F: 'bg-red-500 text-white',
  U: 'bg-slate-600 text-white',
};

function gradeRank(grade: string): number {
  const order: Record<string, number> = { A: 0, B: 1, C: 2, D: 3, F: 4, U: 5 };
  return order[grade] ?? 6;
}

function relativeDate(iso: string): string {
  const now = new Date();
  const then = new Date(iso);
  const diffMs = now.getTime() - then.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
  if (diffDays === 0) return 'Today';
  if (diffDays === 1) return 'Yesterday';
  if (diffDays < 7) return `${diffDays}d ago`;
  if (diffDays < 30) return `${Math.floor(diffDays / 7)}w ago`;
  return `${Math.floor(diffDays / 30)}mo ago`;
}

export default function AnalyticsDashboard() {
  const [tab, setTab] = useState<Tab>('lanes');

  // Lane state
  const [lanes, setLanes] = useState<LaneHistory[]>([]);
  const [lanesLoading, setLanesLoading] = useState(false);
  const [lanesError, setLanesError] = useState<string | null>(null);
  const [originFilter, setOriginFilter] = useState('');
  const [destFilter, setDestFilter] = useState('');
  const [laneSortKey, setLaneSortKey] = useState<LaneSortKey>('avgRate');
  const [laneSortAsc, setLaneSortAsc] = useState(false);

  // Broker state
  const [brokers, setBrokers] = useState<BrokerHistory[]>([]);
  const [brokersLoading, setBrokersLoading] = useState(false);
  const [brokersError, setBrokersError] = useState<string | null>(null);
  const [brokerSortKey, setBrokerSortKey] = useState<BrokerSortKey>('reliabilityGrade');
  const [brokerSortAsc, setBrokerSortAsc] = useState(true);

  const fetchLanes = useCallback(async () => {
    setLanesLoading(true);
    setLanesError(null);
    try {
      const data = await getLaneHistory(originFilter || undefined, destFilter || undefined);
      setLanes(data);
    } catch (err: any) {
      setLanesError(err.message ?? 'Failed to fetch lane history');
    } finally {
      setLanesLoading(false);
    }
  }, [originFilter, destFilter]);

  const fetchBrokers = useCallback(async () => {
    setBrokersLoading(true);
    setBrokersError(null);
    try {
      const data = await getBrokerHistory();
      setBrokers(data);
    } catch (err: any) {
      setBrokersError(err.message ?? 'Failed to fetch broker history');
    } finally {
      setBrokersLoading(false);
    }
  }, []);

  useEffect(() => {
    if (tab === 'lanes') fetchLanes();
    else fetchBrokers();
  }, [tab, fetchLanes, fetchBrokers]);

  // Sorting helpers
  function handleLaneSort(key: LaneSortKey) {
    if (laneSortKey === key) {
      setLaneSortAsc(!laneSortAsc);
    } else {
      setLaneSortKey(key);
      setLaneSortAsc(key === 'lane');
    }
  }

  function handleBrokerSort(key: BrokerSortKey) {
    if (brokerSortKey === key) {
      setBrokerSortAsc(!brokerSortAsc);
    } else {
      setBrokerSortKey(key);
      setBrokerSortAsc(key === 'brokerName');
    }
  }

  const sortedLanes = [...lanes].sort((a, b) => {
    const dir = laneSortAsc ? 1 : -1;
    switch (laneSortKey) {
      case 'lane': {
        const aLane = `${a.originCity}, ${a.originState} → ${a.destinationCity}, ${a.destinationState}`;
        const bLane = `${b.originCity}, ${b.originState} → ${b.destinationCity}, ${b.destinationState}`;
        return dir * aLane.localeCompare(bLane);
      }
      case 'avgRate': return dir * (a.avgRate - b.avgRate);
      case 'avgMarginPct': return dir * (a.avgMarginPct - b.avgMarginPct);
      case 'loadCount': return dir * (a.loadCount - b.loadCount);
      case 'trendDirection': {
        const order = { up: 0, stable: 1, down: 2 };
        return dir * (order[a.trendDirection] - order[b.trendDirection]);
      }
      case 'lastSeen': return dir * (new Date(a.lastSeen).getTime() - new Date(b.lastSeen).getTime());
      default: return 0;
    }
  });

  const sortedBrokers = [...brokers].sort((a, b) => {
    const dir = brokerSortAsc ? 1 : -1;
    switch (brokerSortKey) {
      case 'brokerName': return dir * a.brokerName.localeCompare(b.brokerName);
      case 'reliabilityGrade': return dir * (gradeRank(a.reliabilityGrade) - gradeRank(b.reliabilityGrade));
      case 'loadsCompleted': return dir * (a.loadsCompleted - b.loadsCompleted);
      case 'avgDetentionHours': return dir * (a.avgDetentionHours - b.avgDetentionHours);
      case 'ontimePickupPct': return dir * (a.ontimePickupPct - b.ontimePickupPct);
      case 'rateAccuracyPct': return dir * (a.rateAccuracyPct - b.rateAccuracyPct);
      case 'tonuCount': return dir * (a.tonuCount - b.tonuCount);
      default: return 0;
    }
  });

  const SortHeader = ({ label, sortKey, currentKey, onClick }: { label: string; sortKey: string; currentKey: string; onClick: () => void }) => (
    <th
      className="px-6 py-4 cursor-pointer select-none group"
      onClick={onClick}
    >
      <div className="flex items-center gap-1">
        {label}
        <ArrowUpDown size={12} className={`transition-colors ${currentKey === sortKey ? 'text-amber-500' : 'text-slate-700 group-hover:text-slate-500'}`} />
      </div>
    </th>
  );

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden">
      {/* Header with toggle tabs */}
      <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-900/50">
        <h2 className="text-lg font-bold text-white flex items-center gap-2">
          <BarChart3 size={18} className="text-slate-500" />
          Analytics Dashboard
        </h2>
        <div className="flex bg-slate-950 rounded-lg p-1 border border-slate-800">
          <button
            onClick={() => setTab('lanes')}
            className={`px-4 py-1.5 text-[10px] font-black uppercase tracking-wider rounded-md transition-all flex items-center gap-1.5 ${
              tab === 'lanes' ? 'bg-amber-500 text-black' : 'text-slate-500 hover:text-white'
            }`}
          >
            <BarChart3 size={12} />
            Lanes
          </button>
          <button
            onClick={() => setTab('brokers')}
            className={`px-4 py-1.5 text-[10px] font-black uppercase tracking-wider rounded-md transition-all flex items-center gap-1.5 ${
              tab === 'brokers' ? 'bg-amber-500 text-black' : 'text-slate-500 hover:text-white'
            }`}
          >
            <Users size={12} />
            Brokers
          </button>
        </div>
      </div>

      {/* Lanes Tab */}
      {tab === 'lanes' && (
        <>
          {/* Filter row */}
          <div className="px-6 py-3 border-b border-slate-800 flex items-center gap-4 bg-slate-950/30">
            <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Filter:</span>
            <div className="space-y-0.5">
              <label className="block text-[10px] font-bold text-slate-600 uppercase tracking-widest">Origin State</label>
              <select
                value={originFilter}
                onChange={(e) => setOriginFilter(e.target.value)}
                className="bg-transparent text-sm font-semibold text-white focus:outline-none cursor-pointer"
              >
                <option value="" className="bg-slate-900">All</option>
                {US_STATES.map(s => <option key={s} value={s} className="bg-slate-900">{s}</option>)}
              </select>
            </div>
            <div className="space-y-0.5">
              <label className="block text-[10px] font-bold text-slate-600 uppercase tracking-widest">Destination State</label>
              <select
                value={destFilter}
                onChange={(e) => setDestFilter(e.target.value)}
                className="bg-transparent text-sm font-semibold text-white focus:outline-none cursor-pointer"
              >
                <option value="" className="bg-slate-900">All</option>
                {US_STATES.map(s => <option key={s} value={s} className="bg-slate-900">{s}</option>)}
              </select>
            </div>
          </div>

          {/* Lane table */}
          <div className="overflow-x-auto">
            {lanesLoading ? (
              <div className="px-6 py-12 text-center">
                <p className="text-sm text-slate-500 animate-pulse">Loading lane data...</p>
              </div>
            ) : lanesError ? (
              <div className="px-6 py-12 text-center">
                <p className="text-sm text-red-500">{lanesError}</p>
              </div>
            ) : sortedLanes.length === 0 ? (
              <div className="px-6 py-12 text-center">
                <BarChart3 size={32} className="text-slate-700 mx-auto mb-3" />
                <p className="text-sm text-slate-500">No lane data yet. As you import and score loads, lane averages will build automatically.</p>
              </div>
            ) : (
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="text-[10px] font-bold text-slate-500 uppercase tracking-widest border-b border-slate-800">
                    <SortHeader label="Lane" sortKey="lane" currentKey={laneSortKey} onClick={() => handleLaneSort('lane')} />
                    <SortHeader label="Avg Rate ($)" sortKey="avgRate" currentKey={laneSortKey} onClick={() => handleLaneSort('avgRate')} />
                    <SortHeader label="Avg Margin (%)" sortKey="avgMarginPct" currentKey={laneSortKey} onClick={() => handleLaneSort('avgMarginPct')} />
                    <SortHeader label="Loads Seen / Booked" sortKey="loadCount" currentKey={laneSortKey} onClick={() => handleLaneSort('loadCount')} />
                    <SortHeader label="Trend" sortKey="trendDirection" currentKey={laneSortKey} onClick={() => handleLaneSort('trendDirection')} />
                    <SortHeader label="Last Seen" sortKey="lastSeen" currentKey={laneSortKey} onClick={() => handleLaneSort('lastSeen')} />
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800">
                  {sortedLanes.map((lane, i) => (
                    <tr key={i} className="hover:bg-slate-800/50 transition-colors">
                      <td className="px-6 py-4">
                        <span className="text-sm font-bold text-white">
                          {lane.originCity}, {lane.originState}
                        </span>
                        <span className="text-slate-600 mx-2">&rarr;</span>
                        <span className="text-sm font-bold text-white">
                          {lane.destinationCity}, {lane.destinationState}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-sm font-bold text-white">${lane.avgRate.toLocaleString()}</td>
                      <td className="px-6 py-4">
                        <span className={`text-sm font-bold ${lane.avgMarginPct >= 0 ? 'text-emerald-500' : 'text-red-500'}`}>
                          {lane.avgMarginPct.toFixed(1)}%
                        </span>
                      </td>
                      <td className="px-6 py-4 text-sm text-slate-400">
                        {lane.loadCount} / {lane.bookedCount}
                      </td>
                      <td className="px-6 py-4">
                        {lane.trendDirection === 'up' && <TrendingUp size={16} className="text-emerald-500" />}
                        {lane.trendDirection === 'down' && <TrendingDown size={16} className="text-red-500" />}
                        {lane.trendDirection === 'stable' && <Minus size={16} className="text-slate-500" />}
                      </td>
                      <td className="px-6 py-4 text-xs text-slate-500">{relativeDate(lane.lastSeen)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </>
      )}

      {/* Brokers Tab */}
      {tab === 'brokers' && (
        <div className="overflow-x-auto">
          {brokersLoading ? (
            <div className="px-6 py-12 text-center">
              <p className="text-sm text-slate-500 animate-pulse">Loading broker data...</p>
            </div>
          ) : brokersError ? (
            <div className="px-6 py-12 text-center">
              <p className="text-sm text-red-500">{brokersError}</p>
            </div>
          ) : sortedBrokers.length === 0 ? (
            <div className="px-6 py-12 text-center">
              <Users size={32} className="text-slate-700 mx-auto mb-3" />
              <p className="text-sm text-slate-500">No broker data yet. Submit feedback after completing loads to build broker profiles.</p>
            </div>
          ) : (
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="text-[10px] font-bold text-slate-500 uppercase tracking-widest border-b border-slate-800">
                  <SortHeader label="Broker Name" sortKey="brokerName" currentKey={brokerSortKey} onClick={() => handleBrokerSort('brokerName')} />
                  <SortHeader label="Grade" sortKey="reliabilityGrade" currentKey={brokerSortKey} onClick={() => handleBrokerSort('reliabilityGrade')} />
                  <SortHeader label="Loads Completed" sortKey="loadsCompleted" currentKey={brokerSortKey} onClick={() => handleBrokerSort('loadsCompleted')} />
                  <SortHeader label="Avg Detention (hrs)" sortKey="avgDetentionHours" currentKey={brokerSortKey} onClick={() => handleBrokerSort('avgDetentionHours')} />
                  <SortHeader label="On-Time %" sortKey="ontimePickupPct" currentKey={brokerSortKey} onClick={() => handleBrokerSort('ontimePickupPct')} />
                  <SortHeader label="Rate Accuracy %" sortKey="rateAccuracyPct" currentKey={brokerSortKey} onClick={() => handleBrokerSort('rateAccuracyPct')} />
                  <SortHeader label="TONU Count" sortKey="tonuCount" currentKey={brokerSortKey} onClick={() => handleBrokerSort('tonuCount')} />
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                {sortedBrokers.map((broker, i) => (
                  <tr key={i} className="hover:bg-slate-800/50 transition-colors">
                    <td className="px-6 py-4 text-sm font-bold text-white">{broker.brokerName}</td>
                    <td className="px-6 py-4">
                      <span className={`inline-flex items-center justify-center w-7 h-7 rounded-full text-xs font-black ${GRADE_COLORS[broker.reliabilityGrade] ?? GRADE_COLORS.U}`}>
                        {broker.reliabilityGrade}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-sm text-slate-400">{broker.loadsCompleted}</td>
                    <td className="px-6 py-4 text-sm text-slate-400">{broker.avgDetentionHours.toFixed(1)}</td>
                    <td className="px-6 py-4">
                      <span className={`text-sm font-bold ${broker.ontimePickupPct >= 90 ? 'text-emerald-500' : broker.ontimePickupPct >= 70 ? 'text-amber-500' : 'text-red-500'}`}>
                        {broker.ontimePickupPct.toFixed(0)}%
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <span className={`text-sm font-bold ${broker.rateAccuracyPct >= 95 ? 'text-emerald-500' : broker.rateAccuracyPct >= 85 ? 'text-amber-500' : 'text-red-500'}`}>
                        {broker.rateAccuracyPct.toFixed(0)}%
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <span className={`text-sm font-bold ${broker.tonuCount === 0 ? 'text-slate-400' : 'text-red-500'}`}>
                        {broker.tonuCount}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  );
}
