import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, CheckCircle, AlertTriangle } from 'lucide-react';
import AgentPipeline from '../components/AgentPipeline';
import AgentThoughts from '../components/AgentThoughts';
import DiagnosisView, { HumanReviewPanel } from '../components/DiagnosisCard';
import { api } from '../api/client';

const STATUS_LABEL = {
  connecting:      { label: 'Connecting…',      color: '#64748b' },
  streaming:       { label: 'Running',           color: '#0d9488' },
  awaiting_review: { label: 'Awaiting Review',   color: '#7c3aed' },
  completed:       { label: 'Completed',         color: '#16a34a' },
  error:           { label: 'Error',             color: '#dc2626' },
};

const P_CLASS = { P1: 'badge-p1', P2: 'badge-p2', P3: 'badge-p3', P4: 'badge-p4' };

function getTime() {
  return new Date().toLocaleTimeString('en-US', { hour12: false });
}

export default function SessionPage() {
  const { sessionId } = useParams();
  const navigate = useNavigate();

  const [sessionData, setSessionData]     = useState(null);
  const [lastEvent, setLastEvent]         = useState(null);
  const [thoughts, setThoughts]           = useState([]);
  const [status, setStatus]               = useState('connecting');
  const [reviewDone, setReviewDone]       = useState(false);
  const [error, setError]                 = useState('');

  const log = useCallback((agent, message, highlight = false) => {
    setThoughts(p => [...p, { agent, message, time: getTime(), highlight }]);
  }, []);

  useEffect(() => {
    if (!sessionId) return;
    let cleanupStream = null;
    let isCancelled = false;

    const startStreaming = () => {
      log('supervisor', 'Initializing clinical assessment pipeline…', true);
      setStatus('streaming');

      cleanupStream = api.streamSession(
        sessionId,
        (ev) => {
          if (isCancelled) return;
          setLastEvent(prev => ({ ...prev, ...ev }));
          setSessionData(prev => ({
            triage: ev.triage || prev?.triage || null,
            diagnosis: ev.diagnosis || prev?.diagnosis || null,
            treatment: ev.treatment || prev?.treatment || null,
            note_summary: ev.note_summary || prev?.note_summary || null,
          }));

          const agent = ev.current_agent;
          if (agent && agent !== 'init') {
            const msgs = {
              supervisor:      `Routing → ${ev.next_agent || 'evaluating…'}`,
              triage_agent:    ev.triage ? `Triage: ${ev.triage.priority} — ${ev.triage.priority_label}` : 'Assessing urgency…',
              diagnosis_agent: ev.diagnosis ? `Diagnosis: ${ev.diagnosis.primary_diagnosis}` : 'Generating differential…',
              treatment_agent: ev.treatment ? `Treatment plan ready (${ev.treatment.medications?.length || 0} medications)` : 'Creating treatment plan…',
              note_summarizer: ev.note_summary ? 'Clinical note generated' : 'Summarising findings…',
              human_review:    'Paused — awaiting doctor review',
            };
            log(agent, msgs[agent] || 'Processing…', !!ev.triage || !!ev.diagnosis || !!ev.treatment || !!ev.note_summary);
          }

          if (ev.event === 'awaiting_human_review') setStatus('awaiting_review');
          if (ev.event === 'completed' || ev.completed) { setStatus('completed'); log('supervisor', 'Assessment complete', true); }
          if (ev.error || ev.event === 'error') {
            setStatus('error');
            setError(ev.message || ev.error || 'Agent execution encountered an error.');
          }
        },
        () => {
          if (!isCancelled) {
            setStatus('error');
            setError('Backend connection failed. Is the server running?');
          }
        },
        (done) => { if (done.event !== 'awaiting_human_review') setStatus('completed'); }
      );
    };

    // First check existing session state
    api.getSession(sessionId)
      .then(data => {
        if (isCancelled) return;
        if (data.triage || data.diagnosis || data.treatment || data.note_summary) {
          setSessionData({
            triage: data.triage,
            diagnosis: data.diagnosis,
            treatment: data.treatment,
            note_summary: data.note_summary,
          });
          setLastEvent(data);
        }

        if (data.completed) {
          setStatus('completed');
          log('supervisor', 'Loaded completed clinical assessment', true);
          return;
        }

        if (data.status === 'awaiting_review') {
          setStatus('awaiting_review');
          log('human_review', 'Paused — awaiting doctor review', true);
          return;
        }

        // Otherwise stream
        startStreaming();
      })
      .catch(() => {
        if (!isCancelled) startStreaming();
      });

    return () => {
      isCancelled = true;
      if (cleanupStream) cleanupStream();
    };
  }, [sessionId]);

  const handleReview = (approved) => {
    setReviewDone(true);
    setStatus('streaming');
    log('human_review', `Doctor ${approved ? 'APPROVED' : 'REJECTED'} the assessment`, true);

    api.streamReview(
      sessionId,
      (ev) => {
        setLastEvent(prev => ({ ...prev, ...ev }));
        if (ev.triage || ev.diagnosis || ev.treatment || ev.note_summary) {
          setSessionData(prev => ({
            triage: ev.triage || prev?.triage || null,
            diagnosis: ev.diagnosis || prev?.diagnosis || null,
            treatment: ev.treatment || prev?.treatment || null,
            note_summary: ev.note_summary || prev?.note_summary || null,
          }));
        }
        if (ev.completed) setStatus('completed');
      },
      async () => {
        setStatus('completed');
        log('supervisor', 'Assessment finalised', true);
        try {
          const finalData = await api.getSession(sessionId);
          setSessionData({
            triage: finalData.triage,
            diagnosis: finalData.diagnosis,
            treatment: finalData.treatment,
            note_summary: finalData.note_summary,
          });
          setLastEvent(prev => ({ ...prev, ...finalData }));
        } catch (e) {
          console.error('Failed to fetch final session data:', e);
        }
      }
    );
  };

  const st = STATUS_LABEL[status] || STATUS_LABEL.connecting;
  const priority = lastEvent?.triage?.priority;

  return (
    <div>
      {/* Header */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 12,
        marginBottom: 20, flexWrap: 'wrap'
      }}>
        <button className="btn btn-ghost btn-sm" onClick={() => navigate('/')}>
          <ArrowLeft size={13} /> Back
        </button>
        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <h2 style={{ fontSize: '1.1rem' }}>Clinical Assessment</h2>
            {priority && (
              <span className={`badge ${P_CLASS[priority] || 'badge-slate'}`}>{priority}</span>
            )}
            <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
              <div style={{ width: 7, height: 7, borderRadius: '50%', background: st.color,
                animation: status === 'streaming' ? 'pulse 1.5s ease-in-out infinite' : 'none'
              }} />
              <span style={{ fontSize: '0.775rem', color: st.color }}>{st.label}</span>
            </div>
          </div>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-3)', fontFamily: 'JetBrains Mono, monospace', marginTop: 2 }}>
            {sessionId}
          </div>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="alert alert-error" style={{ marginBottom: 16 }}>
          <AlertTriangle size={14} style={{ flexShrink: 0 }} />
          <div>
            {error}
            <div style={{ marginTop: 4, fontSize: '0.75rem' }}>
              Make sure the backend is running: <code>uvicorn backend.api.main:app --reload</code>
            </div>
          </div>
        </div>
      )}

      {/* Pipeline */}
      <AgentPipeline lastEvent={lastEvent} />

      {/* Two-column layout */}
      <div className="grid-2" style={{ alignItems: 'start' }}>
        {/* Left: Results */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <DiagnosisView sessionData={sessionData} />

          {status === 'awaiting_review' && !reviewDone && (
            <HumanReviewPanel sessionId={sessionId} onReviewComplete={handleReview} />
          )}

          {status === 'completed' && lastEvent?.human_review && (
            <div className="card card-padded">
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <CheckCircle size={16} color="#16a34a" />
                <span style={{ fontWeight: 600, fontSize: '0.875rem' }}>
                  {lastEvent.human_review.approved ? 'Assessment Approved & Finalised' : 'Assessment Revised'}
                </span>
              </div>
              <p style={{ marginTop: 6, fontSize: '0.8rem' }}>
                Reviewed by <strong>{lastEvent.human_review.reviewer_name}</strong>
                {lastEvent.human_review.reviewer_notes && ` — ${lastEvent.human_review.reviewer_notes}`}
              </p>
            </div>
          )}
        </div>

        {/* Right: Activity log (sticky) */}
        <div style={{ position: 'sticky', top: 24 }}>
          <AgentThoughts thoughts={thoughts} />
        </div>
      </div>

      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.4; }
        }
      `}</style>
    </div>
  );
}
