// TypeScript interfaces matching backend Pydantic schemas

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface UserResponse {
  id: string;
  email: string;
  roles: string[];
}

export interface Load {
  id: string;
  organization_id: string;
  broker_id: string | null;
  reference_number: string | null;
  shipping_document_number: string | null;
  commodity: string | null;
  weight_lbs: number | null;
  pieces: number | null;
  rate_total: number | null;
  rate_type: string | null;
  miles_loaded: number | null;
  miles_deadhead_est: number | null;
  notes: string | null;
  status: string;
  stops: LoadStop[];
  assignments: Assignment[];
  created_at: string;
  updated_at: string;
}

export interface LoadStop {
  id: string;
  seq: number;
  stop_type: string;
  facility_name: string | null;
  city: string | null;
  state: string | null;
  zip: string | null;
  appt_start: string | null;
  appt_end: string | null;
}

export interface Assignment {
  id: string;
  driver_id: string;
  vehicle_id: string | null;
  trailer_id: string | null;
  assigned_at: string;
  unassigned_at: string | null;
}

export interface Driver {
  id: string;
  organization_id: string;
  first_name: string;
  last_name: string;
  phone: string | null;
  license_state: string | null;
  status: string;
  created_at: string;
}

export interface Vehicle {
  id: string;
  organization_id: string;
  unit_number: string;
  make: string | null;
  model: string | null;
  year: number | null;
  status: string;
  created_at: string;
}

export interface Broker {
  id: string;
  organization_id: string;
  legal_name: string;
  dba_name: string | null;
  billing_email: string | null;
  payment_terms_days: number | null;
}

export interface DashboardSummary {
  active_loads: number;
  monthly_revenue: number;
  total_drivers: number;
  total_vehicles: number;
  overdue_receivables: number;
  overdue_amount: number;
}

export interface RevenueEntry {
  period: string;
  revenue: number;
  load_count: number;
  avg_rpm: number | null;
}

export interface FleetUtilization {
  driver_id: string;
  driver_name: string;
  loads_count: number;
  total_revenue: number;
  total_miles: number;
  status: string;
}

export interface FuelCostEntry {
  month: string;
  total_gallons: number;
  total_cost: number;
  avg_price_per_gallon: number | null;
}

export interface ComplianceAlert {
  alert_type: string;
  severity: string;
  entity_type: string;
  entity_id: string;
  entity_label: string;
  message: string;
}

export interface LoadScore {
  load_id: string;
  rate_per_mile: number;
  grade: string;
  rate_total: number;
  miles_loaded: number;
}

export interface LaneProfitability {
  origin_state: string;
  dest_state: string;
  loads_count: number;
  avg_rpm: number;
  total_revenue: number;
}

export interface BrokerRating {
  broker_id: string;
  broker_name: string;
  loads_count: number;
  avg_rpm: number;
  avg_payment_days: number | null;
  score: number;
}

export interface Receivable {
  id: string;
  load_id: string;
  broker_id: string | null;
  amount: number;
  due_date: string;
  status: string;
  paid_at: string | null;
}

export interface InvoicePacket {
  id: string;
  load_id: string;
  status: string;
  generated_at: string | null;
}

export interface SandboxStatus {
  sandbox_mode: boolean;
  message?: string;
}

// Load state machine valid transitions (mirrors backend)
export const LOAD_STATUSES = [
  "quoted",
  "booked",
  "dispatched",
  "arrived_pickup",
  "loaded",
  "in_transit",
  "arrived_delivery",
  "delivered",
  "invoice_ready",
  "invoiced",
  "paid",
  "closed",
  "archived",
] as const;

export type LoadStatus = (typeof LOAD_STATUSES)[number];

export const VALID_TRANSITIONS: Record<string, string[]> = {
  quoted: ["booked"],
  booked: ["dispatched"],
  dispatched: ["arrived_pickup"],
  arrived_pickup: ["loaded"],
  loaded: ["in_transit"],
  in_transit: ["arrived_delivery"],
  arrived_delivery: ["delivered"],
  delivered: ["invoice_ready"],
  invoice_ready: ["invoiced"],
  invoiced: ["paid"],
  paid: ["closed"],
  closed: ["archived"],
};
