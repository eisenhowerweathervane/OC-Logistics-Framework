/**
 * OC Logistics TMS — OpenClaw Plugin
 *
 * Registers 68 agent tools that give the AI dispatcher direct read/write access
 * to the OC Logistics backend API.
 *
 * Required environment variables (set in the agent's env or via `openclaw config`):
 *   OC_BACKEND_URL    — backend base URL, default: http://localhost:8000
 *   OC_BACKEND_TOKEN  — JWT bearer token (owner or dispatcher account)
 *
 * Install (one-time):
 *   openclaw plugins install --link /path/to/apps/openclaw
 *
 * Tool groups:
 *   Loads        — create_load, list_loads, get_load, update_load_status, assign_driver
 *   Fleet        — list_drivers, list_vehicles, driver_context, vehicle_compliance
 *   Brokers      — list_brokers, get_broker, create_broker, update_broker
 *   Trailers     — list_trailers, get_trailer, create_trailer, update_trailer
 *   Invoices     — list_receivables, generate_invoice, get_invoice_packet, record_payment
 *   Documents    — presign_upload, create_document, list_documents, download_document
 *   Compliance   — log_fuel, list_fuel_purchases, log_maintenance, list_maintenance,
 *                  compliance_scan, calculate_ifta, list_ifta_returns, file_ifta_return,
 *                  create_annual_inspection, list_annual_inspections,
 *                  create_roadside_inspection, list_roadside_inspections,
 *                  create_eld_day, list_eld_days
 *   Analytics    — dashboard, revenue_report, fleet_utilization, fuel_costs
 *   Accessorials — add_accessorial, list_accessorials, update_accessorial, accessorial_summary
 *   Settlements  — generate_settlement, list_settlements, get_settlement,
 *                  approve_settlement, pay_settlement, add_settlement_line
 *   Customers    — list_customers, get_customer, create_customer, update_customer
 *   Scoring      — score_load, lane_profitability, broker_ratings
 *   Notifications — send_overdue_ar_summary, send_compliance_check
 *   WhatsApp     — driver_by_phone, notify_driver_dispatched, notify_driver_docs_needed
 *   Sandbox      — sandbox_status, sandbox_toggle
 *   Meta         — system_info
 */

import type { OpenClawPluginApi } from "openclaw/plugin-sdk/core";

import { tmsCreateLoad, tmsListLoads, tmsGetLoad, tmsUpdateLoadStatus, tmsAssignDriver } from "./src/tools/loads.js";
import { tmsListDrivers, tmsListVehicles, tmsDriverContext, tmsVehicleCompliance } from "./src/tools/fleet.js";
import { tmsListBrokers, tmsGetBroker, tmsCreateBroker, tmsUpdateBroker } from "./src/tools/brokers.js";
import { tmsListTrailers, tmsGetTrailer, tmsCreateTrailer, tmsUpdateTrailer } from "./src/tools/trailers.js";
import { tmsListReceivables, tmsGenerateInvoice, tmsGetInvoicePacket, tmsRecordPayment } from "./src/tools/invoices.js";
import { tmsPresignUpload, tmsCreateDocument, tmsListDocuments, tmsDownloadDocument } from "./src/tools/documents.js";
import {
  tmsLogFuel,
  tmsListFuelPurchases,
  tmsLogMaintenance,
  tmsListMaintenance,
  tmsComplianceScan,
  tmsCalculateIfta,
  tmsListIftaReturns,
  tmsFileIftaReturn,
  tmsCreateAnnualInspection,
  tmsListAnnualInspections,
  tmsCreateRoadsideInspection,
  tmsListRoadsideInspections,
  tmsCreateEldDay,
  tmsListEldDays,
} from "./src/tools/compliance.js";
import { tmsDashboard, tmsRevenueReport, tmsFleetUtilization, tmsFuelCosts } from "./src/tools/analytics.js";
import { tmsAddAccessorial, tmsListAccessorials, tmsUpdateAccessorial, tmsAccessorialSummary } from "./src/tools/accessorials.js";
import {
  tmsGenerateSettlement,
  tmsListSettlements,
  tmsGetSettlement,
  tmsApproveSettlement,
  tmsPaySettlement,
  tmsAddSettlementLine,
} from "./src/tools/settlements.js";
import { tmsListCustomers, tmsGetCustomer, tmsCreateCustomer, tmsUpdateCustomer } from "./src/tools/customers.js";
import { tmsScoreLoad, tmsLaneProfitability, tmsBrokerRatings } from "./src/tools/scoring.js";
import { tmsSendOverdueArSummary, tmsSendComplianceCheck } from "./src/tools/notifications.js";
import { tmsDriverByPhone, tmsNotifyDriverDispatched, tmsNotifyDriverDocsNeeded } from "./src/tools/whatsapp.js";
import { tmsSandboxStatus, tmsSandboxToggle } from "./src/tools/sandbox.js";
import { tmsSystemInfo } from "./src/tools/meta.js";

