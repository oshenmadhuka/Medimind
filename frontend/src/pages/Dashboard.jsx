import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Activity, Plus, Clock, CheckCircle2, AlertCircle,
  Loader2, Brain, ChevronRight, Users
} from 'lucide-react';
import { api } from '../api/client';

const STATUS_CONFIG = {
  created:         { label: 'Created',         color: '#64748b' },
  running:         { label: 'Running',          color: '#0d9488' },
  awaiting_review: { label: 'Awaiting Review',  color: '#7c3aed' },
  completed:       { label: 'Completed',        color: '#16a34a' },
  error:           { label: 'Error',            color: '#dc2626' },
};

const P_CLASS = { P1: 'badge-p1', P2: 'badge-p2', P3: 'badge-p3', P4: 'badge-p4' };

export default function Dashboard() {
  const navigate = useNavigate();
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const data = await api.listSessions();
        setSessions(data.sessions || []);
      } catch { setSessions([]); }
      finally { setLoading(false); }
    };
    load();
    const t = setInterval(load, 10000);
    return () => clearInterval(t);
  }, []);

  const stats = {
    total:     sessions.length,
    active:    sessions.filter(s => s.status === 'running').length,
    review:    sessions.filter(s => s.status === 'awaiting_review').length,
    completed: sessions.filter(s => s.status === 'completed').length,
  };

  return (
    <div>
      {/* Page header */}
      <div style={{
        display: 'flex', alignItems: 'flex-start',
        justifyContent: 'space-between', marginBottom: 24
      }}>
        <div>
          <h2>Patient Assessments</h2>
          <p className="text-xs text-muted" style={{ marginTop: 2 }}>
            LangGraph multi-agent clinical decision support
          </p>
        </div>
        <button
          id="new-assessment-btn"
          className="btn btn-primary"
          onClick={() => navigate('/new')}
        >
          <Plus size={14} /> New Assessment
        </button>
      </div>

      {/* Stats */}
      <div className="stats-row">
        {[
          { label: 'Total Sessions',    value: stats.total,     icon: Users,        bg: '#f1f5f9', ic: '#64748b' },
          { label: 'Active',            value: stats.active,    icon: Loader2,      bg: '#f0fdfa', ic: '#0d9488' },
          { label: 'Pending Review',    value: stats.review,    icon: AlertCircle,  bg: '#ede9fe', ic: '#7c3aed' },
          { label: 'Completed',         value: stats.completed, icon: CheckCircle2, bg: '#f0fdf4', ic: '#16a34a' },
        ].map((s, i) => (
          <div key={i} className="stat-box">
            <div className="stat-box-header">
              <span className="stat-box-label">{s.label}</span>
              <div className="stat-box-icon" style={{ background: s.bg }}>
                <s.icon size={14} color={s.ic} />
              </div>
            </div>
            <div className="stat-box-value">{s.value}</div>
          </div>
        ))}
      </div>

      {/* Sessions table */}
      <div className="card">
        <div className="card-header">
          <span className="card-title">
            <Activity size={13} />
            Sessions
          </span>
          {sessions.length > 0 && (
            <span className="badge badge-slate">{sessions.length}</span>
          )}
        </div>

        {loading ? (
          <div style={{ padding: 40, textAlign: 'center' }}>
            <span className="spinner" />
            <p className="text-xs text-muted" style={{ marginTop: 8 }}>Loading sessions…</p>
          </div>
        ) : sessions.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state-icon">
              <Brain size={20} color="#94a3b8" />
            </div>
            <h3>No sessions yet</h3>
            <p>Start a new patient assessment to run the AI clinical pipeline.</p>
            <button
              className="btn btn-primary btn-sm"
              onClick={() => navigate('/new')}
            >
              <Plus size={13} /> Start assessment
            </button>
          </div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Patient</th>
                <th>Priority</th>
                <th>Status</th>
                <th>Session</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {sessions.map(s => {
                const st = STATUS_CONFIG[s.status] || STATUS_CONFIG.created;
                return (
                  <tr key={s.session_id}>
                    <td>
                      <span className="font-medium">{s.patient_name}</span>
                    </td>
                    <td>
                      {s.priority
                        ? <span className={`badge ${P_CLASS[s.priority] || 'badge-slate'}`}>{s.priority}</span>
                        : <span className="text-xs text-muted">—</span>}
                    </td>
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                        <div style={{
                          width: 6, height: 6, borderRadius: '50%',
                          background: st.color, flexShrink: 0
                        }} />
                        <span style={{ fontSize: '0.775rem', color: st.color }}>{st.label}</span>
                      </div>
                    </td>
                    <td>
                      <code style={{ fontSize: '0.725rem' }}>
                        {s.session_id.slice(0, 8)}
                      </code>
                    </td>
                    <td>
                      <button
                        className="btn btn-ghost btn-sm"
                        onClick={() => navigate(`/session/${s.session_id}`)}
                      >
                        View <ChevronRight size={13} />
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
