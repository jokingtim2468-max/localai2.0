import { createRoot } from "react-dom/client";
import "@fontsource/inter-tight/400.css";
import "@fontsource/inter-tight/600.css";
import "@fontsource/jetbrains-mono/400.css";
import "./theme.css";
import { App } from "./App";

createRoot(document.getElementById("root")!).render(<App />);
