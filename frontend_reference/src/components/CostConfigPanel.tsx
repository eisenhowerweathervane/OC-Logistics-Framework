import React, { useEffect, useState, useCallback } from 'react';
import { getCostConfig, updateCostConfig, getScorerConfig, updateScorerConfig } from '../services/api';
import { CostConfig, ScorerConfig } from '../types';
import { ChevronDown, ChevronRight, DollarSign, Truck, Fuel, Save, Settings2 } from 'lucide-react';

interface CostConfigPanelProps {
  isOpen: boolean;
  onToggle: () => void;
}

const DEFAULT_COST_CONFIG: CostConfig = {
  truckLeaseMonthly: 4000,
  insuranceMonthly: 1800,
  overheadMonthly: 500,
  maintReserveMonthly: 0,
  expectedMonthlyMiles: 8000,
  driverPayMode: 'base_plus_mile',
  driverBaseWeekly: 0,
  driverPerMile: 0,
  factoringFeePct: 3.0,
  fuelMpg: 6.5,
  defaultFuelPrice: 3.85,
};

const DEFAULT_SCORER_CONFIG: ScorerConfig = {
  financialWeight: 50,
  laneWeight: 15,
  brokerWeight: 15,
  strategicWeight: 20,
};

export default function CostConfigPanel({ isOpen, onToggle }: CostConfigPanelProps) {
  const [config, setConfig] = useState<CostConfig>(DEFAULT_COST_CONFIG);
  const [scorer, setScorer] = useState<ScorerConfig>(DEFAULT_SCORER_CONFIG);
  const [scorerOpen, setScorerOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [scorerSaving, setScorerSaving] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  // Load config from API on mount
  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const [costData, scorerData] = await Promise.all([getCostConfig(), getScorerConfig()]);
        if (!cancelled) {
          setConfig(costData);
          setScorer(scorerData);
          setLoadError(null);
        }
      } catch (err) {
        if (!cancelled) {
          setLoadError('Failed to load config — using defaults');
        }
      }
    }
    load();
    return () => { cancelled = true; };
  }, []);

  // Debounced save for cost config
  const saveCostConfig = useCallback(async (updated: CostConfig) => {
    setSaving(true);
    try {
      const result = await updateCostConfig(updated);
      setConfig(result);
    } catch {
      // silently fail — user sees stale state
    } finally {
      setSaving(false);
    }
  }, []);

  // Debounce timer ref
  const debounceRef = React.useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleChange = (key: keyof CostConfig, value: number | string) => {
    const updated = { ...config, [key]: value };
    setConfig(updated);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => saveCostConfig(updated), 600);
  };

  const handleSaveScorer = async () => {
    setScorerSaving(true);
    try {
      const result = await updateScorerConfig(scorer);
      setScorer(result);
    } catch {
      // ignore
    } finally {
      setScorerSaving(false);
    }
  };

  // Calculations
  const miles = config.expectedMonthlyMiles || 1;
  const truckCpm = config.truckLeaseMonthly / miles;
  const insuranceCpm = config.insuranceMonthly / miles;
  const overheadCpm = config.overheadMonthly / miles;
  const maintCpm = config.maintReserveMonthly / miles;
  const fuelCpm = config.defaultFuelPrice / (config.fuelMpg || 1);

  // Driver cost per mile
  let driverCpm = 0;
  if (config.driverPayMode === 'base_plus_mile') {
    driverCpm = (config.driverBaseWeekly * 52 / 12) / miles + config.driverPerMile;
  } else if (config.driverPayMode === 'per_mile_only') {
    driverCpm = config.driverPerMile;
  } else {
    // base_only
    driverCpm = (config.driverBaseWeekly * 52 / 12) / miles;
  }

  const baseCpm = truckCpm + insuranceCpm + overheadCpm + maintCpm + fuelCpm + driverCpm;
  const minMargin = 15; // reasonable default
  const floorRpm = baseCpm / (1 - minMargin / 100) / (1 - config.factoringFeePct / 100);

  const scorerSum = scorer.financialWeight + scorer.laneWeight + scorer.brokerWeight + scorer.strategicWeight;

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden mb-6">
      {/* Header */}
      <button
        onClick={onToggle}
        className="w-full px-6 py-4 flex items-center justify-between hover:bg-slate-800/50 transition-colors"
      >
        <div className="flex items-center gap-3">
          <Settings2 className="w-5 h-5 text-amber-500" />
          <h2 className="text-lg font-semibold text-white">Cost Configuration</h2>
          <div className="px-3 py-1 bg-amber-500/10 border border-amber-500/20 rounded-full">
            <span className="text-xs font-bold text-amber-500 uppercase tracking-wider">
              Base CPM: ${baseCpm.toFixed(2)} | Floor RPM: ${floorRpm.toFixed(2)}
            </span>
          </div>
          {saving && (
            <span className="text-xs text-slate-500 animate-pulse">Saving...</span>
          )}
        </div>
        {isOpen ? <ChevronDown className="text-slate-400" /> : <ChevronRight className="text-slate-400" />}
      </button>

      {isOpen && (
        <div className="px-6 pb-6 border-t border-slate-800 pt-6 space-y-8">
          {loadError && (
            <div className="px-4 py-2 bg-amber-500/10 border border-amber-500/20 rounded-lg text-sm text-amber-400">
              {loadError}
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            {/* Section 1: Monthly Fixed Costs */}
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                <Truck className="w-4 h-4 text-amber-500" />
                <h3 className="text-xs font-bold text-slate-500 uppercase tracking-widest">Monthly Fixed Costs</h3>
              </div>

              <CostInput
                label="Truck Lease ($/month)"
                value={config.truckLeaseMonthly}
                onChange={(v) => handleChange('truckLeaseMonthly', v)}
                step={100}
                suffix={`$${config.truckLeaseMonthly.toLocaleString()}/mo = $${truckCpm.toFixed(2)}/mi`}
              />
              <CostInput
                label="Insurance ($/month)"
                value={config.insuranceMonthly}
                onChange={(v) => handleChange('insuranceMonthly', v)}
                step={100}
                suffix={`$${config.insuranceMonthly.toLocaleString()}/mo = $${insuranceCpm.toFixed(2)}/mi`}
              />
              <CostInput
                label="Overhead ($/month)"
                value={config.overheadMonthly}
                onChange={(v) => handleChange('overheadMonthly', v)}
                step={50}
                suffix={`$${config.overheadMonthly.toLocaleString()}/mo = $${overheadCpm.toFixed(2)}/mi`}
              />
              <CostInput
                label="Maintenance Reserve ($/month)"
                value={config.maintReserveMonthly}
                onChange={(v) => handleChange('maintReserveMonthly', v)}
                step={50}
                suffix={`$${config.maintReserveMonthly.toLocaleString()}/mo = $${maintCpm.toFixed(2)}/mi`}
              />
              <CostInput
                label="Expected Monthly Miles"
                value={config.expectedMonthlyMiles}
                onChange={(v) => handleChange('expectedMonthlyMiles', v)}
                step={500}
              />
            </div>

            {/* Section 2: Driver Pay */}
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                <DollarSign className="w-4 h-4 text-emerald-500" />
                <h3 className="text-xs font-bold text-slate-500 uppercase tracking-widest">Driver Pay</h3>
              </div>

              {/* Mode selector */}
              <div className="flex gap-1 bg-slate-950 border border-slate-700 rounded-lg p-1">
                {([
                  { key: 'base_plus_mile' as const, label: 'Base + Per Mile' },
                  { key: 'per_mile_only' as const, label: 'Per Mile Only' },
                  { key: 'base_only' as const, label: 'Base Only' },
                ]).map(({ key, label }) => (
                  <button
                    key={key}
                    onClick={() => handleChange('driverPayMode', key)}
                    className={`flex-1 px-2 py-1.5 text-xs font-medium rounded-md transition-colors ${
                      config.driverPayMode === key
                        ? 'bg-amber-500 text-slate-950'
                        : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    {label}
                  </button>
                ))}
              </div>

              {/* Conditional fields */}
              {(config.driverPayMode === 'base_plus_mile' || config.driverPayMode === 'base_only') && (
                <CostInput
                  label="Weekly Base ($)"
                  value={config.driverBaseWeekly}
                  onChange={(v) => handleChange('driverBaseWeekly', v)}
                  step={25}
                />
              )}
              {(config.driverPayMode === 'base_plus_mile' || config.driverPayMode === 'per_mile_only') && (
                <CostInput
                  label="Per Mile ($)"
                  value={config.driverPerMile}
                  onChange={(v) => handleChange('driverPerMile', v)}
                  step={0.01}
                />
              )}

              <div className="px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg">
                <span className="text-xs text-slate-400">Driver cost: </span>
                <span className="text-sm font-semibold text-emerald-400">${driverCpm.toFixed(3)}/mi</span>
              </div>
            </div>

            {/* Section 3: Other Costs */}
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                <Fuel className="w-4 h-4 text-amber-500" />
                <h3 className="text-xs font-bold text-slate-500 uppercase tracking-widest">Other Costs</h3>
              </div>

              <CostInput
                label="Factoring Fee (%)"
                value={config.factoringFeePct}
                onChange={(v) => handleChange('factoringFeePct', v)}
                step={0.1}
              />
              <CostInput
                label="Fuel MPG"
                value={config.fuelMpg}
                onChange={(v) => handleChange('fuelMpg', v)}
                step={0.1}
              />
              <CostInput
                label="Default Fuel Price ($/gal)"
                value={config.defaultFuelPrice}
                onChange={(v) => handleChange('defaultFuelPrice', v)}
                step={0.05}
              />

              <div className="px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg">
                <span className="text-xs text-slate-400">Fuel cost: </span>
                <span className="text-sm font-semibold text-amber-400">${fuelCpm.toFixed(3)}/mi</span>
              </div>
            </div>
          </div>

          {/* Section 4: Summary Bar */}
          <div className="flex items-center gap-6 px-5 py-4 bg-slate-950 border border-slate-800 rounded-xl">
            <div>
              <span className="text-xs text-slate-500 uppercase tracking-wider">Total Base CPM</span>
              <p className="text-xl font-bold text-white">${baseCpm.toFixed(3)}</p>
            </div>
            <div className="h-10 w-px bg-slate-800" />
            <div>
              <span className="text-xs text-slate-500 uppercase tracking-wider">Floor RPM (15% margin)</span>
              <p className="text-xl font-bold text-amber-500">${floorRpm.toFixed(3)}</p>
            </div>
            <div className="h-10 w-px bg-slate-800" />
            <div className="text-xs text-slate-500 space-y-0.5">
              <p>Truck: ${truckCpm.toFixed(3)} | Insurance: ${insuranceCpm.toFixed(3)}</p>
              <p>Overhead: ${overheadCpm.toFixed(3)} | Maint: ${maintCpm.toFixed(3)}</p>
              <p>Driver: ${driverCpm.toFixed(3)} | Fuel: ${fuelCpm.toFixed(3)}</p>
            </div>
          </div>

          {/* Section 5: Scorer Weights (collapsible) */}
          <div className="border border-slate-800 rounded-xl overflow-hidden">
            <button
              onClick={() => setScorerOpen(!scorerOpen)}
              className="w-full px-5 py-3 flex items-center justify-between hover:bg-slate-800/50 transition-colors"
            >
              <div className="flex items-center gap-2">
                <Settings2 className="w-4 h-4 text-slate-400" />
                <h3 className="text-sm font-semibold text-slate-200">Scorer Weights</h3>
                {scorerSum !== 100 && (
                  <span className="px-2 py-0.5 bg-red-500/10 border border-red-500/30 rounded-full text-xs text-red-400">
                    Sum: {scorerSum}% (must be 100%)
                  </span>
                )}
              </div>
              {scorerOpen ? <ChevronDown className="w-4 h-4 text-slate-400" /> : <ChevronRight className="w-4 h-4 text-slate-400" />}
            </button>

            {scorerOpen && (
              <div className="px-5 pb-5 border-t border-slate-800 pt-4 space-y-4">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <ScorerInput
                    label="Financial"
                    value={scorer.financialWeight}
                    onChange={(v) => setScorer({ ...scorer, financialWeight: v })}
                  />
                  <ScorerInput
                    label="Lane"
                    value={scorer.laneWeight}
                    onChange={(v) => setScorer({ ...scorer, laneWeight: v })}
                  />
                  <ScorerInput
                    label="Broker"
                    value={scorer.brokerWeight}
                    onChange={(v) => setScorer({ ...scorer, brokerWeight: v })}
                  />
                  <ScorerInput
                    label="Strategic"
                    value={scorer.strategicWeight}
                    onChange={(v) => setScorer({ ...scorer, strategicWeight: v })}
                  />
                </div>

                {scorerSum !== 100 && (
                  <p className="text-sm text-red-400">
                    Weights must sum to 100%. Current sum: {scorerSum}%
                  </p>
                )}

                <button
                  onClick={handleSaveScorer}
                  disabled={scorerSaving || scorerSum !== 100}
                  className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                    scorerSum === 100
                      ? 'bg-amber-500 text-slate-950 hover:bg-amber-400'
                      : 'bg-slate-700 text-slate-500 cursor-not-allowed'
                  }`}
                >
                  <Save className="w-4 h-4" />
                  {scorerSaving ? 'Saving...' : 'Save Weights'}
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// =============================================================================
// Sub-components
// =============================================================================

function CostInput({
  label,
  value,
  onChange,
  step = 1,
  suffix,
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
  step?: number;
  suffix?: string;
}) {
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
      {suffix && (
        <p className="text-xs text-slate-500">{suffix}</p>
      )}
    </div>
  );
}

function ScorerInput({
  label,
  value,
  onChange,
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
}) {
  return (
    <div className="space-y-1.5">
      <label className="block text-xs font-medium text-slate-400">{label} (%)</label>
      <input
        type="range"
        min={0}
        max={100}
        step={5}
        value={value}
        onChange={(e) => onChange(parseInt(e.target.value, 10))}
        className="w-full accent-amber-500"
      />
      <div className="flex justify-between text-xs text-slate-500">
        <span>0</span>
        <span className="text-slate-200 font-semibold">{value}%</span>
        <span>100</span>
      </div>
    </div>
  );
}
