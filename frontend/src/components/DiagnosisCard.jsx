import { useState } from 'react';
import {
  AlertTriangle, CheckCircle, TrendingUp,
  Pill, FileText, Shield, Microscope
} from 'lucide-react';
import { api } from '../api/client';

/* ── Triage ──────────────────────────────────────────────── */
function TriageSection({ data }) {
  if (!data) return null;
  const pc = { P1: 'badge-p1', P2: 'badge-p2', P3: 'badge-p3', P4: 'badge-p4' };
  return (
    <div className="card">
      <div className="card-header">
        <span className="card-title"><Shield size={13} /> Triage</span>
        <span className={`badge ${pc[data.priority] || 'badge-slate'}`}>
          {data.priority} — {data.priority_label}
        </span>
      </div>
      <div style={{ padding: '14px 20px' }}>
        <p style={{ fontSize: '0.825rem', lineHeight: 1.7, color: 'var(--text-2)' }}>
          {data.reasoning}
        </p>
        {data.escalate_immediately && (
          <div className="alert alert-error" style={{ marginTop: 12 }}>
            <AlertTriangle size={14} style={{ flexShrink: 0 }} />
            <strong>Immediate escalation required</strong>
          </div>
        )}
      </div>
    </div>
  );
}

/* ── Diagnosis ───────────────────────────────────────────── */
function DiagnosisSection({ data }) {
  if (!data) return null;
  return (
    <div className="card">
      <div className="card-header">
        <span className="card-title"><Microscope size={13} /> Differential Diagnosis</span>
        <span className="badge badge-slate">
          {Math.round((data.confidence || 0) * 100)}% confidence
        </span>
      </div>
      <div style={{ padding: '14px 20px' }}>
        {/* Primary */}
        <div className="dx-item primary">
          <div className="dx-rank">1</div>
          <div style={{ flex: 1 }}>
            <div className="dx-name">{data.primary_diagnosis}</div>
            <div style={{ display: 'flex', gap: 6, marginTop: 4 }}>
              <code style={{ fontSize: '0.725rem' }}>{data.icd10_code}</code>
              <span className="badge badge-teal" style={{ fontSize: '0.65rem' }}>Primary</span>
            </div>
          </div>
          <TrendingUp size={14} color="var(--teal-600)" />
        </div>

        {/* Differentials */}
        {data.differential_diagnoses?.slice(0, 3).map((d, i) => (
          <div key={i} className="dx-item">
            <div className="dx-rank">{i + 2}</div>
            <div style={{ flex: 1 }}>
              <div className="dx-name">{d.name}</div>
              <div className="dx-reason">{d.reasoning}</div>
            </div>
            <span className={`badge ${
              d.likelihood === 'High' ? 'badge-p2' :
              d.likelihood === 'Medium' ? 'badge-slate' : 'badge-p4'
            }`} style={{ fontSize: '0.65rem', flexShrink: 0 }}>
              {d.likelihood}
            </span>
          </div>
        ))}

        {/* Red flags */}
        {data.red_flags?.length > 0 && (
          <div className="alert alert-warning" style={{ marginTop: 12 }}>
            <AlertTriangle size={14} style={{ flexShrink: 0 }} />
            <div>
              <strong>Red flags: </strong>
              {data.red_flags.join(', ')}
            </div>
          </div>
        )}

        {/* Evidence */}
        {data.supporting_evidence?.length > 0 && (
          <>
            <div className="divider" />
            <div className="section-label">Supporting Evidence</div>
            <ul className="info-list">
              {data.supporting_evidence.slice(0, 4).map((e, i) => (
                <li key={i}><span className="dot" />{e}</li>
              ))}
            </ul>
          </>
        )}
      </div>
    </div>
  );
}

