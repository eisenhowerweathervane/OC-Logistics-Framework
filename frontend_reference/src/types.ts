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

// =============================================================================
// Cost configuration (monthly-based)
// =============================================================================

export interface CostConfig {
  truckLeaseMonthly: number;
  insuranceMonthly: number;
  overheadMonthly: number;
  maintReserveMonthly: number;
  expectedMonthlyMiles: number;
  driverPayMode: 'base_plus_mile' | 'per_mile_only' | 'base_only';
  driverBaseWeekly: number;
  driverPerMile: number;
  factoringFeePct: number;
  fuelMpg: number;
  defaultFuelPrice: number;
}

// =============================================================================
// Scorer weights
// =============================================================================

export interface ScorerConfig {
  financialWeight: number;
  laneWeight: number;
  brokerWeight: number;
  strategicWeight: number;
}

// =============================================================================
// Gap report from ingestion
// =============================================================================

export interface GapReport {
  loads: ParsedLoadResult[];
  count: number;
  gaps: string[];
  duplicates: number;
}

export interface ParsedLoadResult {
  originCity: string;
  originState: string;
  destinationCity: string;
  destinationState: string;
  mileage: number;
  rateTotal: number | null;
  source: string;
  brokerName: string;
  pickupDate: string;
  gaps: string;
  missingOptional: string[];
  isComplete: boolean;
  duplicateOf?: number;
  duplicateMessage?: string;
  [key: string]: any;
}

// =============================================================================
// Watchlist
// =============================================================================

export interface WatchlistPlan {
  committed: any[];
  watchlist: WatchlistEntry[];
  scenarioTree: ScenarioTree;
}

export interface WatchlistEntry {
  load: any;
  score: number | null;
  profit: number | null;
  scenarios: string[];
  pickupDeadline: string;
}

export interface ScenarioTree {
  scenarios: {
    quick: ScenarioBranch;
    normal: ScenarioBranch;
    slow: ScenarioBranch;
    detention: ScenarioBranch;
  };
  currentCity: string;
  hosState: any;
}

export interface ScenarioBranch {
  dwellHours: number;
  recommendations: ScenarioRecommendation[];
}

export interface ScenarioRecommendation {
  load: any;
  score: number;
  profit: number;
  chainSummary: any;
}

// =============================================================================
// Analytics
// =============================================================================

export interface LaneHistory {
  originCity: string;
  originState: string;
  destinationCity: string;
  destinationState: string;
  avgRate: number;
  avgMarginPct: number;
  loadCount: number;
  bookedCount: number;
  trendDirection: 'up' | 'down' | 'stable';
  lastSeen: string;
}

export interface BrokerHistory {
  brokerName: string;
  brokerMcNumber: string;
  avgDetentionHours: number;
  tonuCount: number;
  loadsCompleted: number;
  loadsSeen: number;
  rateAccuracyPct: number;
  ontimePickupPct: number;
  reliabilityGrade: string;
}

// =============================================================================
// Load feedback
// =============================================================================

export interface LoadFeedback {
  actualDwellHours: number;
  actualRatePaid: number;
  actualTollCost: number;
  detentionHours: number;
  ontimePickup: boolean;
  issues: string;
}

// =============================================================================
// City demand tier
// =============================================================================

export interface CityDemandTier {
  city: string;
  state: string;
  tier: number;
  source: string;
}
