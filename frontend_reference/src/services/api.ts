/**
 * API Service - Connects frontend to FastAPI backend
 * Handles data transformation between camelCase (frontend) and snake_case (backend)
 */

import type {
  CostConfig,
  ScorerConfig,
  GapReport,
  LoadFeedback,
  LaneHistory,
  BrokerHistory,
  WatchlistPlan,
  CityDemandTier,
} from '../types';

const API_BASE_URL = 'http://localhost:8000';

// =============================================================================
// DATA TRANSFORMERS
// =============================================================================

// Convert snake_case to camelCase
function toCamelCase(str: string): string {
  return str.replace(/_([a-z])/g, (_, letter) => letter.toUpperCase());
}

// Convert camelCase to snake_case
function toSnakeCase(str: string): string {
  return str.replace(/[A-Z]/g, letter => `_${letter.toLowerCase()}`);
}

// Transform object keys from snake_case to camelCase
function transformToCamelCase<T>(obj: any): T {
  if (Array.isArray(obj)) {
    return obj.map(item => transformToCamelCase(item)) as T;
  }
  if (obj !== null && typeof obj === 'object') {
    const newObj: any = {};
    for (const key in obj) {
      const camelKey = toCamelCase(key);
      newObj[camelKey] = transformToCamelCase(obj[key]);
    }
    return newObj as T;
  }
  return obj;
}

// Transform object keys from camelCase to snake_case
function transformToSnakeCase(obj: any): any {
  if (Array.isArray(obj)) {
    return obj.map(item => transformToSnakeCase(item));
  }
  if (obj !== null && typeof obj === 'object') {
    const newObj: any = {};
    for (const key in obj) {
      const snakeKey = toSnakeCase(key);
      newObj[snakeKey] = transformToSnakeCase(obj[key]);
    }
    return newObj;
  }
  return obj;
}

// =============================================================================
// API FUNCTIONS
// =============================================================================

/**
 * Fetch all loads from the backend
 */
export async function fetchLoads(options?: {
  limit?: number;
  offset?: number;
  sortBy?: string;
  sortOrder?: 'asc' | 'desc';
  action?: string;
}): Promise<any[]> {
  const params = new URLSearchParams();
  if (options?.limit) params.append('limit', options.limit.toString());
  if (options?.offset) params.append('offset', options.offset.toString());
  if (options?.sortBy) params.append('sort_by', toSnakeCase(options.sortBy));
  if (options?.sortOrder) params.append('sort_order', options.sortOrder);
  if (options?.action) params.append('action', options.action);

  const response = await fetch(`${API_BASE_URL}/api/loads?${params}`);
  if (!response.ok) throw new Error('Failed to fetch loads');

  const data = await response.json();
  return transformToCamelCase(data);
}

/**
 * Create and score a new load
 */
export async function createLoad(load: {
  originCity: string;
  originState: string;
  destinationCity: string;
  destinationState: string;
  rateTotal?: number;
  mileage?: number;
  weight?: number;
  commodity?: string;
  equipmentType?: string;
  pickupDate?: string;
  deliveryDate?: string;
  brokerName?: string;
}, assumptions?: any): Promise<any> {
  const body: any = {
    load: transformToSnakeCase(load),
    assumptions: assumptions ? transformToSnakeCase(assumptions) : undefined,
  };

  const response = await fetch(`${API_BASE_URL}/api/loads`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

  if (!response.ok) throw new Error('Failed to create load');
  return transformToCamelCase(await response.json());
}

/**
 * Score a load without saving
 */
export async function scoreLoad(load: {
  originCity: string;
  originState: string;
  destinationCity: string;
  destinationState: string;
  rateTotal?: number;
  mileage?: number;
  weight?: number;
}, assumptions?: any): Promise<any> {
  const loadData = transformToSnakeCase(load);

  const response = await fetch(`${API_BASE_URL}/api/score`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      load: loadData,
      assumptions: assumptions ? transformToSnakeCase(assumptions) : undefined,
    }),
  });

  if (!response.ok) throw new Error('Failed to score load');
  return transformToCamelCase(await response.json());
}

/**
 * Run the chain optimizer
 */
