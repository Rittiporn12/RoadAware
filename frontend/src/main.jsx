import { StrictMode, Suspense, lazy, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import Landing from "./components/Landing.jsx";
import { discoverServer } from "./config.js";
import "./styles.css";
import "./landing.css";
import "./dashboard.css";

// Two pages: the home page (default) and the app (#/app). The app loads only after the current demo-server
// address has been looked up, so its first readiness check already talks to the right server.
const App = lazy(() => discoverServer().then(() => import("./App.jsx")));
const Dashboard = lazy(() => import("./components/Dashboard.jsx"));
const pageOf = () => (/^#\/app/.test(window.location.hash) ? "app" : /^#\/dashboard/.test(window.location.hash) ? "dashboard" : "home");

function Root() {
  const [page, setPage] = useState(pageOf);
  useEffect(() => {
    discoverServer(); // start the lookup right away
    const on = () => setPage(pageOf());
    window.addEventListener("hashchange", on);
    return () => window.removeEventListener("hashchange", on);
  }, []);
  if (page === "home") return <Landing />;
  if (page === "dashboard") return <Suspense fallback={<div className="boot"><span className="boot-dot" />กำลังเปิดแดชบอร์ด…</div>}><Dashboard /></Suspense>;
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
