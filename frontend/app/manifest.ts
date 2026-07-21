import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "Toy Library",
    short_name: "Toy Library",
    description: "Manage your toy library membership, checkouts, and reservations",
    start_url: "/",
    display: "standalone",
    background_color: "#f9fafb",
    theme_color: "#2563eb",
    icons: [
      {
        src: "/icons/favicon-192x192.png",
        sizes: "192x192",
        type: "image/png",
      },
      {
        src: "/icons/favicon-512x512.png",
        sizes: "512x512",
        type: "image/png",
        purpose: "any",
      },
      {
        src: "/icons/android-maskable-512x512.png",
        sizes: "512x512",
        type: "image/png",
        purpose: "maskable",
      },
    ],
  };
}
