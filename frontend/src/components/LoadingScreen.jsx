/**
 * LoadingScreen.jsx
 * Shown while frontend_state.json is being fetched on first load.
 */
import logo from "../assets/logo.jpg";

export default function LoadingScreen({ error }) {
  if (error) {
    return (
      <div style={{
        minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center',
        background: '#111827', flexDirection: 'column', gap: 20,
      }}>
        <div style={{
          width: 56, height: 56, borderRadius: 14,
          background: 'rgba(239,68,68,0.15)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          border: '1px solid rgba(239,68,68,0.3)',
        }}>
          <svg width="28" height="28" fill="none" viewBox="0 0 24 24" stroke="#ef4444" strokeWidth="2">
            <path d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
          </svg>
        </div>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: 18, fontWeight: 700, color: '#f1f5f9', marginBottom: 8 }}>
            Failed to load compliance data
          </div>
          <div style={{ fontSize: 13, color: '#64748b', maxWidth: 400 }}>
            Could not fetch <code style={{ color: '#f87171' }}>/frontend_state.json</code>.
            <br/>Ensure the Dashboard Aggregator has been run and the file exists.
          </div>
          <div style={{ marginTop: 12, fontSize: 12, color: '#475569', fontFamily: 'monospace', background: '#1a2332', padding: '8px 16px', borderRadius: 8, border: '1px solid rgba(255,255,255,0.07)' }}>
            Error: {error}
          </div>
          <button
            onClick={() => window.location.reload()}
            style={{ marginTop: 20, padding: '10px 24px', borderRadius: 8, background: '#10b981', color: '#fff', border: 'none', fontWeight: 700, cursor: 'pointer' }}
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div style={{
      minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center',
      background: 'linear-gradient(135deg, #0f172a 0%, #111827 50%, #0c1a30 100%)',
      flexDirection: 'column', gap: 28,
    }}>
      {/* Logo */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
        <img
          src={logo}
          alt="RegIntel AI"
          style={{ width: 56, height: 56, borderRadius: 14, objectFit: 'cover', boxShadow: '0 0 32px rgba(16,185,129,0.45)' }}
        />
        <div>
          <div style={{ fontSize: 24, fontWeight: 900, color: '#f1f5f9', letterSpacing: -0.5, lineHeight: 1 }}>RegIntel AI</div>
          <div style={{ fontSize: 12, color: '#10b981', fontWeight: 600, marginTop: 4, letterSpacing: 0.5 }}>
            Compliance Intelligence Platform
          </div>
        </div>
      </div>

      {/* Progress ring */}
      <div style={{ position: 'relative', width: 64, height: 64 }}>
        <svg width="64" height="64" viewBox="0 0 64 64" style={{ animation: 'spin 1.2s linear infinite' }}>
          <circle cx="32" cy="32" r="26" fill="none" stroke="rgba(16,185,129,0.12)" strokeWidth="4" />
          <circle
            cx="32" cy="32" r="26"
            fill="none"
            stroke="#10b981"
            strokeWidth="4"
            strokeDasharray="40 124"
            strokeLinecap="round"
          />
        </svg>
      </div>

      {/* Status */}
      <div style={{ textAlign: 'center' }}>
        <div style={{ fontSize: 14, fontWeight: 700, color: '#94a3b8', marginBottom: 6 }}>
          Loading compliance intelligence data…
        </div>
        <div style={{ fontSize: 12, color: '#475569' }}>
          Parsing 354 regulatory documents · 59,125 MAPs · 178,467 checks
        </div>
      </div>

      {/* Pipeline stages */}
      <div style={{
        display: 'flex', gap: 8, alignItems: 'center',
        background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)',
        borderRadius: 10, padding: '12px 20px',
      }}>
        {[
          'Interpreter', 'Reasoner', 'Rule Generator', 'Planner', 'Executor', 'Aggregator'
        ].map((stage, i) => (
          <div key={stage} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            {i > 0 && <div style={{ width: 16, height: 1, background: 'rgba(16,185,129,0.3)' }} />}
            <div style={{
              fontSize: 10.5, fontWeight: 700, color: '#34d399',
              background: 'rgba(16,185,129,0.1)', border: '1px solid rgba(16,185,129,0.2)',
              borderRadius: 6, padding: '3px 9px',
            }}>
              {stage}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
