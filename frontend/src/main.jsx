import { StrictMode, Suspense, lazy, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { flushSync } from "react-dom";
import Landing from "./components/Landing.jsx";
import { PageSkeleton, installSegments, reducedMotion } from "./components/site.jsx";
import { discoverServer } from "./config.js";
import "./styles.css";
import "./landing.css";
import "./dashboard.css";
import "./model.css";
import "./theme.css";

// Four pages on the hash: home (default), #/app, #/dashboard, #/model. The app loads only after the current
// demo-server address has been looked up, so its first readiness check already talks to the right server.
// Moving between pages uses the browser's view transition where available (the top bar stays put, the page
// underneath fades and rises); elsewhere the new page simply fades in.
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
    installSegments();
    const on = () => {
      const next = pageOf();
      if (document.startViewTransition && !reducedMotion()) {
        document.documentElement.dataset.vt = next === "app" || page === "app" ? "swap" : "page";
        const vt = document.startViewTransition(() => flushSync(() => setPage(next)));
        vt.finished.finally(() => { delete document.documentElement.dataset.vt; });
      } else setPage(next);
    };
    window.addEventListener("hashchange", on);
    return () => window.removeEventListener("hashchange", on);
  }, [page]);
  useEffect(() => { document.documentElement.dataset.page = page; }, [page]);
  if (page === "home") return <Landing />;
  if (page === "model") return <Suspense fallback={<PageSkeleton kind="model" />}><ModelPage /></Suspense>;
  if (page === "dashboard") return <Suspense fallback={<PageSkeleton kind="dashboard" />}><Dashboard /></Suspense>;
  return <Suspense fallback={<PageSkeleton kind="app" />}><App /></Suspense>;
}

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <Root />
  </StrictMode>,
);
