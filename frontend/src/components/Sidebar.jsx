import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard, Plus, Activity, Shield,
  Microscope, Pill, FileText, UserCheck,
  Circle
} from 'lucide-react';

const agents = [
  { label: 'Triage Agent',      icon: Shield,     color: '#dc2626' },
  { label: 'Diagnosis Agent',   icon: Microscope, color: '#0d9488' },
  { label: 'Treatment Agent',   icon: Pill,       color: '#7c3aed' },
  { label: 'Note Summarizer',   icon: FileText,   color: '#ca8a04' },
  { label: 'Human Review',      icon: UserCheck,  color: '#16a34a' },
];

export default function Sidebar() {
  return (
    <div className="sidebar">
      {/* Logo */}
      <div className="sidebar-logo">
        <div className="logo-mark">
          <Activity size={16} color="#fff" strokeWidth={2.5} />
        </div>
        <div>
          <h1 style={{ color: '#fff', fontSize: '0.9rem' }}>MediMind</h1>
          <p style={{ fontSize: '0.65rem', color: '#64748b', margin: 0 }}>Clinical AI · v1.0</p>
        </div>
      </div>

      <nav className="sidebar-nav">
        {/* Main */}
        <div className="nav-label">Workspace</div>
        <NavLink
          to="/"
          end
          className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}
        >
          <LayoutDashboard size={14} /> Dashboard
        </NavLink>
        <NavLink
          to="/new"
          className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}
        >
          <Plus size={14} /> New Assessment
        </NavLink>

        {/* Agents */}
        <div className="nav-label" style={{ marginTop: 16 }}>AI Agents</div>
        {agents.map(({ label, icon: Icon, color }) => (
          <div key={label} className="nav-link" style={{ cursor: 'default', gap: 8 }}>
            <Icon size={13} color={color} />
            <span style={{ fontSize: '0.8rem' }}>{label}</span>
            <div
              className="nav-agent-dot"
              style={{ background: color, opacity: 0.5 }}
            />
          </div>
        ))}
      </nav>

      {/* Footer */}
      <div className="sidebar-footer">
        <div className="sidebar-version">
          <span style={{ color: '#475569' }}>LangGraph · Groq · ChromaDB</span>
        </div>
        <div style={{
          marginTop: 6,
          display: 'flex', gap: 4, alignItems: 'center',
          fontSize: '0.675rem', color: '#475569'
        }}>
          <div style={{ width: 6, height: 6, borderRadius: '50%', background: '#16a34a' }} />
          All systems operational
        </div>
      </div>
    </div>
  );
}
