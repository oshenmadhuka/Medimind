import { CheckCircle2, Circle, Loader2 } from 'lucide-react';

const STEPS = [
  { id: 'triage_agent',    label: 'Triage',    key: 'triage_complete' },
  { id: 'diagnosis_agent', label: 'Diagnosis', key: 'diagnosis_complete' },
  { id: 'treatment_agent', label: 'Treatment', key: 'treatment_complete' },
  { id: 'note_summarizer', label: 'Note',      key: 'note_complete' },
  { id: 'human_review',    label: 'Review',    key: 'awaiting_review' },
];

function nodeState(step, ev) {
  if (!ev) return 'pending';
  if (ev[step.key]) return 'done';
  if (ev.current_agent === step.id) return 'active';
  return 'pending';
}

export default function AgentPipeline({ lastEvent }) {
  const activeIdx = STEPS.findIndex(s => lastEvent?.current_agent === s.id);
  const doneCount = STEPS.filter(s => lastEvent?.[s.key]).length;
  const pct = lastEvent?.completed ? 100 : Math.round((doneCount / STEPS.length) * 100);

  return (
    <div className="card" style={{ marginBottom: 16 }}>
      <div className="card-header">
        <span className="card-title">Agent Pipeline</span>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {lastEvent?.completed && <span className="badge badge-green">Complete</span>}
          {lastEvent?.awaiting_review && !lastEvent?.completed && (
            <span className="badge badge-violet">Awaiting Review</span>
          )}
          <span className="text-xs text-muted">{pct}%</span>
        </div>
      </div>

      <div className="pipeline-row">
        {STEPS.map((step, i) => {
          const state = nodeState(step, lastEvent);
          return (
            <div key={step.id} className="pipeline-step">
              <div className={`pipeline-node ${state}`}>
                <div className="pipeline-node-icon">
                  {state === 'done'
                    ? <CheckCircle2 size={14} color="#16a34a" />
                    : state === 'active'
                      ? <Loader2 size={14} color="#0d9488" style={{ animation: 'spin 0.7s linear infinite' }} />
                      : <Circle size={14} color="#94a3b8" />
                  }
                </div>
                <span className="pipeline-node-label">{step.label}</span>
              </div>
              {i < STEPS.length - 1 && (
                <div className={`pipeline-connector ${state === 'done' ? 'done' : state === 'active' ? 'active' : ''}`} />
              )}
            </div>
          );
        })}
      </div>

      <div style={{ padding: '0 20px 14px' }}>
        <div className="progress-track">
          <div className="progress-fill" style={{ width: `${pct}%` }} />
        </div>
      </div>
    </div>
  );
}
