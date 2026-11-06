import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ChevronRight, ChevronLeft, AlertCircle, X } from 'lucide-react';
import { api } from '../api/client';

/* ── Tag input ─────────────────────────────────────────────── */
function TagInput({ value, onChange, placeholder }) {
  const [input, setInput] = useState('');

  const add = (raw) => {
    const v = raw.trim();
    if (v && !value.includes(v)) onChange([...value, v]);
    setInput('');
  };

  const remove = (i) => onChange(value.filter((_, idx) => idx !== i));

  return (
    <div className="tag-field">
      {value.map((tag, i) => (
        <span key={i} className="tag-pill">
          {tag}
          <button onClick={() => remove(i)} type="button" aria-label="remove">
            <X size={11} />
          </button>
        </span>
      ))}
      <input
        className="tag-input-field"
        value={input}
        placeholder={value.length === 0 ? placeholder : 'Add more…'}
        onChange={e => setInput(e.target.value)}
        onKeyDown={e => {
          if (e.key === 'Enter' || e.key === ',') { e.preventDefault(); add(input); }
          if (e.key === 'Backspace' && !input && value.length) remove(value.length - 1);
        }}
        onBlur={() => input && add(input)}
      />
    </div>
  );
}

/* ── Vitals grid ───────────────────────────────────────────── */
function VitalsInput({ value, onChange }) {
  const fields = [
    { key: 'bp',     label: 'Blood Pressure', ph: '120/80 mmHg' },
    { key: 'temp',   label: 'Temperature',    ph: '37.0 °C' },
    { key: 'spo2',   label: 'SpO₂',           ph: '98%' },
    { key: 'hr',     label: 'Heart Rate',     ph: '72 bpm' },
    { key: 'rr',     label: 'Resp. Rate',     ph: '16 /min' },
    { key: 'weight', label: 'Weight',         ph: '70 kg' },
  ];
  return (
    <div className="form-row-3">
      {fields.map(f => (
        <div key={f.key} className="form-group" style={{ marginBottom: 0 }}>
          <label className="form-label">{f.label}</label>
          <input
            className="form-input"
            value={value[f.key] || ''}
            onChange={e => onChange({ ...value, [f.key]: e.target.value })}
            placeholder={f.ph}
          />
        </div>
      ))}
    </div>
  );
}

/* ── Step bar ──────────────────────────────────────────────── */
const STEPS = ['Patient Info', 'Symptoms', 'Medical History', 'Vitals'];

function StepBar({ current, onGo }) {
  return (
    <div className="step-track">
      {STEPS.map((label, i) => {
        const state = i + 1 === current ? 'active' : i + 1 < current ? 'done' : '';
        return (
          <div key={i} className="step-item">
            <div
              className={`step-circle ${state}`}
              onClick={() => i + 1 < current && onGo(i + 1)}
            >
              {state === 'done' ? '✓' : i + 1}
            </div>
            <span className={`step-label ${state}`}>{label}</span>
            {i < STEPS.length - 1 && (
              <div className={`step-line ${i + 1 < current ? 'done' : ''}`} />
            )}
          </div>
        );
      })}
    </div>
  );
}

