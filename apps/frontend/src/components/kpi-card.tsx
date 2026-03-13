import { type ReactNode } from "react";
import { clsx } from "clsx";

interface KpiCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon?: ReactNode;
  trend?: "up" | "down" | "neutral";
}

export default function KpiCard({ title, value, subtitle, icon, trend }: KpiCardProps) {
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm">
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium text-gray-500">{title}</p>
        {icon && <div className="text-gray-400">{icon}</div>}
      </div>
      <p className="mt-2 text-3xl font-semibold text-gray-900">{value}</p>
      {subtitle && (
        <p
          className={clsx(
            "mt-1 text-sm",
            trend === "up" && "text-green-600",
            trend === "down" && "text-red-600",
            (!trend || trend === "neutral") && "text-gray-500",
          )}
        >
          {subtitle}
        </p>
      )}
    </div>
  );
}
