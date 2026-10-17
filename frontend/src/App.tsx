import React, { useState, useEffect } from 'react';
import { 
  BarChart3, 
  Network, 
  Briefcase, 
  Scissors, 
  FileSearch, 
  DatabaseZap, 
  ShieldCheck, 
  AlertTriangle,
  RefreshCw,
  Layers
} from 'lucide-react';
import { api } from './services/api';
import type { HealthResponse } from './types/api';

// Views
import { OverviewView } from './views/OverviewView';
import { ChannelView } from './views/ChannelView';
import { LoanPurposeView } from './views/LoanPurposeView';
import { HaircutView } from './views/HaircutView';
import { RiskView } from './views/RiskView';
import { ApplicationExplorerView } from './views/ApplicationExplorerView';
import { DataQualityView } from './views/DataQualityView';
import { ServicingDemoView } from './views/ServicingDemoView';

type TabKey = 
  | 'overview' 
  | 'channels' 
  | 'purposes' 
  | 'haircut' 
  | 'risk' 
  | 'explorer' 
  | 'quality' 
  | 'servicing';

const VALID_TABS: TabKey[] = [
  'overview', 
  'channels', 
  'purposes', 
  'haircut', 
  'risk', 
  'explorer', 
  'quality', 
  'servicing'
];

const getInitialTab = (): TabKey => {
  const hash = window.location.hash.replace('#', '') as TabKey;
  return VALID_TABS.includes(hash) ? hash : 'overview';
};

