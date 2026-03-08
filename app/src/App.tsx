import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import Telemetry from './pages/Telemetry';

export default function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/backend/telemetry" element={<Layout><Telemetry /></Layout>} />
      </Routes>
    </Router>
  )
}
