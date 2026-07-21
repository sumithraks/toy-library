import { apiFetch } from "./api-client";

function urlBase64ToUint8Array(base64String: string) {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
  const rawData = atob(base64);
  return Uint8Array.from([...rawData].map((c) => c.charCodeAt(0)));
}

export async function subscribeToPush() {
  if (!("serviceWorker" in navigator) || !("PushManager" in window)) {
    throw new Error("Push notifications are not supported in this browser");
  }
  const vapidKey = process.env.NEXT_PUBLIC_VAPID_PUBLIC_KEY;
  if (!vapidKey) throw new Error("Missing VAPID public key");

  const registration = await navigator.serviceWorker.register("/sw.js");
  await navigator.serviceWorker.ready;

  const subscription = await registration.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey: urlBase64ToUint8Array(vapidKey),
  });

  const json = subscription.toJSON();
  await apiFetch("/push-subscriptions/", {
    method: "POST",
    body: {
      endpoint: json.endpoint,
      p256dh_key: json.keys?.p256dh,
      auth_key: json.keys?.auth,
      user_agent: navigator.userAgent,
    },
  });
  return subscription;
}