const App: React.FC = () => {
  const [activeTab, setActiveTabState] = useState<TabKey>(getInitialTab);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [healthLoading, setHealthLoading] = useState<boolean>(false);
  const [healthError, setHealthError] = useState<string | null>(null);

  const setActiveTab = (tab: TabKey) => {
    setActiveTabState(tab);
    window.location.hash = tab;
  };

  useEffect(() => {
    const handleHashChange = () => {
      const hash = window.location.hash.replace('#', '') as TabKey;
      if (VALID_TABS.includes(hash)) {
        setActiveTabState(hash);
      }
    };
    window.addEventListener('hashchange', handleHashChange);
    return () => window.removeEventListener('hashchange', handleHashChange);
  }, []);

  const checkHealth = async () => {
    setHealthLoading(true);
    try {
      const res = await api.getHealth();
      setHealth(res);
      setHealthError(null);
    } catch (err: any) {
      setHealthError(err.message || 'Backend unreachable');
      setHealth(null);
    } finally {
      setHealthLoading(false);
    }
  };

  useEffect(() => {
    checkHealth();
    // Poll health status every 30 seconds
    const interval = setInterval(checkHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  const renderActiveView = () => {
    switch (activeTab) {
      case 'overview':
        return <OverviewView />;
      case 'channels':
        return <ChannelView />;
      case 'purposes':
        return <LoanPurposeView />;
      case 'haircut':
        return <HaircutView />;
      case 'risk':
        return <RiskView />;
      case 'explorer':
        return <ApplicationExplorerView />;
      case 'quality':
        return <DataQualityView />;
      case 'servicing':
        return <ServicingDemoView />;
      default:
        return <OverviewView />;
    }
  };

  const getTabTitle = (tab: TabKey): string => {
    switch (tab) {
      case 'overview': return 'Executive Overview';
      case 'channels': return 'Origination Channel Analytics';
      case 'purposes': return 'Loan Purpose Segmentation';
      case 'haircut': return 'Portfolio Haircut & Sanction Audit';
      case 'risk': return 'Risk-Tier Distribution & Scorecards';
      case 'explorer': return 'Application Record Explorer';
      case 'quality': return 'Data Quality & Inconsistency Audit';
      case 'servicing': return 'Simulated Servicing & Collection — Demonstration Data';
    }
  };

  return (
    <div className="app-container">
      {/* Sidebar Navigation */}
      <aside className="sidebar">
        <div className="sidebar-header">
          <div className="brand-badge">
            <Layers size={22} color="var(--brand-cyan)" />
            <span>RiskLens<span style={{ color: 'var(--text-primary)' }}> AI</span></span>
          </div>
          <div className="brand-subtitle">
            Credit Analytics & Risk Engine
          </div>
        </div>

        <nav className="sidebar-nav">
          <div className="nav-section-label">Primary Portfolio Analytics</div>

          <button
            type="button"
            className={`nav-item ${activeTab === 'overview' ? 'active' : ''}`}
            onClick={() => setActiveTab('overview')}
          >
            <BarChart3 size={18} />
            <span>Overview</span>
          </button>

          <button
            type="button"
            className={`nav-item ${activeTab === 'channels' ? 'active' : ''}`}
            onClick={() => setActiveTab('channels')}
          >
            <Network size={18} />
            <span>Channel Analysis</span>
          </button>

          <button
            type="button"
            className={`nav-item ${activeTab === 'purposes' ? 'active' : ''}`}
            onClick={() => setActiveTab('purposes')}
          >
            <Briefcase size={18} />
            <span>Loan Purpose</span>
          </button>

          <button
            type="button"
            className={`nav-item ${activeTab === 'haircut' ? 'active' : ''}`}
            onClick={() => setActiveTab('haircut')}
          >
            <Scissors size={18} />
            <span>Haircut Analysis</span>
          </button>

          <button
            type="button"
            className={`nav-item ${activeTab === 'risk' ? 'active' : ''}`}
            onClick={() => setActiveTab('risk')}
          >
            <ShieldCheck size={18} />
            <span>Risk Tiers & Scores</span>
          </button>

          <button
            type="button"
            className={`nav-item ${activeTab === 'explorer' ? 'active' : ''}`}
            onClick={() => setActiveTab('explorer')}
          >
            <FileSearch size={18} />
            <span>Application Explorer</span>
          </button>

          <button
            type="button"
            className={`nav-item ${activeTab === 'quality' ? 'active' : ''}`}
            onClick={() => setActiveTab('quality')}
          >
            <DatabaseZap size={18} />
            <span>Data Quality</span>
          </button>

          <div className="nav-section-label" style={{ marginTop: 12, color: '#f59e0b' }}>
            Quarantined Demonstration
          </div>

          <button
            type="button"
            className={`nav-item nav-item-demo ${activeTab === 'servicing' ? 'active' : ''}`}
            onClick={() => setActiveTab('servicing')}
            title="Isolated synthetic repayment records (48,596 rows). Excluded from primary underwriting analytics."
          >
            <AlertTriangle size={18} />
            <span>Simulated Servicing</span>
            <span style={{ 
              marginLeft: 'auto', 
              fontSize: '0.65rem', 
              fontWeight: 700,
              padding: '2px 6px',
              borderRadius: '4px',
              backgroundColor: 'rgba(245, 158, 11, 0.25)',
              color: '#f59e0b'
            }}>
              DEMO
            </span>
          </button>
        </nav>

        <div className="sidebar-footer">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
            <span style={{ color: 'var(--text-secondary)', fontWeight: 600 }}>Portfolio Cohort:</span>
            <span style={{ color: 'var(--text-primary)', fontWeight: 700 }}>100,000 Apps</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
            <span style={{ color: 'var(--text-muted)' }}>Financial Unit:</span>
            <span style={{ color: 'var(--text-secondary)' }}>Credit Units (CU)</span>
          </div>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: 8 }}>
            RiskLens AI • v1.0.0 Production
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="main-content">
        {/* Top Header */}
        <header className="top-header">
          <div className="header-title-container">
            <span className="header-view-title">{getTabTitle(activeTab)}</span>
            {activeTab === 'servicing' && (
              <span className="badge badge-warning" style={{ fontSize: '0.72rem' }}>
                DEMO DATA — NOT OBSERVED OUTCOMES
              </span>
            )}
          </div>

          <div className="header-actions">
            {/* Real Backend Connection Indicator */}
            <div className="status-indicator">
              <span className={`status-dot ${health?.status === 'healthy' ? '' : 'offline'}`} />
              <span style={{ color: health?.status === 'healthy' ? 'var(--text-primary)' : 'var(--danger)' }}>
                {health?.status === 'healthy' 
                  ? `FastAPI Online (${health.record_counts?.fct_count?.toLocaleString() || '100,000'} rows)` 
                  : 'Backend Offline'}
              </span>
            </div>

            <button
              type="button"
              className="button button-secondary"
              style={{ padding: '6px 12px', fontSize: '0.8rem' }}
              onClick={checkHealth}
              disabled={healthLoading}
              title="Refresh connection status"
            >
              <RefreshCw size={14} className={healthLoading ? 'spin' : ''} style={{ marginRight: 6 }} />
              Ping API
            </button>
          </div>
        </header>

        {/* Dynamic View Mount */}
        <main className="view-body">
          {healthError && (
            <div style={{
              backgroundColor: 'rgba(239, 68, 68, 0.1)',
              border: '1px solid rgba(239, 68, 68, 0.3)',
              borderRadius: 'var(--radius-md)',
              padding: '12px 16px',
              marginBottom: 20,
              display: 'flex',
              alignItems: 'center',
              gap: 12
            }}>
              <AlertTriangle size={18} color="var(--danger)" />
              <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                <strong style={{ color: 'var(--danger)' }}>API Connection Warning: </strong>
                {healthError}. Ensure the FastAPI server is running locally on <code>http://127.0.0.1:8000</code>.
              </div>
            </div>
          )}

          {renderActiveView()}
        </main>
      </div>
    </div>
  );
};

export default App;
