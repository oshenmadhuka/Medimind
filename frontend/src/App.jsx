import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import Dashboard from './pages/Dashboard';
import PatientForm from './components/PatientForm';
import SessionPage from './pages/SessionPage';
import './index.css';

export default function App() {
  return (
    <BrowserRouter>
      <div className="app-layout">
        <Sidebar />
        <main className="main-content">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/new" element={<PatientForm />} />
            <Route path="/session/:sessionId" element={<SessionPage />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
