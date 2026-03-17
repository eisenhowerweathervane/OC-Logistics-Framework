import { Load, Assumptions, OptimizedChain, ChainLeg } from '../types';
import { calculateDistance, scoreLoad } from './math';

export function optimizeChain(
  allLoads: Load[], 
  startCity: string, 
  hosRemaining: number, 
  assumptions: Assumptions
): OptimizedChain {
  const totalDays = assumptions.daysAway + 1;
  const maxDriveableMiles = (hosRemaining + (assumptions.daysAway * 11)) * assumptions.avgSpeed;
  const beamWidth = 3;

  function build(currentCity: string, remainingLoads: Load[], milesUsed: number, currentTime: Date): ChainLeg[] {
    const candidates: { load: Load; dh: number; result: any; ranking: number }[] = [];

    for (const load of remainingLoads) {
      const dh = calculateDistance(currentCity, load.origin);
      // We need to ensure we can finish this load AND have enough miles left to potentially get home
      // (though we'll add the return leg even if it exceeds the limit, but we prefer chains that can get home)
      const distToHome = calculateDistance(load.destination, assumptions.homeBase);
      
      if (milesUsed + dh + load.miles + distToHome > maxDriveableMiles) {
        continue;
      }
      const result = scoreLoad(load, dh, assumptions);
      // Ranking: (profit_per_hour * 10) - (deadhead_miles * 0.5) - (dist_to_home * 0.1)
      const ranking = (result.profitPerHour * 10) - (dh * 0.5) - (distToHome * 0.1);
      candidates.push({ load, dh, result, ranking });
    }

    if (candidates.length === 0) {
      // End of chain, add return home leg if not already there
      if (currentCity !== assumptions.homeBase) {
        const dhToHome = calculateDistance(currentCity, assumptions.homeBase);
        const driveTime = dhToHome / assumptions.avgSpeed;
        const endTime = new Date(currentTime.getTime() + driveTime * 3600000);
        
        // Calculate cost of return deadhead
        const fuelCpm = assumptions.fuelPrice / assumptions.mpg;
        const totalCpm = fuelCpm + assumptions.driverPay + assumptions.truckLease + assumptions.insurance + assumptions.maintReserve + assumptions.overhead;
        const cost = dhToHome * totalCpm;

        return [{
          load: null,
          deadhead: dhToHome,
          result: {
            id: 'RETURN-HOME',
            origin: currentCity,
            destination: assumptions.homeBase,
            miles: 0,
            rate: 0,
            weight: 0,
            commodity: 'DEADHEAD',
            detentionHours: 0,
            pickupWindowStart: currentTime.toISOString(),
            deliveryDeadline: endTime.toISOString(),
            deadheadMiles: dhToHome,
            totalMiles: dhToHome,
            totalCost: cost,
            netRevenue: 0,
            profit: -cost,
            marginPct: -100,
            rpm: 0,
            allInRpm: 0,
            driveHours: driveTime,
            totalHours: driveTime,
            profitPerHour: -totalCpm * assumptions.avgSpeed,
            score: -5,
            action: 'PASS',
            estimatedDelivery: endTime.toISOString()
          },
          startTime: currentTime.toISOString(),
          endTime: endTime.toISOString(),
          isOvernight: false,
          isReturnHome: true
        }];
      }
      return [];
    }

    candidates.sort((a, b) => b.ranking - a.ranking);
    const topCandidates = candidates.slice(0, beamWidth);

    let bestChain: ChainLeg[] = [];
    let bestValue = -Infinity;

    for (const candidate of topCandidates) {
      const nextRemaining = remainingLoads.filter(l => l.id !== candidate.load.id);
      
      const legStartTime = new Date(Math.max(currentTime.getTime(), new Date(candidate.load.pickupWindowStart).getTime()));
      const legEndTime = new Date(legStartTime.getTime() + candidate.result.totalHours * 3600000);
      
      const rest = build(
        candidate.load.destination,
        nextRemaining,
        milesUsed + candidate.dh + candidate.load.miles,
        legEndTime
      );

      const isOvernight = candidate.result.totalHours > 10 || (legEndTime.getHours() < legStartTime.getHours());

      const currentChain = [{ 
        load: candidate.load, 
        deadhead: candidate.dh, 
        result: candidate.result,
        startTime: legStartTime.toISOString(),
        endTime: legEndTime.toISOString(),
        isOvernight
      }, ...rest];
      
      // Value for comparison
      const chainValue = currentChain.reduce((sum, leg) => sum + (leg.result?.profit || 0), 0);

      if (chainValue > bestValue) {
        bestChain = currentChain;
        bestValue = chainValue;
      }
    }

    return bestChain;
  }

  const startT = new Date();
  startT.setHours(8, 0, 0, 0);
  const legs = build(startCity, allLoads, 0, startT);
  return summarizeChain(legs);
}

