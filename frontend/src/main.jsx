import { StrictMode, Suspense, lazy, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import Landing from "./components/Landing.jsx";
import { discoverServer } from "./config.js";
import "./styles.css";
import "./landing.css";
import "./dashboard.css";
import "./model.css";

// Two pages: the home page (default) and the app (#/app). The app loads only after the current demo-server
// address has been looked up, so its first readiness check already talks to the right server.
const App = lazy(() => discoverServer().then(() => import("./App.jsx")));
const Dashboard = lazy(() => import("./components/Dashboard.jsx"));
const ModelPage = lazy(() => import("./components/ModelPage.jsx"));
const pageOf = () => {
  const h = window.location.hash;
  return /^#\/app/.test(h) ? "app" : /^#\/dashboard/.test(h) ? "dashboard" : /^#\/model/.test(h) ? "model" : "home";
};

function Root() {
  const [page, setPage] = useState(pageOf);
  useEffect(() => {
    discoverServer(); // start the lookup right away
    const on = () => setPage(pageOf());
    window.addEventListener("hashchange", on);
    return () => window.removeEventListener("hashchange", on);
  }, []);
  if (page === "home") return <Landing />;
  if (page === "model") return <Suspense fallback={<div className="boot"><span className="boot-dot" />กำลังเปิดหน้าโมเดล…</div>}><ModelPage /></Suspense>;
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
