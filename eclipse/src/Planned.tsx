// Screens from the spec that are not built yet: say exactly what they will do, no filler.
const PLAN: Record<string, [string, string]> = {
  projects: ["Projects", "Open a folder: file tree, Monaco editor, git status, and a per-hunk Accept/Reject review of every change the agent makes."],
  game: ["Game kit", "Godot 4, Rust/Bevy and Three.js templates. One button builds and runs each, with live reload and a frame-time HUD."],
  gui: ["GUI builder", "Describe a screen and get PyQt6, CustomTkinter (Eclipse-themed) or React code with a live preview beside it."],
  shield: ["Anti-tamper lab", "Integrity checks for your own games: signed saves, hash checks at start, heartbeats, checksummed key values, plus a sample game and a report of what each check catches."],
  bench: ["Analysis bench", "Ghidra headless, radare2/rizin, binwalk, strings, otool/nm and lldb wrappers for your own binaries and firmware, with notes written to analysis/."],
  fork: ["Open-source adapter", "Paste a GitHub URL: clone it, map its structure, read its licence, and plan the changes to fit your spec. The licence file is always kept."],
  assets: ["Assets", "Per-project library of images, .glb/.fbx/.obj models and audio with previews. Optional Imgur upload with the key in the system keychain."],
};
export function Planned({ id }: { id: string }) {
  const [title, what] = PLAN[id] || ["", ""];
  return (
    <div className="view"><div className="page">
      <h2>{title}</h2>
      <div className="card">{what}</div>
      <div className="muted">Not built yet. Chat and Models work today.</div>
    </div></div>
  );
}
