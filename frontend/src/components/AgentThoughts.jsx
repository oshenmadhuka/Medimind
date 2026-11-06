import { useEffect, useRef } from 'react';
import { Terminal } from 'lucide-react';

const AGENT_STYLE = {
  supervisor:      { color: '#7c3aed', label: 'supervisor' },
  triage_agent:    { color: '#dc2626', label: 'triage' },
  diagnosis_agent: { color: '#0d9488', label: 'diagnosis' },
  treatment_agent: { color: '#7c3aed', label: 'treatment' },
  note_summarizer: { color: '#ca8a04', label: 'notes' },
  human_review:    { color: '#16a34a', label: 'human_review' },
  init:            { color: '#64748b', label: 'system' },
};

export default function AgentThoughts({ thoughts }) {
  const endRef = useRef(null);
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [thoughts]);

  return (
    <div className="card">
      <div className="card-header">
        <span className="card-title">
          <Terminal size={13} /> Activity Log
        </span>
        <span className="badge badge-teal" style={{ fontSize: '0.65rem' }}>LIVE</span>
      </div>

      <div className="activity-log">
        {thoughts.length === 0 ? (
          <span style={{ color: '#475569', fontStyle: 'italic' }}>Waiting for agents…</span>
        ) : (
          thoughts.map((t, i) => {
            const ag = AGENT_STYLE[t.agent] || AGENT_STYLE.init;
            return (
              <div key={i} className={`log-line ${t.highlight ? 'highlight' : ''}`}>
                <span className="log-time">{t.time}</span>
                <span className="log-agent" style={{ color: ag.color }}>
                  [{ag.label}]
                </span>
                <span className="log-msg">{t.message}</span>
              </div>
            );
          })
        )}
        <div ref={endRef} />
      </div>
    </div>
  );
}
