import React from "react";
import { Trash2 } from "lucide-react";

interface ClientCardProps {
  client: any;
  onDelete: (id: number) => void;
}

export const ClientCard = React.memo(function ClientCard({ client: c, onDelete }: ClientCardProps) {
  return (
    <div className="flex justify-between items-start p-4 bg-zinc-900/50 border border-zinc-800/80 rounded-xl text-xs">
      <div className="space-y-1">
        <h4 className="text-sm font-bold text-zinc-100">{c.name}</h4>
        {c.email && <div className="text-zinc-400">Email: {c.email}</div>}
        {c.phone && <div className="text-zinc-400">Phone: {c.phone}</div>}
        {c.notes && (
          <div className="bg-zinc-955/60 p-2.5 rounded border border-zinc-850 text-zinc-400 font-mono mt-2 text-[10px] leading-relaxed">
            🔒 <strong className="text-zinc-300">Decrypted Notes:</strong> {c.notes}
          </div>
        )}
      </div>
      <button
        onClick={() => onDelete(c.id)}
        className="text-zinc-500 hover:text-rose-400 p-1.5 rounded-lg hover:bg-zinc-900 transition cursor-pointer"
      >
        <Trash2 className="w-4 h-4" />
      </button>
    </div>
  );
});
