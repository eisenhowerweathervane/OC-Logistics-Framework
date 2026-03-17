import { City, Load, Assumptions, ScoredLoad } from '../types';
import { CITIES } from '../constants';

export function getCityCoords(cityName: string): City | undefined {
  return CITIES.find(c => c.name === cityName);
}

export function calculateDistance(city1: string, city2: string): number {
  const c1 = getCityCoords(city1);
  const c2 = getCityCoords(city2);
  if (!c1 || !c2) return 0;

  const R = 3958.8; // Earth radius in miles
  const dLat = (c2.lat - c1.lat) * Math.PI / 180;
  const dLon = (c2.lng - c1.lng) * Math.PI / 180;
  const a = 
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(c1.lat * Math.PI / 180) * Math.cos(c2.lat * Math.PI / 180) * 
    Math.sin(dLon / 2) * Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  const distance = R * c;

  return Math.round(distance * 1.28); // Road factor
}

export function scoreLoad(load: Load, deadheadMiles: number, assumptions: Assumptions): ScoredLoad {
  const {
    fuelPrice, mpg, driverPay, truckLease, insurance, 
    maintReserve, overhead, factoringFee, detentionRate,
    maxDeadhead, minMargin, targetMargin, avgSpeed, loadUnloadTime
  } = assumptions;

  // Cost Calculation
  const fuelCpm = fuelPrice / mpg;
  const totalCpm = fuelCpm + driverPay + truckLease + insurance + maintReserve + overhead;
  
  const totalMiles = load.miles + deadheadMiles;
  const totalCost = totalCpm * totalMiles;

  // Revenue Calculation
  const detentionRevenue = load.detentionHours * detentionRate;
  const grossRevenue = load.rate + detentionRevenue;
  const factoringAmount = grossRevenue * (factoringFee / 100);
  const netRevenue = grossRevenue - factoringAmount;

  // Profit & Metrics
  const profit = netRevenue - totalCost;
  const marginPct = (profit / netRevenue) * 100;
  const rpm = load.rate / load.miles;
  const allInRpm = netRevenue / totalMiles;
  const driveHours = totalMiles / avgSpeed;
  const totalHours = driveHours + loadUnloadTime + load.detentionHours;
  const profitPerHour = profit / totalHours;

  // Scoring Rubric
  let score = 0;

  // Margin
  if (marginPct >= targetMargin) score += 4;
  else if (marginPct >= minMargin) score += 2;
  else if (marginPct >= 5) score += 0;
  else if (marginPct >= 0) score -= 2;
  else score -= 5;

  // All-in RPM
  if (allInRpm >= 3.00) score += 2;
  else if (allInRpm >= 2.50) score += 1;
  else if (allInRpm >= 2.00) score += 0;
  else score -= 2;

  // Deadhead penalty
  const dhPct = (deadheadMiles / load.miles) * 100;
  if (dhPct <= 5) score += 2;
  else if (dhPct <= maxDeadhead) score += 1;
  else if (dhPct <= 25) score -= 1;
  else score -= 3;

  // Mileage sweet spot
  if (load.miles >= 150 && load.miles <= 300) score += 1;
  else if (load.miles < 80) score -= 1;

  // Detention risk
  if (load.detentionHours > 2) score -= 1;

  score = Math.max(-10, Math.min(10, score));

  // Action
  let action: ScoredLoad['action'] = 'PASS';
  const floorRpm = totalCpm / (1 - minMargin / 100) / (1 - factoringFee / 100);
  
  if (allInRpm < floorRpm) {
    action = 'PASS';
  } else if (score >= 5) {
    action = 'BOOK IT';
  } else if (score >= 2) {
    action = 'CONSIDER';
  } else if (score >= 0) {
    action = 'NEGOTIATE';
  } else {
    action = 'PASS';
  }

  const estimatedDeliveryDate = new Date(load.pickupWindowStart);
  estimatedDeliveryDate.setHours(estimatedDeliveryDate.getHours() + totalHours);

  return {
    ...load,
    deadheadMiles,
    totalMiles,
    totalCost,
    netRevenue,
    profit,
    marginPct,
    rpm,
    allInRpm,
    driveHours,
    totalHours,
    profitPerHour,
    score,
    action,
    estimatedDelivery: estimatedDeliveryDate.toISOString()
  };
}
