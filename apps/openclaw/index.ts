/**
 * OC Logistics TMS — OpenClaw Plugin
 *
 * Registers 23 agent tools that give the AI dispatcher direct read/write access
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
 *   Loads       — create_load, list_loads, get_load, update_load_status, assign_driver
 *   Fleet       — list_drivers, list_vehicles, driver_context, vehicle_compliance
 *   Invoices    — list_receivables, generate_invoice, get_invoice_packet
 *   Compliance  — log_fuel, log_maintenance, list_maintenance
 *   Notifications — send_overdue_ar_summary, send_compliance_check
 *   WhatsApp     — driver_by_phone, notify_driver_dispatched, notify_driver_docs_needed
 *   Sandbox      — sandbox_status, sandbox_toggle
 *   Meta         — system_info
 */

import type { OpenClawPluginApi } from "openclaw/plugin-sdk/core";

import { tmsCreateLoad, tmsListLoads, tmsGetLoad, tmsUpdateLoadStatus, tmsAssignDriver } from "./src/tools/loads.js";
import { tmsListDrivers, tmsListVehicles, tmsDriverContext, tmsVehicleCompliance } from "./src/tools/fleet.js";
import { tmsListReceivables, tmsGenerateInvoice, tmsGetInvoicePacket } from "./src/tools/invoices.js";
import { tmsLogFuel, tmsLogMaintenance, tmsListMaintenance } from "./src/tools/compliance.js";
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

  // Invoices & AR
  api.registerTool(tmsListReceivables);
  api.registerTool(tmsGenerateInvoice);
  api.registerTool(tmsGetInvoicePacket);

  // Compliance & fuel
  api.registerTool(tmsLogFuel);
  api.registerTool(tmsLogMaintenance);
  api.registerTool(tmsListMaintenance);

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

  api.logger.info(`OC Logistics plugin loaded — ${23} tools registered`);
}
