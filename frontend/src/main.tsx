import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./index.css";

// Auto-reload on chunk load failure after deploy (stale index.html referencing
// removed hashed chunks). Reload once to re-fetch fresh index.html + chunks.
window.addEventListener("vite:preloadError", (event) => {
  event.preventDefault();
  const key = "std-cards:preload-reload";
  if (sessionStorage.getItem(key)) return;
  sessionStorage.setItem(key, "1");
  window.location.reload();
});

window.addEventListener("load", () => {
  sessionStorage.removeItem("std-cards:preload-reload");
});

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
