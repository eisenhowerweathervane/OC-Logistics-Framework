/**
 * API Service - Connects frontend to FastAPI backend
 * Handles data transformation between camelCase (frontend) and snake_case (backend)
 */

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

// Export API base URL for reference
export { API_BASE_URL };