export function naiveBaseline(
  allLoads: Load[], 
  startCity: string, 
  hosRemaining: number, 
  assumptions: Assumptions
): OptimizedChain {
  const maxDriveableMiles = (hosRemaining + (assumptions.daysAway * 11)) * assumptions.avgSpeed;
  let currentCity = startCity;
  let milesUsed = 0;
  let remainingLoads = [...allLoads];
  const legs: ChainLeg[] = [];
  let currentTime = new Date();
  currentTime.setHours(8, 0, 0, 0);

  while (remainingLoads.length > 0) {
    const candidates = remainingLoads.map(load => {
      const dh = calculateDistance(currentCity, load.origin);
      const result = scoreLoad(load, dh, assumptions);
      const distToHome = calculateDistance(load.destination, assumptions.homeBase);
      return { load, dh, result, distToHome };
    }).filter(c => milesUsed + c.dh + c.load.miles + c.distToHome <= maxDriveableMiles);

    if (candidates.length === 0) break;

    // Greedy pick by individual score
    candidates.sort((a, b) => b.result.score - a.result.score);
    const best = candidates[0];

    const legStartTime = new Date(Math.max(currentTime.getTime(), new Date(best.load.pickupWindowStart).getTime()));
    const legEndTime = new Date(legStartTime.getTime() + best.result.totalHours * 3600000);
    const isOvernight = best.result.totalHours > 10 || (legEndTime.getHours() < legStartTime.getHours());

    legs.push({ 
      load: best.load, 
      deadhead: best.dh, 
      result: best.result,
      startTime: legStartTime.toISOString(),
      endTime: legEndTime.toISOString(),
      isOvernight
    });
    currentCity = best.load.destination;
    milesUsed += best.dh + best.load.miles;
    currentTime = legEndTime;
    remainingLoads = remainingLoads.filter(l => l.id !== best.load.id);
  }

  // Add return home leg if needed
  if (currentCity !== assumptions.homeBase) {
    const dhToHome = calculateDistance(currentCity, assumptions.homeBase);
    const driveTime = dhToHome / assumptions.avgSpeed;
    const endTime = new Date(currentTime.getTime() + driveTime * 3600000);
    
    const fuelCpm = assumptions.fuelPrice / assumptions.mpg;
    const totalCpm = fuelCpm + assumptions.driverPay + assumptions.truckLease + assumptions.insurance + assumptions.maintReserve + assumptions.overhead;
    const cost = dhToHome * totalCpm;

    legs.push({
      load: null,
      deadhead: dhToHome,
      result: {
        id: 'RETURN-HOME',
        origin: currentCity,
        destination: assumptions.homeBase,
        miles: 0,
        rate: 0,
        weight: 0,
        commodity: 'DEADHEAD',
        detentionHours: 0,
        pickupWindowStart: currentTime.toISOString(),
        deliveryDeadline: endTime.toISOString(),
        deadheadMiles: dhToHome,
        totalMiles: dhToHome,
        totalCost: cost,
        netRevenue: 0,
        profit: -cost,
        marginPct: -100,
        rpm: 0,
        allInRpm: 0,
        driveHours: driveTime,
        totalHours: driveTime,
        profitPerHour: -totalCpm * assumptions.avgSpeed,
        score: -5,
        action: 'PASS',
        estimatedDelivery: endTime.toISOString()
      },
      startTime: currentTime.toISOString(),
      endTime: endTime.toISOString(),
      isOvernight: false,
      isReturnHome: true
    });
  }

  return summarizeChain(legs);
}

function summarizeChain(legs: ChainLeg[]): OptimizedChain {
  const totalProfit = legs.reduce((sum, l) => sum + (l.result?.profit || 0), 0);
  const totalRevenue = legs.reduce((sum, l) => sum + (l.result?.netRevenue || 0), 0);
  const totalDeadhead = legs.reduce((sum, l) => sum + l.deadhead, 0);
  const totalMiles = legs.reduce((sum, l) => sum + (l.result?.totalMiles || 0), 0);
  const totalHours = legs.reduce((sum, l) => sum + (l.result?.totalHours || 0), 0);
  const avgMargin = legs.filter(l => !l.isReturnHome).length > 0 
    ? legs.filter(l => !l.isReturnHome).reduce((sum, l) => sum + (l.result?.marginPct || 0), 0) / legs.filter(l => !l.isReturnHome).length 
    : 0;

  return {
    legs,
    summary: {
      totalProfit,
      totalRevenue,
      numLoads: legs.filter(l => !l.isReturnHome).length,
      totalDeadhead,
      deadheadPct: totalMiles > 0 ? (totalDeadhead / totalMiles) * 100 : 0,
      totalHours,
      avgMargin,
      profitPerHour: totalHours > 0 ? totalProfit / totalHours : 0,
      totalMiles
    }
  };
}