export async function optimizeChain(
  loadIds: number[],
  startCity: string,
  hosRemaining: number,
  daysAway: number,
  assumptions?: any
): Promise<any> {
  const body = {
    load_ids: loadIds,
    start_city: startCity,
    hos_remaining: hosRemaining,
    days_away: daysAway,
    assumptions: assumptions ? transformToSnakeCase(assumptions) : undefined,
  };

  const response = await fetch(`${API_BASE_URL}/api/optimize`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

  if (!response.ok) throw new Error('Failed to optimize chain');
  return transformToCamelCase(await response.json());
}

/**
 * Get distance and drive time between two cities
 */
export async function getDistance(origin: string, destination: string): Promise<{
  distanceMiles: number;
  driveTimeHours: number;
  source: string;
}> {
  const params = new URLSearchParams({
    origin,
    destination,
  });

  const response = await fetch(`${API_BASE_URL}/api/distance?${params}`);
  if (!response.ok) throw new Error('Failed to get distance');

  return transformToCamelCase(await response.json());
}

/**
 * Get list of known cities
 */
export async function getCities(): Promise<string[]> {
  const response = await fetch(`${API_BASE_URL}/api/cities`);
  if (!response.ok) throw new Error('Failed to get cities');
  return response.json();
}

/**
 * Get default assumptions
 */
export async function getAssumptions(): Promise<any> {
  const response = await fetch(`${API_BASE_URL}/api/assumptions`);
  if (!response.ok) throw new Error('Failed to get assumptions');
  return transformToCamelCase(await response.json());
}

/**
 * Parse an email and score loads
 */
export async function parseAndScoreEmail(
  rawText: string,
  save: boolean = false,
  assumptions?: any
): Promise<any> {
  const body: any = {
    raw_text: rawText,
    save,
  };
  if (assumptions) {
    body.assumptions = transformToSnakeCase(assumptions);
  }

  const response = await fetch(`${API_BASE_URL}/api/parse-and-score`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

  if (!response.ok) throw new Error('Failed to parse email');
  return transformToCamelCase(await response.json());
}

/**
 * Health check
 */
export async function healthCheck(): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE_URL}/`);
    return response.ok;
  } catch {
    return false;
  }
}

// =============================================================================
// COST CONFIG
// =============================================================================

/**
 * Get the current cost configuration
 */
export async function getCostConfig(): Promise<CostConfig> {
  const response = await fetch(`${API_BASE_URL}/api/config/costs`);
  if (!response.ok) throw new Error('Failed to get cost config');
  return transformToCamelCase(await response.json());
}

/**
 * Update cost configuration (partial update)
 */
export async function updateCostConfig(config: Partial<CostConfig>): Promise<CostConfig> {
  const response = await fetch(`${API_BASE_URL}/api/config/costs`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(transformToSnakeCase(config)),
  });
  if (!response.ok) throw new Error('Failed to update cost config');
  return transformToCamelCase(await response.json());
}

// =============================================================================
// SCORER CONFIG
// =============================================================================

/**
 * Get the current scorer weights
 */
export async function getScorerConfig(): Promise<ScorerConfig> {
  const response = await fetch(`${API_BASE_URL}/api/config/scorer`);
  if (!response.ok) throw new Error('Failed to get scorer config');
  return transformToCamelCase(await response.json());
}

/**
 * Update scorer weights
 */
export async function updateScorerConfig(config: ScorerConfig): Promise<ScorerConfig> {
  const response = await fetch(`${API_BASE_URL}/api/config/scorer`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(transformToSnakeCase(config)),
  });
  if (!response.ok) throw new Error('Failed to update scorer config');
  return transformToCamelCase(await response.json());
}

// =============================================================================
// INGESTION
// =============================================================================

/**
 * Ingest pasted load text and get a gap report
 */
export async function ingestPaste(text: string): Promise<GapReport> {
  const response = await fetch(`${API_BASE_URL}/api/ingest/paste`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text }),
  });
  if (!response.ok) throw new Error('Failed to ingest paste');
  return transformToCamelCase(await response.json());
}

/**
 * Complete ingestion with gap fills
 */
export async function ingestComplete(
  load: any,
  fills: Record<string, any>,
  save: boolean
): Promise<any> {
  const response = await fetch(`${API_BASE_URL}/api/ingest/complete`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      load: transformToSnakeCase(load),
      fills: transformToSnakeCase(fills),
      save,
    }),
  });
  if (!response.ok) throw new Error('Failed to complete ingestion');
  return transformToCamelCase(await response.json());
}

// =============================================================================
// LOAD MANAGEMENT
// =============================================================================

/**
 * Update a load's outcome (booked, passed, etc.)
 */
export async function updateLoadOutcome(loadId: number, outcome: string): Promise<any> {
  const response = await fetch(`${API_BASE_URL}/api/loads/${loadId}/outcome`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ outcome }),
  });
  if (!response.ok) throw new Error('Failed to update load outcome');
  return transformToCamelCase(await response.json());
}

/**
 * Submit feedback for a completed load
 */
export async function submitLoadFeedback(loadId: number, feedback: LoadFeedback): Promise<any> {
  const response = await fetch(`${API_BASE_URL}/api/loads/${loadId}/feedback`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(transformToSnakeCase(feedback)),
  });
  if (!response.ok) throw new Error('Failed to submit load feedback');
  return transformToCamelCase(await response.json());
}

// =============================================================================
// ANALYTICS
// =============================================================================

/**
 * Get lane history with optional state filters
 */
export async function getLaneHistory(
  originState?: string,
  destState?: string
): Promise<LaneHistory[]> {
  const params = new URLSearchParams();
  if (originState) params.append('origin_state', originState);
  if (destState) params.append('dest_state', destState);

  const query = params.toString();
  const url = `${API_BASE_URL}/api/analytics/lanes${query ? `?${query}` : ''}`;
  const response = await fetch(url);
  if (!response.ok) throw new Error('Failed to get lane history');
  return transformToCamelCase(await response.json());
}

/**
 * Get broker history / reliability data
 */
export async function getBrokerHistory(): Promise<BrokerHistory[]> {
  const response = await fetch(`${API_BASE_URL}/api/analytics/brokers`);
  if (!response.ok) throw new Error('Failed to get broker history');
  return transformToCamelCase(await response.json());
}

// =============================================================================
// WATCHLIST
// =============================================================================

/**
 * Get the watchlist plan with scenario tree
 */
export async function getWatchlist(
  committedIds: number[],
  startCity: string,
  hosRemaining: number,
  maxDays: number
): Promise<WatchlistPlan> {
  const response = await fetch(`${API_BASE_URL}/api/watchlist`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      committed_ids: committedIds,
      start_city: startCity,
      hos_remaining: hosRemaining,
      max_days: maxDays,
    }),
  });
  if (!response.ok) throw new Error('Failed to get watchlist');
  return transformToCamelCase(await response.json());
}

/**
 * Resolve watchlist after actual dwell is known
 */
export async function resolveWatchlist(
  actualDwellHours: number,
  scenarioTree: any
): Promise<any[]> {
  const response = await fetch(`${API_BASE_URL}/api/watchlist/resolve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      actual_dwell_hours: actualDwellHours,
      scenario_tree: transformToSnakeCase(scenarioTree),
    }),
  });
  if (!response.ok) throw new Error('Failed to resolve watchlist');
  return transformToCamelCase(await response.json());
}

