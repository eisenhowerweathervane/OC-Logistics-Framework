export interface City {
  name: string;
  lat: number;
  lng: number;
}

export interface Load {
  id: string;
  origin: string;
  destination: string;
  miles: number;
  rate: number;
  weight: number;
  commodity: string;
  detentionHours: number;
  pickupWindowStart: string; // ISO string
  deliveryDeadline: string; // ISO string
}

export interface Assumptions {
  fuelPrice: number;
  mpg: number;
  driverPay: number;
  truckLease: number;
  insurance: number;
  maintReserve: number;
  overhead: number;
  factoringFee: number;
  detentionRate: number;
  maxDeadhead: number;
  minMargin: number;
  targetMargin: number;
  avgSpeed: number;
  loadUnloadTime: number;
  daysAway: number;
  homeBase: string;
}

export interface ScoredLoad extends Load {
  deadheadMiles: number;
  totalMiles: number;
  totalCost: number;
  netRevenue: number;
  profit: number;
  marginPct: number;
  rpm: number;
  allInRpm: number;
  driveHours: number;
  totalHours: number;
  profitPerHour: number;
  score: number;
  action: 'BOOK IT' | 'CONSIDER' | 'NEGOTIATE' | 'PASS';
  estimatedDelivery: string; // ISO string
}

export interface ChainLeg {
  load: Load | null;
  deadhead: number;
  result: ScoredLoad | null;
  startTime: string; // ISO string
  endTime: string; // ISO string
  isOvernight: boolean;
  isReturnHome?: boolean;
}

export interface OptimizedChain {
  legs: ChainLeg[];
  summary: {
    totalProfit: number;
    totalRevenue: number;
    numLoads: number;
    totalDeadhead: number;
    deadheadPct: number;
    totalHours: number;
    avgMargin: number;
    profitPerHour: number;
    totalMiles: number;
  };
}
