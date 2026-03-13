import { clsx } from "clsx";

const STATUS_COLORS: Record<string, string> = {
  quoted: "bg-gray-100 text-gray-700",
  booked: "bg-blue-100 text-blue-700",
  dispatched: "bg-indigo-100 text-indigo-700",
  arrived_pickup: "bg-yellow-100 text-yellow-800",
  loaded: "bg-orange-100 text-orange-700",
  in_transit: "bg-purple-100 text-purple-700",
  arrived_delivery: "bg-cyan-100 text-cyan-700",
  delivered: "bg-green-100 text-green-700",
  invoice_ready: "bg-emerald-100 text-emerald-700",
  invoiced: "bg-teal-100 text-teal-700",
  paid: "bg-green-200 text-green-800",
  closed: "bg-gray-200 text-gray-600",
  archived: "bg-gray-300 text-gray-500",
};

export default function LoadStatusBadge({ status }: { status: string }) {
  return (
    <span
      className={clsx(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium",
        STATUS_COLORS[status] || "bg-gray-100 text-gray-700",
      )}
    >
      {status.replace(/_/g, " ")}
    </span>
  );
}
