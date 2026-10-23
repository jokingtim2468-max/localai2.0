// 18px line icons, drawn for Eclipse (no icon font, works offline).
const P: Record<string, string> = {
  chat: "M4 5h12v8H9l-4 3v-3H4z",
  projects: "M3 6h5l2 2h7v8H3z",
  models: "M10 3l6 3.5v7L10 17l-6-3.5v-7zM4 6.5l6 3.5 6-3.5M10 10v7",
  recommend: "M10 3l2.2 4.5 4.8.7-3.5 3.4.8 4.9-4.3-2.3-4.3 2.3.8-4.9L3 8.2l4.8-.7z",
  train: "M3 16l4-5 3 3 4-6 3 4M3 4v12h14",
  game: "M5 8h10a3 3 0 0 1 0 6l-2-1H7l-2 1a3 3 0 0 1 0-6zM7 10v2M6 11h2M13 11h.01",
  gui: "M3 4h14v12H3zM3 7h14M7 7v9",
  studio: "M10 2l7 4v8l-7 4-7-4V6zM10 2v16M3 6l7 4 7-4",
  shield: "M10 3l6 2v5c0 4-3 6-6 7-3-1-6-3-6-7V5z",
  bench: "M4 15l4-4 3 3 5-6M4 4v12h12",
  fork: "M6 4v5a3 3 0 0 0 3 3h2a3 3 0 0 1 3 3v1M6 4a1.5 1.5 0 1 0 0 .01M14 4v4",
  assets: "M3 5h14v10H3zM6 12l3-3 3 3 2-2 3 3",
  settings: "M10 7a3 3 0 1 0 0 6 3 3 0 0 0 0-6zM10 2v2M10 16v2M2 10h2M16 10h2M4.3 4.3l1.4 1.4M14.3 14.3l1.4 1.4M4.3 15.7l1.4-1.4M14.3 5.7l1.4-1.4",
};
export function Icon({ name }: { name: string }) {
  return (
    <svg width="18" height="18" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d={P[name] || ""} />
    </svg>
  );
}