/* ── Treatment ───────────────────────────────────────────── */
function TreatmentSection({ data }) {
  if (!data) return null;
  return (
    <div className="card">
      <div className="card-header">
        <span className="card-title"><Pill size={13} /> Treatment Plan</span>
        <span className="badge badge-green">Evidence-Based</span>
      </div>
      <div style={{ padding: '14px 20px' }}>

        {/* Medications */}
        {data.medications?.length > 0 && (
          <>
            <div className="section-label">Medications</div>
            {data.medications.map((m, i) => (
              <div key={i} className="med-row">
                <div className="med-icon">
                  <Pill size={14} color="var(--text-2)" />
                </div>
                <div style={{ flex: 1 }}>
                  <div className="med-name">{m.name} — {m.dose}</div>
                  <div className="med-detail">
                    {m.frequency} · {m.route} · {m.duration} · For: {m.indication}
                  </div>
                </div>
              </div>
            ))}
          </>
        )}

        {/* Drug alerts */}
        {data.drug_interactions?.length > 0 && (
          <div className="alert alert-warning" style={{ marginTop: 12 }}>
            <AlertTriangle size={14} style={{ flexShrink: 0 }} />
            <div>
              <strong>{data.drug_interactions.length} drug interaction alert(s)</strong>
              <div style={{ marginTop: 4, fontSize: '0.775rem' }}>
                {data.drug_interactions[0]?.slice(0, 120)}…
              </div>
            </div>
          </div>
        )}

        <div className="divider" />

        {/* Plan steps */}
        <div className="section-label">Steps</div>
        <ul className="info-list">
          {data.treatment_plan?.slice(0, 5).map((s, i) => (
            <li key={i}><span className="dot" />{s}</li>
          ))}
        </ul>

        {/* Follow-up / Referrals */}
        <div style={{ display: 'flex', gap: 24, marginTop: 14, flexWrap: 'wrap' }}>
          <div>
            <div className="section-label" style={{ marginBottom: 2 }}>Follow-up</div>
            <span style={{ fontSize: '0.825rem', color: 'var(--text-1)', fontWeight: 500 }}>
              {data.follow_up_timeline}
            </span>
          </div>
          {data.referrals?.length > 0 && (
            <div>
              <div className="section-label" style={{ marginBottom: 4 }}>Referrals</div>
              <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                {data.referrals.map((r, i) => (
                  <span key={i} className="badge badge-violet" style={{ fontSize: '0.7rem' }}>{r}</span>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/* ── Clinical Note ───────────────────────────────────────── */
function NoteSection({ data }) {
  if (!data) return null;
  return (
    <div className="card">
      <div className="card-header">
        <span className="card-title"><FileText size={13} /> Clinical Summary</span>
      </div>
      <div style={{ padding: '14px 20px' }}>
        <p style={{ marginBottom: 14 }}>{data.summary}</p>
        <div className="grid-2" style={{ gap: 20 }}>
          <div>
            <div className="section-label">Key Findings</div>
            <ul className="info-list">
              {data.key_findings?.slice(0, 4).map((f, i) => (
                <li key={i}><span className="dot" style={{ background: 'var(--yellow-600)' }} />{f}</li>
              ))}
            </ul>
          </div>
          <div>
            <div className="section-label">Action Items</div>
            <ul className="info-list">
              {data.action_items?.slice(0, 4).map((a, i) => (
                <li key={i}><span className="dot" style={{ background: 'var(--red-600)' }} />{a}</li>
              ))}
            </ul>
          </div>
        </div>
        {data.references?.length > 0 && (
          <div style={{ marginTop: 12, fontSize: '0.725rem', color: 'var(--text-3)' }}>
            References: {data.references.join(' · ')}
          </div>
        )}
      </div>
    </div>
  );
}

/* ── Human Review Panel ──────────────────────────────────── */
export function HumanReviewPanel({ sessionId, onReviewComplete }) {
  const [reviewer, setReviewer] = useState('');
  const [notes, setNotes] = useState('');
  const [mods, setMods] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const submit = async (approved) => {
    if (!reviewer.trim()) { setError('Reviewer name required'); return; }
    setLoading(true); setError('');
    try {
      await api.submitReview(sessionId, {
        approved, reviewer_name: reviewer,
        reviewer_notes: notes, modifications: mods,
      });
      onReviewComplete(approved);
    } catch (e) { setError(e.message); }
    finally { setLoading(false); }
  };

  return (
    <div className="review-panel">
      <div className="review-header">
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 2 }}>
            <span style={{ fontWeight: 600, fontSize: '0.9rem' }}>Doctor Review Required</span>
            <span className="review-badge">Pending approval</span>
          </div>
          <p style={{ fontSize: '0.775rem', color: 'var(--text-3)', margin: 0 }}>
            Review the AI assessment below and approve or reject with modifications.
          </p>
        </div>
      </div>
      <div className="review-body">
        {error && (
          <div className="alert alert-error" style={{ marginBottom: 14 }}>
            <AlertTriangle size={13} />{error}
          </div>
        )}
        <div className="form-row" style={{ marginBottom: 14 }}>
          <div className="form-group" style={{ marginBottom: 0 }}>
            <label className="form-label">Reviewer Name <span className="req">*</span></label>
            <input
              id="reviewer-name"
              className="form-input"
              value={reviewer}
              onChange={e => setReviewer(e.target.value)}
              placeholder="Dr. Priya Mehta"
            />
          </div>
          <div className="form-group" style={{ marginBottom: 0 }}>
            <label className="form-label">Modifications (if rejecting)</label>
            <input
              id="modifications"
              className="form-input"
              value={mods}
              onChange={e => setMods(e.target.value)}
              placeholder="Specify what to change…"
            />
          </div>
        </div>
        <div className="form-group">
          <label className="form-label">Review Notes</label>
          <textarea
            id="reviewer-notes"
            className="form-textarea"
            rows={2}
            value={notes}
            onChange={e => setNotes(e.target.value)}
            placeholder="Clinical observations, agreement or concerns…"
          />
        </div>
        <div style={{ display: 'flex', gap: 10 }}>
          <button
            id="approve-btn"
            className="btn btn-success"
            onClick={() => submit(true)}
            disabled={loading}
            style={{ flex: 1 }}
          >
            {loading ? <span className="spinner" /> : <CheckCircle size={14} />}
            Approve & Finalize
          </button>
          <button
            id="reject-btn"
            className="btn btn-danger"
            onClick={() => submit(false)}
            disabled={loading}
          >
            Reject & Revise
          </button>
        </div>
      </div>
    </div>
  );
}

/* ── Main export ─────────────────────────────────────────── */
export default function DiagnosisView({ sessionData }) {
  if (!sessionData) return null;
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      <TriageSection   data={sessionData.triage} />
      <DiagnosisSection data={sessionData.diagnosis} />
      <TreatmentSection data={sessionData.treatment} />
      <NoteSection      data={sessionData.note_summary} />
    </div>
  );
}
