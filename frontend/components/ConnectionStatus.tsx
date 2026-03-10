import type { ConnectionState } from "@/lib/types";

interface ConnectionStatusProps {
  state: ConnectionState;
}

const STATUS_CONFIG: Record<
  ConnectionState,
  { color: string; label: string }
> = {
  disconnected: { color: "bg-gray-400", label: "Disconnected" },
  connecting: { color: "bg-yellow-400", label: "Connecting..." },
  connected: { color: "bg-green-400", label: "Connected" },
  reconnecting: { color: "bg-orange-400", label: "Reconnecting..." },
  failed: { color: "bg-red-400", label: "Connection Failed" },
};

export default function ConnectionStatus({ state }: ConnectionStatusProps) {
  const config = STATUS_CONFIG[state];

  return (
    <div className="flex items-center gap-2">
      <div className={`w-2 h-2 rounded-full ${config.color}`} />
      <span className="text-sm text-gray-600">{config.label}</span>
    </div>
  );
}