export default function register(api: OpenClawPluginApi): void {
  // Load management
  api.registerTool(tmsCreateLoad);
  api.registerTool(tmsListLoads);
  api.registerTool(tmsGetLoad);
  api.registerTool(tmsUpdateLoadStatus);
  api.registerTool(tmsAssignDriver);

  // Fleet
  api.registerTool(tmsListDrivers);
  api.registerTool(tmsListVehicles);
  api.registerTool(tmsDriverContext);
  api.registerTool(tmsVehicleCompliance);

  // Brokers
  api.registerTool(tmsListBrokers);
  api.registerTool(tmsGetBroker);
  api.registerTool(tmsCreateBroker);
  api.registerTool(tmsUpdateBroker);

  // Trailers
  api.registerTool(tmsListTrailers);
  api.registerTool(tmsGetTrailer);
  api.registerTool(tmsCreateTrailer);
  api.registerTool(tmsUpdateTrailer);

  // Invoices & AR
  api.registerTool(tmsListReceivables);
  api.registerTool(tmsGenerateInvoice);
  api.registerTool(tmsGetInvoicePacket);
  api.registerTool(tmsRecordPayment);

  // Documents
  api.registerTool(tmsPresignUpload);
  api.registerTool(tmsCreateDocument);
  api.registerTool(tmsListDocuments);
  api.registerTool(tmsDownloadDocument);

  // Compliance & fuel
  api.registerTool(tmsLogFuel);
  api.registerTool(tmsListFuelPurchases);
  api.registerTool(tmsLogMaintenance);
  api.registerTool(tmsListMaintenance);
  api.registerTool(tmsComplianceScan);

  // IFTA
  api.registerTool(tmsCalculateIfta);
  api.registerTool(tmsListIftaReturns);
  api.registerTool(tmsFileIftaReturn);

  // Inspections
  api.registerTool(tmsCreateAnnualInspection);
  api.registerTool(tmsListAnnualInspections);
  api.registerTool(tmsCreateRoadsideInspection);
  api.registerTool(tmsListRoadsideInspections);

  // ELD
  api.registerTool(tmsCreateEldDay);
  api.registerTool(tmsListEldDays);

  // Accessorial charges
  api.registerTool(tmsAddAccessorial);
  api.registerTool(tmsListAccessorials);
  api.registerTool(tmsUpdateAccessorial);
  api.registerTool(tmsAccessorialSummary);

  // Settlements & driver pay
  api.registerTool(tmsGenerateSettlement);
  api.registerTool(tmsListSettlements);
  api.registerTool(tmsGetSettlement);
  api.registerTool(tmsApproveSettlement);
  api.registerTool(tmsPaySettlement);
  api.registerTool(tmsAddSettlementLine);

  // Analytics & reporting
  api.registerTool(tmsDashboard);
  api.registerTool(tmsRevenueReport);
  api.registerTool(tmsFleetUtilization);
  api.registerTool(tmsFuelCosts);

  // Customers (direct shippers)
  api.registerTool(tmsListCustomers);
  api.registerTool(tmsGetCustomer);
  api.registerTool(tmsCreateCustomer);
  api.registerTool(tmsUpdateCustomer);

  // Scoring & profitability
  api.registerTool(tmsScoreLoad);
  api.registerTool(tmsLaneProfitability);
  api.registerTool(tmsBrokerRatings);

  // Notifications (Slack push alerts)
  api.registerTool(tmsSendOverdueArSummary);
  api.registerTool(tmsSendComplianceCheck);

  // WhatsApp driver tools
  api.registerTool(tmsDriverByPhone);
  api.registerTool(tmsNotifyDriverDispatched);
  api.registerTool(tmsNotifyDriverDocsNeeded);

  // Sandbox mode
  api.registerTool(tmsSandboxStatus);
  api.registerTool(tmsSandboxToggle);

  // System meta
  api.registerTool(tmsSystemInfo);

  api.logger.info(`OC Logistics plugin loaded — ${68} tools registered`);
}
