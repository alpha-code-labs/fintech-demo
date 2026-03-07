import { Routes, Route } from 'react-router-dom';
import Layout from './components/layout/Layout';
import GlobalPulse from './pages/GlobalPulse';
import SignalScanner from './pages/SignalScanner';
import StockDeepDive from './pages/StockDeepDive';
import PortfolioMonitor from './pages/PortfolioMonitor';
import Reporting from './pages/Reporting';
import WeeklyBriefing from './pages/WeeklyBriefing';
import DataBlueprint from './pages/DataBlueprint';

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<GlobalPulse />} />
        <Route path="/scanner" element={<SignalScanner />} />
        <Route path="/stock/:symbol" element={<StockDeepDive />} />
        <Route path="/portfolio" element={<PortfolioMonitor />} />
        <Route path="/reporting" element={<Reporting />} />
        <Route path="/briefing" element={<WeeklyBriefing />} />
        <Route path="/blueprint" element={<DataBlueprint />} />
      </Routes>
    </Layout>
  );
}
