import { Type } from "@sinclair/typebox";
import type { AnyAgentTool } from "openclaw/plugin-sdk/core";
import { api, ok, err } from "../client.js";

export const tmsListTrailers: AnyAgentTool = {
  name: "tms_list_trailers",
  label: "TMS: List Trailers",
  description:
    "List trailers in the fleet. Filter by status to find available trailers for assignment.",
  parameters: Type.Object({
    status: Type.Optional(
      Type.String({ description: "Filter by trailer status: available, in_use, out_of_service" }),
    ),
    page: Type.Optional(Type.Number({ description: "Page number, default 1" })),
    page_size: Type.Optional(Type.Number({ description: "Results per page, default 50" })),
  }),
  execute: async (_id, params) => {
    try {
      const qs = new URLSearchParams();
      if (params.status) qs.set("trailer_status", params.status);
      if (params.page) qs.set("page", String(params.page));
      if (params.page_size) qs.set("page_size", String(params.page_size));
      const trailers = await api.get(`/api/trailers?${qs}`);
      return ok(trailers);
    } catch (e) {
      return err(e);
    }
  },
};

export const tmsGetTrailer: AnyAgentTool = {
  name: "tms_get_trailer",
  label: "TMS: Get Trailer",
  description: "Get full details for a single trailer.",
  parameters: Type.Object({
    trailer_id: Type.String({ description: "UUID of the trailer" }),
  }),
  execute: async (_id, params) => {
    try {
      const trailer = await api.get(`/api/trailers/${params.trailer_id}`);
      return ok(trailer);
    } catch (e) {
      return err(e);
    }
  },
};

export const tmsCreateTrailer: AnyAgentTool = {
  name: "tms_create_trailer",
  label: "TMS: Create Trailer",
  description:
    "Add a new trailer to the fleet. Provide a unit number and type (dry_van, reefer, flatbed, step_deck).",
  parameters: Type.Object({
    trailer_number: Type.String({ description: "Unit number, e.g. 'TR-201'" }),
    trailer_type: Type.Optional(
      Type.String({ description: "Trailer type: dry_van (default), reefer, flatbed, step_deck" }),
    ),
  }),
  execute: async (_id, params) => {
    try {
      const trailer = await api.post("/api/trailers", {
        trailer_number: params.trailer_number,
        trailer_type: params.trailer_type ?? "dry_van",
      });
      return ok(trailer);
    } catch (e) {
      return err(e);
    }
  },
};

export const tmsUpdateTrailer: AnyAgentTool = {
  name: "tms_update_trailer",
  label: "TMS: Update Trailer",
  description: "Update a trailer's number, type, or status.",
  parameters: Type.Object({
    trailer_id: Type.String({ description: "UUID of the trailer to update" }),
    trailer_number: Type.Optional(Type.String({ description: "Updated unit number" })),
    trailer_type: Type.Optional(Type.String({ description: "Updated type: dry_van, reefer, flatbed, step_deck" })),
    status: Type.Optional(Type.String({ description: "Updated status: available, in_use, out_of_service" })),
  }),
  execute: async (_id, params) => {
    try {
      const { trailer_id, ...body } = params;
      const trailer = await api.patch(`/api/trailers/${trailer_id}`, body);
      return ok(trailer);
    } catch (e) {
      return err(e);
    }
  },
};
