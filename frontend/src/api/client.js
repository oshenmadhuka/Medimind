// MediMind API Client
const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const api = {
  // Create a new patient session
  createSession: async (patientData) => {
    const res = await fetch(`${API_BASE}/sessions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(patientData),
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  // Get session state
  getSession: async (sessionId) => {
    const res = await fetch(`${API_BASE}/sessions/${sessionId}`);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  // List all sessions
  listSessions: async () => {
    const res = await fetch(`${API_BASE}/sessions`);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  // Submit human review
  submitReview: async (sessionId, reviewData) => {
    const res = await fetch(`${API_BASE}/sessions/${sessionId}/review`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(reviewData),
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  // Stream session events (SSE)
  streamSession: (sessionId, onEvent, onError, onDone) => {
    const url = `${API_BASE}/sessions/${sessionId}/stream`;
    const es = new EventSource(url);

    es.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        onEvent(data);
        if (data.event === 'error') {
          es.close();
        }
        if (data.event === 'completed' || data.event === 'awaiting_human_review') {
          es.close();
          onDone && onDone(data);
        }
      } catch (err) {
        console.error('SSE parse error:', err);
      }
    };

    es.onerror = (e) => {
      es.close();
      onError && onError(e);
    };

    return () => es.close(); // cleanup
  },

  // Stream after review
  streamReview: (sessionId, onEvent, onDone) => {
    const url = `${API_BASE}/sessions/${sessionId}/stream-review`;
    const es = new EventSource(url);
    es.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        onEvent(data);
        if (data.event === 'completed') {
          es.close();
          onDone && onDone(data);
        }
      } catch {}
    };
    es.onerror = () => es.close();
    return () => es.close();
  },
};
