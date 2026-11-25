import { StrictMode, Suspense, lazy, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import Landing from "./components/Landing.jsx";
import { discoverServer } from "./config.js";
import "./styles.css";
import "./landing.css";

// Two pages: the home page (default) and the app (#/app). The app loads only after the current demo-server
// address has been looked up, so its first readiness check already talks to the right server.
const App = lazy(() => discoverServer().then(() => import("./App.jsx")));
const isApp = () => /^#\/app/.test(window.location.hash);

function Root() {
  const [page, setPage] = useState(isApp() ? "app" : "home");
  useEffect(() => {
    discoverServer(); // start the lookup right away
    const on = () => setPage(isApp() ? "app" : "home");
    window.addEventListener("hashchange", on);
    return () => window.removeEventListener("hashchange", on);
  }, []);
  if (page === "home") return <Landing />;
  return (
    <Suspense fallback={<div className="boot"><span className="boot-dot" />กำลังเปิด RoadAware…</div>}>
      <App />
    </Suspense>
  );
}

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <Root />
  </StrictMode>,
);
