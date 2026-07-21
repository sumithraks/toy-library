"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api-client";
import type { NotificationLogEntry, Paginated } from "@/lib/types";

export default function NotificationsPage() {
  const queryClient = useQueryClient();

  const { data } = useQuery({
    queryKey: ["notifications"],
    queryFn: () => apiFetch<Paginated<NotificationLogEntry>>("/notifications/"),
  });

  const markRead = async (id: string) => {
    await apiFetch(`/notifications/${id}/mark-read/`, { method: "POST" });
    queryClient.invalidateQueries({ queryKey: ["notifications"] });
  };

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Notifications</h1>
      <div className="rounded-lg border bg-white p-4">
        {data?.results.length ? (
          <ul className="divide-y">
            {data.results.map((n) => (
              <li key={n.id} className={`py-3 text-sm ${n.read_at ? "opacity-60" : ""}`}>
                <div className="flex items-center justify-between">
                  <p className="font-medium">{n.title}</p>
                  {!n.read_at && (
                    <button
                      onClick={() => markRead(n.id)}
                      className="text-xs text-blue-600 hover:underline"
                    >
                      Mark read
                    </button>
                  )}
                </div>
                <p className="text-gray-600">{n.body}</p>
                <p className="mt-1 text-xs text-gray-400">
                  {new Date(n.sent_at).toLocaleString()} · {n.channel}
                </p>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-gray-500">No notifications yet.</p>
        )}
      </div>
    </div>
  );
}
