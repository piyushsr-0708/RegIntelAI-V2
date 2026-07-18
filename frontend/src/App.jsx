/**
 * App.jsx — RegIntel AI V2
 *
 * Architecture:
 * - AuthProvider      : Demo auth via bcryptjs hashes (no backend)
 * - FrontendStateProvider: Loads /frontend_state.json once; supplies all pages
 * - No AnalysisSession, no ProtectedRoute (replaced by inline auth guard)
 * - No Axios anywhere in this tree
 *
 * Route guard: if not authenticated, redirect to /login.
 * FrontendState: loaded once after login, wrapped around authenticated routes only.
 */
import { BrowserRouter, Routes, Route, Navigate, useNavigate, useLocation } from "react-router-dom";
import { Suspense, lazy } from "react";
import { AuthProvider, useAuth } from "./context/AuthContext";
import { FrontendStateProvider, useFrontendState } from "./context/FrontendStateContext";
import { SessionProvider } from "./context/SessionContext";
import LoadingScreen from "./components/LoadingScreen";
import Topbar from "./components/Topbar";
import Sidebar from "./components/Sidebar";

// ─── Lazy-loaded pages ─────────────────────────────────────────────────────────
const Login              = lazy(() => import("./pages/Login"));
const Dashboard          = lazy(() => import("./pages/Dashboard"));
const Maps               = lazy(() => import("./pages/Maps"));
const MapDetail          = lazy(() => import("./pages/MapDetail"));
const Departments        = lazy(() => import("./pages/Departments"));
const Requirements       = lazy(() => import("./pages/Requirements"));
const Graph              = lazy(() => import("./pages/Graph"));
const AssignmentCenter   = lazy(() => import("./pages/AssignmentCenter"));
const DepartmentWorkspace= lazy(() => import("./pages/DepartmentWorkspace"));
const Pipeline           = lazy(() => import("./pages/Pipeline"));
const SessionDashboard   = lazy(() => import("./pages/SessionDashboard"));
const SessionMapDetail   = lazy(() => import("./pages/SessionMapDetail"));

// ─── Suspense fallback ─────────────────────────────────────────────────────────
const PageLoader = () => (
  <div style={{ display: "flex", justifyContent: "center", alignItems: "center", height: "50vh", color: "#10b981", fontSize: 13, fontWeight: 600, gap: 10 }}>
    <svg width="18" height="18" viewBox="0 0 24 24" style={{ animation: "spin 1s linear infinite" }}>
      <circle cx="12" cy="12" r="10" fill="none" stroke="rgba(16,185,129,0.2)" strokeWidth="3"/>
      <path d="M12 2a10 10 0 0 1 10 10" fill="none" stroke="#10b981" strokeWidth="3" strokeLinecap="round"/>
    </svg>
    Loading module…
  </div>
);

// ─── App shell for authenticated users ────────────────────────────────────────
function AppShell({ children }) {
  return (
    <div style={{ display: "flex", minHeight: "100vh", background: "#111827", fontFamily: "'Inter','Segoe UI',system-ui,sans-serif" }}>
      <Sidebar />
      <div style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0 }}>
        <Topbar />
        <main style={{ flex: 1, padding: "32px", overflow: "auto" }}>
          {children}
        </main>
      </div>
    </div>
  );
}

// ─── State-aware loader wrapper ────────────────────────────────────────────────
// Sits inside FrontendStateProvider and shows the loading screen until JSON is ready.
function StateGate({ children }) {
  const { loading, error } = useFrontendState();
  if (loading || error) return <LoadingScreen error={error} />;
  return children;
}

// ─── Auth guard ────────────────────────────────────────────────────────────────
function AuthGate({ children }) {
  const { isAuthenticated, authLoading } = useAuth();
  const location = useLocation();

  if (authLoading) return <LoadingScreen />;
  if (!isAuthenticated) return <Navigate to="/login" state={{ from: location }} replace />;
  return children;
}

// ─── Route Access Gate ────────────────────────────────────────────────────────
function RoleGate({ children, permission, requireAdmin }) {
  const { can, isAdmin } = useAuth();
  
  const hasPerm = permission ? can(permission) : true;
  const hasAdmin = requireAdmin ? !!isAdmin : true;

  if (hasPerm && hasAdmin) {
    return children;
  }

  return (
    <div style={{ padding: 40, textAlign: "center", display: "flex", flexDirection: "column", justifyContent: "center", height: "100%" }}>
      <h2 style={{ color: "#f87171", marginBottom: 10, fontSize: 24 }}>Access Denied</h2>
      <p style={{ color: "#94a3b8", fontSize: 14 }}>You do not have permission to access this page.</p>
    </div>
  );
}

// ─── All routes ────────────────────────────────────────────────────────────────
function AppRoutes() {
  const { isAuthenticated } = useAuth();

  return (
    <Routes>
      {/* Public */}
      <Route
        path="/login"
        element={
          <Suspense fallback={<PageLoader />}>
            <Login />
          </Suspense>
        }
      />

      {/* Protected — all wrapped inside FrontendStateProvider + SessionProvider */}
      <Route
        path="/*"
        element={
          <AuthGate>
            <FrontendStateProvider>
              <SessionProvider>
                <AppShell>
                  <Suspense fallback={<PageLoader />}>
                    <Routes>
                      <Route path="/"                  element={<RoleGate permission="pipeline:read" requireAdmin><StateGate><Dashboard /></StateGate></RoleGate>} />
                      <Route path="/maps"              element={<RoleGate permission="map:read" requireAdmin><StateGate><Maps /></StateGate></RoleGate>} />
                      <Route path="/registry/:id"      element={<RoleGate permission="map:read" requireAdmin><StateGate><MapDetail /></StateGate></RoleGate>} />
                      <Route path="/maps/:id"          element={<RoleGate permission="map:read" requireAdmin><StateGate><MapDetail /></StateGate></RoleGate>} />
                      <Route path="/departments"       element={<RoleGate permission="dept:read" requireAdmin><Departments /></RoleGate>} />
                      <Route path="/requirements"      element={<Requirements />} />
                      <Route path="/graph"             element={<Graph />} />
                      <Route path="/assignment-center" element={<RoleGate permission="map:approve"><AssignmentCenter /></RoleGate>} />
                      <Route path="/workspace"         element={<RoleGate permission="assign:read"><DepartmentWorkspace /></RoleGate>} />
                      <Route path="/pipeline"                    element={<RoleGate permission="pipeline:read"><Pipeline /></RoleGate>} />
                      <Route path="/session/:id"                 element={<RoleGate permission="pipeline:read"><SessionDashboard /></RoleGate>} />
                      <Route path="/session/:sessionId/map/:mapId" element={<RoleGate permission="pipeline:read"><StateGate><MapDetail /></StateGate></RoleGate>} />
                      {/* Catch-all */}
                      <Route path="*"                  element={<Navigate to="/" replace />} />
                    </Routes>
                  </Suspense>
                </AppShell>
              </SessionProvider>
            </FrontendStateProvider>
          </AuthGate>
        }
      />
    </Routes>
  );
}

// ─── Root ──────────────────────────────────────────────────────────────────────
export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
    </AuthProvider>
  );
}
