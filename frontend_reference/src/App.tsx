import React, { useState, useEffect, useCallback } from 'react';
import { Load, Assumptions, ScoredLoad, OptimizedChain } from './types';
import { DEFAULT_ASSUMPTIONS } from './constants';
import { generateRandomLoads } from './utils/generator';
import * as api from './services/api';

import ControlBar from './components/ControlBar';
import AssumptionsPanel from './components/AssumptionsPanel';
import OptimizedChainView from './components/OptimizedChainView';
import ComparisonView from './components/ComparisonView';
import LoadPoolTable from './components/LoadPoolTable';
import AddLoadModal from './components/AddLoadModal';

export default function App() {
  // State
  const [loads, setLoads] = useState<Load[]>([]);
  const [scoredLoads, setScoredLoads] = useState<ScoredLoad[]>([]);
  const [assumptions, setAssumptions] = useState<Assumptions>(DEFAULT_ASSUMPTIONS);
  const [truckLocation, setTruckLocation] = useState('Cleveland, OH');
  const [hosRemaining, setHosRemaining] = useState(11);
  const [isAssumptionsOpen, setIsAssumptionsOpen] = useState(false);
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [apiConnected, setApiConnected] = useState(false);

  const [optimizedChain, setOptimizedChain] = useState<OptimizedChain | null>(null);
  const [naiveChain, setNaiveChain] = useState<OptimizedChain | null>(null);
  const [manualChainIds, setManualChainIds] = useState<string[]>([]);

  // Check API connection on mount
  useEffect(() => {
    api.healthCheck().then(connected => {
      setApiConnected(connected);
      if (connected) {
        console.log('✅ Connected to backend API at', api.API_BASE_URL);
      } else {
        console.warn('⚠️ Backend API not available, some features may not work');
      }
    });
  }, []);

  // Score loads via API
  const scoreLoadsViaApi = useCallback(async (loadsToScore: Load[]) => {
    if (!apiConnected) {
      console.warn('API not connected, cannot score loads');
      return;
    }

    setIsLoading(true);
    try {
      const scored: ScoredLoad[] = [];

      for (const load of loadsToScore) {
        // Parse origin/destination into city/state
        const [originCity, originState] = load.origin.split(', ');
        const [destCity, destState] = load.destination.split(', ');

        // Convert assumptions to API format
        const apiAssumptions = {
          fuelPrice: assumptions.fuelPrice,
          mpg: assumptions.mpg,
          driverPay: assumptions.driverPay,
          truckLease: assumptions.truckLease,
          insurance: assumptions.insurance,
          maintReserve: assumptions.maintReserve,
          overhead: assumptions.overhead,
          factoringFee: assumptions.factoringFee,
          detentionRate: assumptions.detentionRate,
          maxDeadheadPct: assumptions.maxDeadhead,
          minMarginPct: assumptions.minMargin,
          targetMarginPct: assumptions.targetMargin,
          avgSpeed: assumptions.avgSpeed,
          loadUnloadTime: assumptions.loadUnloadTime,
          homeBase: assumptions.homeBase,
        };

        try {
          const result = await api.scoreLoad({
            originCity: originCity || '',
            originState: originState || '',
            destinationCity: destCity || '',
            destinationState: destState || '',
            rateTotal: load.rate,
            mileage: load.miles,
            weight: load.weight,
          }, apiAssumptions);

          // Transform API response to ScoredLoad format
          scored.push({
            ...load,
            deadheadMiles: result.deadheadMiles || 0,
            totalMiles: result.totalMiles || load.miles,
            totalCost: result.totalCost || 0,
            netRevenue: result.netRevenue || 0,
            profit: result.profit || 0,
            marginPct: result.marginPct || 0,
            rpm: result.rpm || 0,
            allInRpm: result.allInRpm || 0,
            driveHours: result.driveHours || 0,
            totalHours: result.totalHours || 0,
            profitPerHour: result.profitPerHour || 0,
            score: result.score || 0,
            action: result.action || 'PASS',
            estimatedDelivery: load.deliveryDeadline,
          });
        } catch (err) {
          console.error(`Failed to score load ${load.id}:`, err);
          // Add with default values on error
          scored.push({
            ...load,
            deadheadMiles: 0,
            totalMiles: load.miles,
            totalCost: 0,
            netRevenue: 0,
            profit: 0,
            marginPct: 0,
            rpm: 0,
            allInRpm: 0,
            driveHours: 0,
            totalHours: 0,
            profitPerHour: 0,
            score: 0,
            action: 'PASS',
            estimatedDelivery: load.deliveryDeadline,
          });
        }
      }

      setScoredLoads(scored);
      console.log(`✅ Scored ${scored.length} loads via API`);
    } catch (error) {
      console.error('Failed to score loads:', error);
    } finally {
      setIsLoading(false);
    }
  }, [apiConnected, assumptions]);

  // Generate and score loads
  const handleGenerateLoads = useCallback(async () => {
    const newLoads = generateRandomLoads(50);
    setLoads(newLoads);
    await scoreLoadsViaApi(newLoads);
  }, [scoreLoadsViaApi]);

  // Initial Load Generation
  useEffect(() => {
    if (apiConnected) {
      handleGenerateLoads();
    }
  }, [apiConnected]); // eslint-disable-line react-hooks/exhaustive-deps

  // Re-score when assumptions or truck location changes
  useEffect(() => {
    if (loads.length > 0 && apiConnected) {
      scoreLoadsViaApi(loads);
    }
  }, [assumptions, truckLocation]); // eslint-disable-line react-hooks/exhaustive-deps

  // Run Optimizer via API
  const handleRunOptimizer = async () => {
    if (!apiConnected) {
      console.warn('API not connected, cannot optimize');
      return;
    }

    setIsLoading(true);
    try {
      // For now, we'll call the greedy chain endpoint with scored load data
      // The backend optimizer expects load_ids from database, so we need to
      // create loads first or use a different approach

      // Convert assumptions to API format
      const apiAssumptions = {
        fuelPrice: assumptions.fuelPrice,
        mpg: assumptions.mpg,
        driverPay: assumptions.driverPay,
        truckLease: assumptions.truckLease,
        insurance: assumptions.insurance,
        maintReserve: assumptions.maintReserve,
        overhead: assumptions.overhead,
        factoringFee: assumptions.factoringFee,
        detentionRate: assumptions.detentionRate,
        maxDeadheadPct: assumptions.maxDeadhead,
        minMarginPct: assumptions.minMargin,
        targetMarginPct: assumptions.targetMargin,
        avgSpeed: assumptions.avgSpeed,
        loadUnloadTime: assumptions.loadUnloadTime,
        homeBase: assumptions.homeBase,
      };

      // Create loads in database first to get IDs
      const loadIds: number[] = [];
      for (const load of loads.slice(0, 20)) { // Limit to 20 for performance
        const [originCity, originState] = load.origin.split(', ');
        const [destCity, destState] = load.destination.split(', ');

        try {
          const created = await api.createLoad({
            originCity: originCity || '',
            originState: originState || '',
            destinationCity: destCity || '',
            destinationState: destState || '',
            rateTotal: load.rate,
            mileage: load.miles,
            weight: load.weight,
            commodity: load.commodity,
          }, apiAssumptions);

          if (created.id) {
            loadIds.push(created.id);
          }
        } catch (err) {
          // Might be duplicate, continue
          console.warn(`Could not create load: ${err}`);
        }
      }

      if (loadIds.length > 0) {
        // Now run optimizer with the load IDs
        const result = await api.optimizeChain(
          loadIds,
          truckLocation,
          hosRemaining,
          assumptions.daysAway,
          apiAssumptions
        );

        // API returns { optimized: { legs, summary }, greedy: { legs, summary }, profitDifference }
        const optimizedData = result.optimized || result;
        const greedyData = result.greedy;

        // Helper to transform chain data to OptimizedChain format
        const transformChain = (data: any): OptimizedChain => ({
          legs: (data.legs || []).map((leg: any) => ({
            load: leg.load ? {
              id: leg.load.id?.toString() || '',
              origin: `${leg.load.originCity}, ${leg.load.originState}`,
              destination: `${leg.load.destinationCity}, ${leg.load.destinationState}`,
              miles: leg.load.mileage || 0,
              rate: leg.load.rateTotal || 0,
              weight: leg.load.weight || 0,
              commodity: leg.load.commodity || '',
              detentionHours: 0,
              pickupWindowStart: new Date().toISOString(),
              deliveryDeadline: new Date().toISOString(),
            } : null,
            deadhead: leg.deadhead || 0,
            result: leg.result ? {
              ...leg.result,
              id: leg.result.id?.toString() || '',
              origin: `${leg.result.originCity || ''}, ${leg.result.originState || ''}`,
              destination: `${leg.result.destinationCity || ''}, ${leg.result.destinationState || ''}`,
              miles: leg.result.mileage || 0,
              rate: leg.result.rateTotal || 0,
              weight: leg.result.weight || 0,
              commodity: leg.result.commodity || '',
              detentionHours: 0,
              pickupWindowStart: new Date().toISOString(),
              deliveryDeadline: new Date().toISOString(),
              deadheadMiles: leg.result.deadheadMiles || 0,
              totalMiles: leg.result.totalMiles || 0,
              totalCost: leg.result.totalCost || 0,
              netRevenue: leg.result.netRevenue || 0,
              profit: leg.result.profit || 0,
              marginPct: leg.result.marginPct || 0,
              rpm: leg.result.rpm || 0,
              allInRpm: leg.result.allInRpm || 0,
              driveHours: leg.result.driveHours || 0,
              totalHours: leg.result.totalHours || 0,
              profitPerHour: leg.result.profitPerHour || 0,
              score: leg.result.score || 0,
              action: leg.result.action || 'PASS',
              estimatedDelivery: new Date().toISOString(),
            } : null,
            startTime: leg.startTime || new Date().toISOString(),
            endTime: leg.endTime || new Date().toISOString(),
            isOvernight: leg.isOvernight || false,
            isReturnHome: leg.isReturnHome || false,
          })),
          summary: {
            totalProfit: data.summary?.totalProfit || 0,
            totalRevenue: data.summary?.totalRevenue || 0,
            numLoads: data.summary?.numLoads || 0,
            totalDeadhead: data.summary?.totalDeadhead || 0,
            deadheadPct: data.summary?.deadheadPct || 0,
            totalHours: data.summary?.totalHours || 0,
            avgMargin: data.summary?.avgMargin || 0,
            profitPerHour: data.summary?.profitPerHour || 0,
            totalMiles: data.summary?.totalMiles || 0,
          },
        });

        const optimizedResult = transformChain(optimizedData);
        setOptimizedChain(optimizedResult);
        setManualChainIds(optimizedResult.legs.filter(l => l.load).map(l => l.load!.id));

        if (greedyData) {
          setNaiveChain(transformChain(greedyData));
        }

        console.log('✅ Optimization complete via API');
        console.log(`   HOS used: ${optimizedData.summary?.hosUsed || 0} / ${optimizedData.summary?.hosAvailable || 0} hours`);
      }
    } catch (error) {
      console.error('Optimization failed:', error);
    } finally {
      setIsLoading(false);
    }
  };

  // Manual Override
  const handleToggleLoad = (id: string) => {
    let newIds: string[];
    if (manualChainIds.includes(id)) {
      newIds = manualChainIds.filter(i => i !== id);
    } else {
      newIds = [...manualChainIds, id];
    }
    setManualChainIds(newIds);
  };

  // Add a new load via API
  const handleAddLoad = async (load: Load) => {
    const [originCity, originState] = load.origin.split(', ');
    const [destCity, destState] = load.destination.split(', ');

    try {
      await api.createLoad({
        originCity: originCity || '',
        originState: originState || '',
        destinationCity: destCity || '',
        destinationState: destState || '',
        rateTotal: load.rate,
        mileage: load.miles,
        weight: load.weight,
        commodity: load.commodity,
      });

      setLoads([load, ...loads]);
      await scoreLoadsViaApi([load, ...loads]);
      console.log('✅ Load created via API');
    } catch (error) {
      console.error('Failed to add load:', error);
      // Still add locally
      setLoads([load, ...loads]);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-200 font-sans selection:bg-amber-500/30">
      {/* API Status Banner */}
      {!apiConnected && (
        <div className="bg-amber-600 text-black text-center py-2 text-sm font-bold">
          ⚠️ Backend API not connected. Running in offline mode.
        </div>
      )}
      {isLoading && (
        <div className="bg-blue-600 text-white text-center py-2 text-sm font-bold">
          Loading... (Using Google Maps API for real distances)
        </div>
      )}

      <ControlBar
        truckLocation={truckLocation}
        setTruckLocation={setTruckLocation}
        hosRemaining={hosRemaining}
        setHosRemaining={setHosRemaining}
        daysAway={assumptions.daysAway}
        setDaysAway={(d) => setAssumptions(prev => ({ ...prev, daysAway: d }))}
        homeBase={assumptions.homeBase}
        setHomeBase={(h) => setAssumptions(prev => ({ ...prev, homeBase: h }))}
        onRunOptimizer={handleRunOptimizer}
        onAddLoad={() => setIsAddModalOpen(true)}
        onGenerateLoads={handleGenerateLoads}
      />

      <main className="max-w-7xl mx-auto px-6 py-8">
        <AssumptionsPanel
          assumptions={assumptions}
          setAssumptions={setAssumptions}
          isOpen={isAssumptionsOpen}
          setIsOpen={setIsAssumptionsOpen}
        />

        <div className="mb-12">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-2xl font-black text-white uppercase tracking-tight font-display">
              Optimized Dispatch Chain
              {apiConnected && <span className="ml-2 text-xs text-green-500 font-normal">(Live API)</span>}
            </h2>
            {optimizedChain && (
              <button
                onClick={() => { setOptimizedChain(null); setNaiveChain(null); setManualChainIds([]); }}
                className="text-xs font-bold text-slate-500 hover:text-white uppercase tracking-widest transition-colors"
              >
                Clear Results
              </button>
            )}
          </div>
          <OptimizedChainView chain={optimizedChain} assumptions={assumptions} />
        </div>

        <ComparisonView optimized={optimizedChain} naive={naiveChain} />

        <div className="mb-20">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-bold text-white">
              Load Pool ({scoredLoads.length} loads)
              {apiConnected && <span className="ml-2 text-xs text-green-500 font-normal">Scored via API</span>}
            </h2>
          </div>
          <LoadPoolTable
            loads={scoredLoads}
            includedInChain={manualChainIds}
            onToggleLoad={handleToggleLoad}
          />
        </div>
      </main>

      <AddLoadModal
        isOpen={isAddModalOpen}
        onClose={() => setIsAddModalOpen(false)}
        onAdd={handleAddLoad}
      />

      {/* Footer / Branding */}
      <footer className="border-t border-slate-900 py-12 px-6 text-center">
        <div className="flex items-center justify-center gap-2 mb-4">
          <div className="w-6 h-6 bg-slate-800 rounded flex items-center justify-center">
            <span className="text-[10px] font-black text-white">S</span>
          </div>
          <span className="text-sm font-bold text-slate-600 uppercase tracking-[0.3em]">Stratus Logistics LLC</span>
        </div>
        <p className="text-xs text-slate-700">© 2026 Stratus Dispatch Intelligence. All rights reserved.</p>
        {apiConnected && (
          <p className="text-xs text-green-600 mt-2">Connected to backend • Using Google Maps API for real distances</p>
        )}
      </footer>
    </div>
  );
}