/* ── Patient Form ──────────────────────────────────────────── */
export default function PatientForm() {
  const navigate = useNavigate();
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const [form, setForm] = useState({
    patient_name: '', patient_age: '', patient_gender: 'male',
    symptoms: [], symptom_duration: '', severity: 'moderate',
    medical_history: [], current_medications: [], allergies: [],
    vitals: {},
  });

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));

  const next = () => {
    if (step === 1 && (!form.patient_name || !form.patient_age)) {
      setError('Patient name and age are required.'); return;
    }
    if (step === 2 && form.symptoms.length === 0) {
      setError('Add at least one symptom.'); return;
    }
    setError('');
    setStep(s => Math.min(4, s + 1));
  };

  const submit = async () => {
    setLoading(true); setError('');
    try {
      const session = await api.createSession({
        ...form, patient_age: parseInt(form.patient_age),
      });
      navigate(`/session/${session.session_id}`);
    } catch (e) {
      setError(e.message || 'Failed to create session');
    } finally { setLoading(false); }
  };

  return (
    <div>
      {/* Header */}
      <div className="page-header">
        <h2>New Patient Assessment</h2>
        <p className="text-xs text-muted" style={{ marginTop: 2 }}>
          Enter patient details to start the AI clinical assessment pipeline
        </p>
      </div>

      <StepBar current={step} onGo={setStep} />

      {error && (
        <div className="alert alert-error" style={{ marginBottom: 16 }}>
          <AlertCircle size={14} style={{ flexShrink: 0, marginTop: 1 }} />
          {error}
        </div>
      )}

      <div className="card card-padded">

        {/* ── Step 1: Patient Info ───────────────────────────── */}
        {step === 1 && (
          <div>
            <div className="section-label">Patient Information</div>
            <div className="form-row">
              <div className="form-group">
                <label className="form-label">Full Name <span className="req">*</span></label>
                <input
                  id="patient-name"
                  className="form-input"
                  value={form.patient_name}
                  onChange={e => set('patient_name', e.target.value)}
                  placeholder="e.g. Rahul Sharma"
                  autoFocus
                />
              </div>
              <div className="form-group">
                <label className="form-label">Age <span className="req">*</span></label>
                <input
                  id="patient-age"
                  className="form-input"
                  type="number"
                  value={form.patient_age}
                  onChange={e => set('patient_age', e.target.value)}
                  placeholder="45"
                  min={0} max={150}
                />
              </div>
            </div>
            <div className="form-group">
              <label className="form-label">Gender</label>
              <select
                id="patient-gender"
                className="form-select"
                value={form.patient_gender}
                onChange={e => set('patient_gender', e.target.value)}
              >
                <option value="male">Male</option>
                <option value="female">Female</option>
                <option value="other">Other / Prefer not to say</option>
              </select>
            </div>
          </div>
        )}

        {/* ── Step 2: Symptoms ───────────────────────────────── */}
        {step === 2 && (
          <div>
            <div className="section-label">Chief Complaint & Symptoms</div>
            <div className="form-group">
              <label className="form-label">Symptoms <span className="req">*</span></label>
              <TagInput
                value={form.symptoms}
                onChange={v => set('symptoms', v)}
                placeholder="Type symptom and press Enter…"
              />
              <p className="form-hint">e.g. chest pain, shortness of breath, high fever</p>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label className="form-label">Duration</label>
                <input
                  id="symptom-duration"
                  className="form-input"
                  value={form.symptom_duration}
                  onChange={e => set('symptom_duration', e.target.value)}
                  placeholder="e.g. 3 days, 2 weeks"
                />
              </div>
              <div className="form-group">
                <label className="form-label">Severity</label>
                <select
                  id="severity"
                  className="form-select"
                  value={form.severity}
                  onChange={e => set('severity', e.target.value)}
                >
                  <option value="mild">Mild</option>
                  <option value="moderate">Moderate</option>
                  <option value="severe">Severe</option>
                </select>
              </div>
            </div>
          </div>
        )}

        {/* ── Step 3: Medical History ────────────────────────── */}
        {step === 3 && (
          <div>
            <div className="section-label">Medical Background</div>
            <div className="form-group">
              <label className="form-label">Past Medical History</label>
              <TagInput
                value={form.medical_history}
                onChange={v => set('medical_history', v)}
                placeholder="e.g. Type 2 Diabetes, Hypertension…"
              />
            </div>
            <div className="form-group">
              <label className="form-label">Current Medications</label>
              <TagInput
                value={form.current_medications}
                onChange={v => set('current_medications', v)}
                placeholder="e.g. Metformin 500mg, Lisinopril 10mg…"
              />
            </div>
            <div className="form-group">
              <label className="form-label">Allergies</label>
              <TagInput
                value={form.allergies}
                onChange={v => set('allergies', v)}
                placeholder="e.g. Penicillin, Sulfa drugs…"
              />
            </div>
          </div>
        )}

        {/* ── Step 4: Vitals ─────────────────────────────────── */}
        {step === 4 && (
          <div>
            <div className="section-label">Vital Signs <span style={{ fontWeight: 400, textTransform: 'none', letterSpacing: 0 }}>(optional)</span></div>
            <VitalsInput value={form.vitals} onChange={v => set('vitals', v)} />
            <div className="alert alert-info" style={{ marginTop: 16 }}>
              <AlertCircle size={14} style={{ flexShrink: 0, marginTop: 1 }} />
              Vitals are optional — they significantly improve diagnostic accuracy when provided.
            </div>
          </div>
        )}

        {/* ── Navigation ─────────────────────────────────────── */}
        <div style={{
          display: 'flex', justifyContent: 'space-between',
          alignItems: 'center', marginTop: 24,
          paddingTop: 20, borderTop: '1px solid var(--border)'
        }}>
          <button
            className="btn btn-secondary"
            onClick={() => setStep(s => Math.max(1, s - 1))}
            disabled={step === 1}
          >
            <ChevronLeft size={14} /> Back
          </button>

          {step < 4 ? (
            <button id={`step-${step}-next`} className="btn btn-primary" onClick={next}>
              Continue <ChevronRight size={14} />
            </button>
          ) : (
            <button
              id="start-assessment"
              className="btn btn-primary btn-lg"
              onClick={submit}
              disabled={loading}
            >
              {loading
                ? <><span className="spinner" /> Starting…</>
                : 'Start AI Assessment'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