// =============================================================================
// DEMAND TIERS
// =============================================================================

/**
 * Get city demand tiers
 */
export async function getDemandTiers(): Promise<CityDemandTier[]> {
  const response = await fetch(`${API_BASE_URL}/api/config/demand-tiers`);
  if (!response.ok) throw new Error('Failed to get demand tiers');
  return transformToCamelCase(await response.json());
}

/**
 * Update city demand tiers
 */
export async function updateDemandTiers(tiers: CityDemandTier[]): Promise<any> {
  const response = await fetch(`${API_BASE_URL}/api/config/demand-tiers`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(transformToSnakeCase(tiers)),
  });
  if (!response.ok) throw new Error('Failed to update demand tiers');
  return transformToCamelCase(await response.json());
}

// =============================================================================
// DUPLICATES
// =============================================================================

/**
 * Get list of duplicate loads
 */
export async function getDuplicates(): Promise<any[]> {
  const response = await fetch(`${API_BASE_URL}/api/duplicates`);
  if (!response.ok) throw new Error('Failed to get duplicates');
  return transformToCamelCase(await response.json());
}

/**
 * Resolve a duplicate load
 */
export async function resolveDuplicate(
  loadId: number,
  action: 'keep' | 'remove' | 'merge'
): Promise<any> {
  const response = await fetch(`${API_BASE_URL}/api/duplicates`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ load_id: loadId, action }),
  });
  if (!response.ok) throw new Error('Failed to resolve duplicate');
  return transformToCamelCase(await response.json());
}

// Export API base URL for reference
export { API_BASE_URL };
