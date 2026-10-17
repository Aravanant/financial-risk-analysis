import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import type { ServicingDemoResponse } from '../types/api';
import { formatCU } from '../utils/formatters';
import { 
  AlertTriangle, 
  Search, 
  ShieldAlert, 
  Calendar, 
  DollarSign, 
  CheckCircle2, 
  Clock, 
  Database,
  Info
} from 'lucide-react';

export const ServicingDemoView: React.FC = () => {
  const [appIdInput, setAppIdInput] = useState<string>('500001');
  const [activeAppId, setActiveAppId] = useState<number>(500001);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [servicingData, setServicingData] = useState<ServicingDemoResponse | null>(null);

  const fetchRecord = async (id: number) => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getServicingDemoRecord(id);
      setServicingData(data);
    } catch (err: any) {
      setError(err.message || `No synthetic servicing record found for Application ID ${id}. Note: Only approved loans in the 48,596 synthetic demo cohort have servicing records.`);
      setServicingData(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRecord(activeAppId);
  }, [activeAppId]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    const id = parseInt(appIdInput.trim(), 10);
    if (isNaN(id) || id < 1) {
      setError('Please enter a valid numeric Application ID (e.g. 500001).');
      return;
    }
    setActiveAppId(id);
  };

  const getStatusBadge = (status: string | null) => {
    if (!status) return <span className="badge badge-muted">Unknown</span>;
    const s = status.toLowerCase();
    if (s.includes('paid') || s.includes('current') || s.includes('on-time')) {
      return <span className="badge badge-approved"><CheckCircle2 size={12} style={{ marginRight: 4 }} />{status}</span>;
    }
    if (s.includes('late') || s.includes('grace')) {
      return <span className="badge badge-warning"><Clock size={12} style={{ marginRight: 4 }} />{status}</span>;
    }
    return <span className="badge badge-rejected"><AlertTriangle size={12} style={{ marginRight: 4 }} />{status}</span>;
  };

  return (
    <div className="view-container">
      {/* View Header */}
      <div className="view-header">
        <div>
          <h1 className="view-title">Simulated Servicing & Collection — Demonstration Data</h1>
          <p className="view-subtitle">
            Strictly quarantined downstream repayment simulator. Isolated from all primary underwriting analytics.
          </p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span className="badge badge-warning" style={{ fontSize: '0.85rem', padding: '6px 12px' }}>
            <ShieldAlert size={14} style={{ marginRight: 6 }} />
            SYNTHETIC DEMO ONLY
          </span>
        </div>
      </div>

      {/* Prominent Mandatory Quarantine Banner */}
      <div style={{
        background: 'linear-gradient(135deg, rgba(245, 158, 11, 0.12) 0%, rgba(217, 119, 6, 0.05) 100%)',
        border: '1px solid rgba(245, 158, 11, 0.35)',
        borderRadius: 'var(--radius-lg)',
        padding: '20px 24px',
        marginBottom: '24px',
        display: 'flex',
        gap: '16px',
        alignItems: 'flex-start'
      }}>
        <ShieldAlert size={28} color="var(--warning)" style={{ flexShrink: 0, marginTop: 2 }} />
        <div>
          <h2 style={{ fontSize: '1.05rem', fontWeight: 600, color: 'var(--warning)', margin: '0 0 6px 0' }}>
            Simulated Servicing & Collection — Demonstration Data Notice
          </h2>
          <p style={{ margin: 0, fontSize: '0.88rem', color: 'var(--text-secondary)', lineHeight: 1.55 }}>
            These records represent a <strong>synthetic 48,596-application post-origination servicing simulation</strong>. 
            They are <strong>NOT observed loan repayment outcomes</strong>. To preserve strict regulatory and audit integrity, 
            these values are <strong>never mixed into primary dashboard cards, underwriting charts, haircut calculations, 
            or executive business insights</strong>. This isolation is enforced at both the database schema layer and API routing layer.
          </p>
        </div>
      </div>

      {/* Quick Application Search Bar */}
      <div className="card" style={{ marginBottom: 24 }}>
        <form onSubmit={handleSearch} style={{ display: 'flex', flexWrap: 'wrap', gap: 12, alignItems: 'center' }}>
          <div style={{ position: 'relative', flex: '1 1 280px' }}>
            <Search size={16} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
            <input 
              type="text"
              className="input"
              style={{ paddingLeft: 36, width: '100%' }}
              placeholder="Enter Application ID (e.g. 500001, 500002...)"
              value={appIdInput}
              onChange={(e) => setAppIdInput(e.target.value)}
            />
          </div>
          <button type="submit" className="button button-primary" disabled={loading}>
            {loading ? 'Searching...' : 'Lookup Servicing Record'}
          </button>
          
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginLeft: 'auto' }}>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Sample IDs:</span>
            {[500001, 500002, 500005, 500010].map(id => (
              <button
                key={id}
                type="button"
                className="button button-secondary"
                style={{ fontSize: '0.75rem', padding: '4px 8px' }}
                onClick={() => {
                  setAppIdInput(String(id));
                  setActiveAppId(id);
                }}
              >
                #{id}
              </button>
            ))}
          </div>
        </form>
      </div>

      {/* Loading State */}
      {loading && (
        <div className="card" style={{ padding: 48, textAlign: 'center' }}>
          <div className="spinner" style={{ margin: '0 auto 16px auto' }} />
          <p style={{ color: 'var(--text-secondary)' }}>Loading synthetic servicing snapshot for #{activeAppId}...</p>
        </div>
      )}

      {/* Error / Not Found State */}
      {error && !loading && (
        <div className="card" style={{ padding: 32, textAlign: 'center', borderColor: 'rgba(239, 68, 68, 0.3)' }}>
          <AlertTriangle size={36} color="var(--danger)" style={{ margin: '0 auto 12px auto' }} />
          <h3 style={{ fontSize: '1.1rem', marginBottom: 8, color: 'var(--text-primary)' }}>Lookup Result</h3>
          <p style={{ color: 'var(--text-secondary)', maxWidth: 540, margin: '0 auto 16px auto', fontSize: '0.9rem' }}>
            {error}
          </p>
          <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            Tip: Try searching sample approved IDs such as <strong>500001</strong>, <strong>500002</strong>, or <strong>500005</strong>.
          </div>
        </div>
      )}

      {/* Servicing Record Content */}
      {servicingData && !loading && !error && (
        <>
          {/* Top KPI Cards */}
          <div className="metric-grid" style={{ marginBottom: 24 }}>
            <div className="card">
              <div className="metric-header">
                <span className="metric-title">Application Identifier</span>
                <Database size={16} className="metric-icon" />
              </div>
              <div className="metric-value">#{servicingData.application_id}</div>
              <div className="metric-footnote">
                Demonstration Cohort Row
              </div>
            </div>

            <div className="card">
              <div className="metric-header">
                <span className="metric-title">Simulated Payment Status</span>
                <Clock size={16} className="metric-icon" />
              </div>
              <div style={{ marginTop: 8 }}>
                {getStatusBadge(servicingData.simulated_payment_status)}
              </div>
              <div className="metric-footnote">
                Days Late: {servicingData.simulated_days_late !== null ? `${servicingData.simulated_days_late} Days` : '—'}
              </div>
            </div>

            <div className="card">
              <div className="metric-header">
                <span className="metric-title">Simulated Disbursement</span>
                <DollarSign size={16} className="metric-icon" />
              </div>
              <div className="metric-value">
                {formatCU(servicingData.simulated_disbursement_amount_cu)}
              </div>
              <div className="metric-footnote">
                Initial loan disbursement amount
              </div>
            </div>

            <div className="card">
              <div className="metric-header">
                <span className="metric-title">Outstanding Balance</span>
                <DollarSign size={16} className="metric-icon" />
              </div>
              <div className="metric-value" style={{ color: servicingData.simulated_outstanding_balance_cu && servicingData.simulated_outstanding_balance_cu > 0 ? 'var(--warning)' : 'var(--success)' }}>
                {formatCU(servicingData.simulated_outstanding_balance_cu)}
              </div>
              <div className="metric-footnote">
                Simulated residual principal
              </div>
            </div>
          </div>

          {/* Detailed Breakdown Card */}
          <div className="grid-2-col" style={{ marginBottom: 24 }}>
            <div className="card">
              <h2 className="card-title" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <Calendar size={18} color="var(--primary)" />
                Repayment Schedule & Timeline
              </h2>
              <table className="table" style={{ marginTop: 12 }}>
                <tbody>
                  <tr>
                    <td style={{ color: 'var(--text-secondary)', width: '45%' }}>Simulated Due Date</td>
                    <td style={{ fontWeight: 600 }}>{servicingData.simulated_due_date || '—'}</td>
                  </tr>
                  <tr>
                    <td style={{ color: 'var(--text-secondary)' }}>Simulated Payment Date</td>
                    <td style={{ fontWeight: 600 }}>{servicingData.simulated_payment_date || '—'}</td>
                  </tr>
                  <tr>
                    <td style={{ color: 'var(--text-secondary)' }}>Delinquency Metric</td>
                    <td>
                      {servicingData.simulated_days_late !== null ? (
                        <span style={{ 
                          fontWeight: 600, 
                          color: servicingData.simulated_days_late > 0 ? 'var(--danger)' : 'var(--success)' 
                        }}>
                          {servicingData.simulated_days_late === 0 ? 'On-Time (0 DPD)' : `${servicingData.simulated_days_late} Days Past Due`}
                        </span>
                      ) : '—'}
                    </td>
                  </tr>
                  <tr>
                    <td style={{ color: 'var(--text-secondary)' }}>Demonstration Isolation</td>
                    <td>
                      <span className="badge badge-warning">
                        {servicingData.demonstration_only ? 'True (Quarantined)' : 'False'}
                      </span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>

            <div className="card">
              <h2 className="card-title" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <DollarSign size={18} color="var(--primary)" />
                Cashflow & Collection Reconciliation
              </h2>
              <table className="table" style={{ marginTop: 12 }}>
                <tbody>
                  <tr>
                    <td style={{ color: 'var(--text-secondary)', width: '45%' }}>Amount Due (Period)</td>
                    <td style={{ fontWeight: 600 }}>{formatCU(servicingData.simulated_amount_due_cu)}</td>
                  </tr>
                  <tr>
                    <td style={{ color: 'var(--text-secondary)' }}>Amount Paid (Period)</td>
                    <td style={{ fontWeight: 600, color: 'var(--success)' }}>{formatCU(servicingData.simulated_amount_paid_cu)}</td>
                  </tr>
                  <tr>
                    <td style={{ color: 'var(--text-secondary)' }}>Collection Variance</td>
                    <td>
                      {servicingData.simulated_amount_due_cu !== null && servicingData.simulated_amount_paid_cu !== null ? (
                        <span style={{ 
                          fontWeight: 600,
                          color: (servicingData.simulated_amount_due_cu - servicingData.simulated_amount_paid_cu) > 0 ? 'var(--danger)' : 'var(--text-secondary)'
                        }}>
                          {formatCU(servicingData.simulated_amount_due_cu - servicingData.simulated_amount_paid_cu)}
                        </span>
                      ) : '—'}
                    </td>
                  </tr>
                  <tr>
                    <td style={{ color: 'var(--text-secondary)' }}>Remaining Principal</td>
                    <td style={{ fontWeight: 600 }}>{formatCU(servicingData.simulated_outstanding_balance_cu)}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          {/* Audit Verification Notice */}
          <div className="card" style={{ background: 'var(--bg-subtle)', borderColor: 'var(--border-subtle)' }}>
            <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
              <Info size={20} color="var(--primary)" style={{ flexShrink: 0 }} />
              <div>
                <span style={{ fontWeight: 600, color: 'var(--text-primary)', fontSize: '0.88rem' }}>
                  Backend Data Integrity Guarantee:
                </span>
                <p style={{ margin: '4px 0 0 0', fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
                  {servicingData.isolation_notice}
                </p>
              </div>
            </div>
          </div>
        </>
      )}

      {/* Structural Isolation Architecture Info */}
      <div className="card" style={{ marginTop: 24 }}>
        <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: 12 }}>
          Why RiskLens Isolates Servicing Simulations
        </h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 16, fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: 1.6 }}>
          <div style={{ padding: 12, background: 'var(--bg-subtle)', borderRadius: 'var(--radius-sm)' }}>
            <strong style={{ color: 'var(--text-primary)', display: 'block', marginBottom: 4 }}>1. Underwriting vs Servicing Boundary</strong>
            Credit underwriting models make decisions based strictly on pre-origination variables (bureau score, income, debt-to-income). Post-origination servicing records must never leak into origination models or retrospective underwriting assessments.
          </div>
          <div style={{ padding: 12, background: 'var(--bg-subtle)', borderRadius: 'var(--radius-sm)' }}>
            <strong style={{ color: 'var(--text-primary)', display: 'block', marginBottom: 4 }}>2. Zero Data Contamination</strong>
            The primary SQLite table <code>applications</code> holds 100,000 immutable origination records. The synthetic table <code>demo_synthetic_repayment_snapshot</code> is stored in a separate table, accessed by a dedicated endpoint <code>/api/v1/demo/servicing-snapshot/</code>.
          </div>
          <div style={{ padding: 12, background: 'var(--bg-subtle)', borderRadius: 'var(--radius-sm)' }}>
            <strong style={{ color: 'var(--text-primary)', display: 'block', marginBottom: 4 }}>3. Realistic Portfolio Auditing</strong>
            In commercial financial institutions, mixing synthetic downstream projections with real underwriting logs leads to regulatory violations (such as under-reporting haircut haircuts or distorting credit tier risk profiles). RiskLens enforces strict separation by design.
          </div>
        </div>
      </div>
    </div>
  );
};
