import { Type } from "@sinclair/typebox";
import type { AnyAgentTool } from "openclaw/plugin-sdk/core";
import { api, ok, err } from "../client.js";

export const tmsPresignUpload: AnyAgentTool = {
  name: "tms_presign_upload",
  label: "TMS: Presign Upload URL",
  description:
    "Get a presigned URL for uploading a document to storage (MinIO/S3). " +
    "Step 1 of the upload flow: call this to get the upload_url and storage_key, " +
    "then upload the file directly to the URL, then call tms_create_document to create the record.",
  parameters: Type.Object({
    filename: Type.String({ description: "Original filename, e.g. 'ratecon.pdf'" }),
    mime_type: Type.String({ description: "MIME type, e.g. 'application/pdf' or 'image/jpeg'" }),
    target_folder: Type.Optional(Type.String({ description: "Storage folder (default: 'documents')" })),
  }),
  execute: async (_id, params) => {
    try {
      const result = await api.post("/api/documents/presign", params);
      return ok(result);
    } catch (e) {
      return err(e);
    }
  },
};

export const tmsCreateDocument: AnyAgentTool = {
  name: "tms_create_document",
  label: "TMS: Create Document Record",
  description:
    "Create a document record in the TMS after uploading to storage. " +
    "Link documents to loads, drivers, or vehicles using the links array. " +
    "Common doc_types: rate_confirmation, pod, bol, fuel_receipt, inspection_report.",
  parameters: Type.Object({
    doc_type: Type.String({
      description: "Document type: rate_confirmation, pod, bol, fuel_receipt, inspection_report, etc.",
    }),
    filename: Type.String({ description: "Original filename, e.g. 'ratecon-001.pdf'" }),
    mime_type: Type.String({ description: "MIME type, e.g. 'application/pdf'" }),
    storage_key: Type.String({ description: "Storage key returned from tms_presign_upload" }),
    sha256: Type.Optional(Type.String({ description: "SHA-256 hash of the file content" })),
    upload_source: Type.Optional(Type.String({ description: "Where the file came from: whatsapp, email, web, etc." })),
    doc_date: Type.Optional(Type.String({ description: "Date on the document, ISO format, e.g. '2026-03-01'" })),
    amount: Type.Optional(Type.String({ description: "Dollar amount if applicable, e.g. '2800.00'" })),
    vendor_name: Type.Optional(Type.String({ description: "Vendor name if applicable" })),
    links: Type.Optional(
      Type.Array(
        Type.Object({
          entity_type: Type.String({ description: "Entity type: load, driver, vehicle" }),
          entity_id: Type.String({ description: "UUID of the entity to link to" }),
        }),
        { description: "Link this document to loads, drivers, or vehicles" },
      ),
    ),
  }),
  execute: async (_id, params) => {
    try {
      const doc = await api.post("/api/documents", params);
      return ok(doc);
    } catch (e) {
      return err(e);
    }
  },
};

export const tmsListDocuments: AnyAgentTool = {
  name: "tms_list_documents",
  label: "TMS: List Documents",
  description:
    "List documents with optional filters. Filter by doc_type to find rate confirmations, " +
    "PODs, etc. Filter by load_id/driver_id/vehicle_id to find docs linked to a specific entity.",
  parameters: Type.Object({
    doc_type: Type.Optional(
      Type.String({ description: "Filter by type: rate_confirmation, pod, bol, fuel_receipt, inspection_report" }),
    ),
    load_id: Type.Optional(Type.String({ description: "Filter by linked load UUID" })),
    driver_id: Type.Optional(Type.String({ description: "Filter by linked driver UUID" })),
    vehicle_id: Type.Optional(Type.String({ description: "Filter by linked vehicle UUID" })),
    page: Type.Optional(Type.Number({ description: "Page number, default 1" })),
    page_size: Type.Optional(Type.Number({ description: "Results per page, default 50" })),
  }),
  execute: async (_id, params) => {
    try {
      const qs = new URLSearchParams();
      if (params.doc_type) qs.set("doc_type", params.doc_type);
      if (params.load_id) qs.set("load_id", params.load_id);
      if (params.driver_id) qs.set("driver_id", params.driver_id);
      if (params.vehicle_id) qs.set("vehicle_id", params.vehicle_id);
      if (params.page) qs.set("page", String(params.page));
      if (params.page_size) qs.set("page_size", String(params.page_size));
      const docs = await api.get(`/api/documents?${qs}`);
      return ok(docs);
    } catch (e) {
      return err(e);
    }
  },
};

export const tmsDownloadDocument: AnyAgentTool = {
  name: "tms_download_document",
  label: "TMS: Download Document",
  description: "Get a presigned download URL for a document. The URL is temporary and expires after a few minutes.",
  parameters: Type.Object({
    document_id: Type.String({ description: "UUID of the document to download" }),
  }),
  execute: async (_id, params) => {
    try {
      const result = await api.get(`/api/documents/${params.document_id}/download`);
      return ok(result);
    } catch (e) {
      return err(e);
    }
  },
};
