import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import type { PortfolioKPIs, ChannelPerformanceItem, RiskTierItem, HaircutResponse } from '../types/api';
import { formatCU, formatPct, formatInt } from '../utils/formatters';
import { 
  Briefcase, 
  CheckCircle2, 
  XCircle, 
  TrendingUp, 
  AlertTriangle, 
  ArrowUpRight, 
  Sparkles
} from 'lucide-react';

export const OverviewView: React.FC = () => {
  const [kpis, setKpis] = useState<PortfolioKPIs | null>(null);
  const [channels, setChannels] = useState<ChannelPerformanceItem[]>([]);
  const [tiers, setTiers] = useState<RiskTierItem[]>([]);
  const [haircut, setHaircut] = useState<HaircutResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        setError(null);
        const [kpiRes, chRes, tierRes, hairRes] = await Promise.all([
          api.getOverview(),
          api.getChannels(),
          api.getRiskTiers(),
          api.getHaircut()
        ]);
        setKpis(kpiRes);
        setChannels(chRes);
        setTiers(tierRes);
        setHaircut(hairRes);
      } catch (err: any) {
        setError(err.message || 'Failed to load portfolio overview metrics.');
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  if (loading) {
    return (
      <div className="view-body">
        <div className="card" style={{ textAlign: 'center', padding: '60px 20px' }}>
          <div className="status-dot" style={{ margin: '0 auto 16px auto', width: 14, height: 14 }} />
          <p style={{ color: 'var(--text-secondary)' }}>Loading verified portfolio analytics from SQLite warehouse...</p>
        </div>
      </div>
    );
  }

  if (error || !kpis) {
    return (
      <div className="view-body">
        <div className="notice-box notice-warning">
          <AlertTriangle size={20} />
          <div>
            <strong>Unable to Load Overview Data</strong>
            <p style={{ marginTop: 4 }}>{error || 'An unexpected error occurred while communicating with the backend.'}</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="view-body">
      {/* Top Portfolio KPIs */}
      <div className="grid-kpis">
        <div className="card kpi-card">
          <div className="kpi-header">
            <span>Total Applications</span>
            <Briefcase size={18} style={{ color: 'var(--brand-cyan)' }} />
          </div>
          <div className="kpi-value tabular-nums">{formatInt(kpis.total_applications)}</div>
          <div className="kpi-subtext">Verified Deduplicated Population</div>
        </div>

        <div className="card kpi-card">
          <div className="kpi-header">
            <span>Approved Loans</span>
            <CheckCircle2 size={18} style={{ color: 'var(--color-success)' }} />
          </div>
          <div className="kpi-value tabular-nums" style={{ color: 'var(--color-success)' }}>
            {formatInt(kpis.approved_applications)}
          </div>
          <div className="kpi-subtext">
            Approval Rate: <strong className="tabular-nums">{formatPct(kpis.approval_rate_pct, 2)}</strong>
          </div>
        </div>

        <div className="card kpi-card">
          <div className="kpi-header">
            <span>Rejected Loans</span>
            <XCircle size={18} style={{ color: 'var(--color-danger)' }} />
          </div>
          <div className="kpi-value tabular-nums" style={{ color: 'var(--color-danger)' }}>
            {formatInt(kpis.rejected_applications)}
          </div>
          <div className="kpi-subtext">
            Rejection Rate: <strong className="tabular-nums">{formatPct(kpis.rejection_rate_pct, 2)}</strong>
          </div>
        </div>

        <div className="card kpi-card">
          <div className="kpi-header">
            <span>Aggregate Haircut</span>
            <TrendingUp size={18} style={{ color: 'var(--color-warning)' }} />
          </div>
          <div className="kpi-value tabular-nums" style={{ color: 'var(--color-warning)' }}>
            {haircut ? formatPct(haircut.portfolio_summary.aggregate_haircut_pct, 2) : '—'}
          </div>
          <div className="kpi-subtext">
            Reduction: <strong className="tabular-nums">{haircut ? formatCU(haircut.portfolio_summary.total_haircut_cu, true) : '—'}</strong>
          </div>
        </div>
      </div>

      {/* Portfolio Volumes vs Underwriting Reductions */}
      <div className="grid-two-col">
        <div className="card">
          <div className="card-title-group">
            <div>
              <div className="card-title">Portfolio Financial Capital</div>
              <div className="card-subtitle">Total requested vs sanctioned principal across all 100,000 applications</div>
            </div>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 18, marginTop: 12 }}>
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6, fontSize: '0.85rem' }}>
                <span style={{ color: 'var(--text-secondary)' }}>Total Requested Principal</span>
                <span className="tabular-nums" style={{ fontWeight: 600 }}>{formatCU(kpis.total_requested_cu)}</span>
              </div>
              <div className="progress-bar-bg">
                <div className="progress-bar-fill" style={{ width: '100%', backgroundColor: 'var(--brand-blue)' }} />
              </div>
            </div>

            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6, fontSize: '0.85rem' }}>
                <span style={{ color: 'var(--text-secondary)' }}>Total Sanctioned Principal</span>
                <span className="tabular-nums" style={{ fontWeight: 600, color: 'var(--color-success)' }}>
                  {formatCU(kpis.total_sanctioned_cu)}
                </span>
              </div>
              <div className="progress-bar-bg">
                <div 
                  className="progress-bar-fill" 
                  style={{ 
                    width: `${((kpis.total_sanctioned_cu / kpis.total_requested_cu) * 100).toFixed(1)}%`, 
                    backgroundColor: 'var(--color-success)' 
                  }} 
                />
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: 4 }}>
                Sanctioned Capital Ratio: {((kpis.total_sanctioned_cu / kpis.total_requested_cu) * 100).toFixed(2)}% of total requested volume
              </div>
            </div>

            <div style={{ padding: '12px 16px', borderRadius: 'var(--radius-md)', backgroundColor: 'var(--bg-surface-elevated)', border: '1px solid var(--border-subtle)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Haircut-Eligible Population</span>
                <span className="badge badge-neutral tabular-nums">48,022 Approved Applications</span>
              </div>
              <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: 4 }}>
                Restricted to approved loans with positive requested and non-null sanctioned principal.
              </div>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-title-group">
            <div>
              <div className="card-title">Data Quality & Governance Audit</div>
              <div className="card-subtitle">Corrupted negatives sanitized and missing values tracked</div>
            </div>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14, marginTop: 10 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px 14px', backgroundColor: 'var(--bg-surface-elevated)', borderRadius: 'var(--radius-md)' }}>
              <span style={{ fontSize: '0.84rem' }}>Composite Invalid Financial Records</span>
              <span className="badge badge-flag tabular-nums">{kpis.invalid_financials_count} Applications</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px 14px', backgroundColor: 'var(--bg-surface-elevated)', borderRadius: 'var(--radius-md)' }}>
              <span style={{ fontSize: '0.84rem' }}>Missing Sanctioned Amounts (NULLs)</span>
              <span className="badge badge-neutral tabular-nums">{kpis.missing_sanctioned_count} Total (575 App / 631 Rej)</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px 14px', backgroundColor: 'var(--bg-surface-elevated)', borderRadius: 'var(--radius-md)' }}>
              <span style={{ fontSize: '0.84rem' }}>Genuine Recorded Zero Sanctions</span>
              <span className="badge badge-approved tabular-nums" style={{ color: 'var(--text-primary)' }}>50,198 Rejections</span>
            </div>
            <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', lineHeight: 1.4 }}>
              * Zero ABS() conversion applied. Corrupted negative balances nullified with explicit audit flags. Source NULLs strictly preserved without default fallbacks.
            </div>
          </div>
        </div>
      </div>

      {/* Origination Channel Quick Summary */}
      <div className="card" style={{ marginBottom: 24 }}>
        <div className="card-title-group">
          <div>
            <div className="card-title">Channel Origination Volume & Conversion</div>
            <div className="card-subtitle">Distribution across all 4 conformed channels (100,000 total)</div>
          </div>
        </div>

        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>Channel Name</th>
                <th>Total Applications</th>
                <th>Approved</th>
                <th>Rejected</th>
                <th>Approval Rate</th>
                <th>Requested Volume</th>
                <th>Sanctioned Volume</th>
              </tr>
            </thead>
            <tbody>
              {channels.map((ch) => (
                <tr key={ch.channel_id}>
                  <td style={{ fontWeight: 600 }}>{ch.channel_name}</td>
                  <td className="tabular-nums">{formatInt(ch.total_applications)}</td>
                  <td className="tabular-nums" style={{ color: 'var(--color-success)' }}>{formatInt(ch.approved_applications)}</td>
                  <td className="tabular-nums" style={{ color: 'var(--color-danger)' }}>{formatInt(ch.rejected_applications)}</td>
                  <td className="tabular-nums">
                    <span className="badge badge-approved">{formatPct(ch.approval_rate_pct)}</span>
                  </td>
                  <td className="tabular-nums">{formatCU(ch.total_requested_cu, true)}</td>
                  <td className="tabular-nums">{formatCU(ch.total_sanctioned_cu, true)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Risk Tier Overview */}
      <div className="card" style={{ marginBottom: 24 }}>
        <div className="card-title-group">
          <div>
            <div className="card-title">Source Risk Tier Breakdown</div>
            <div className="card-subtitle">Observed approval rate and scorecard metrics across source-provided Default_Risk tiers</div>
          </div>
        </div>

        <div className="grid-three-col">
          {tiers.map((t) => (
            <div 
              key={t.risk_tier} 
              style={{ 
                backgroundColor: 'var(--bg-surface-elevated)', 
                border: '1px solid var(--border-subtle)', 
                borderRadius: 'var(--radius-md)', 
                padding: '18px' 
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                <span className={`badge badge-tier-${t.risk_tier.toLowerCase()}`}>{t.risk_tier} Risk Tier</span>
                <span className="tabular-nums" style={{ fontSize: '1.1rem', fontWeight: 700 }}>
                  {formatPct(t.tier_approval_rate_pct)} Appr
                </span>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6, fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span>Volume:</span>
                  <span className="tabular-nums" style={{ color: 'var(--text-primary)', fontWeight: 600 }}>{formatInt(t.total_applications)}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span>Avg Risk Score:</span>
                  <span className="tabular-nums" style={{ color: 'var(--text-primary)', fontWeight: 600 }}>{t.avg_proprietary_risk_score.toFixed(1)} / 100</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span>Avg Bureau Score:</span>
                  <span className="tabular-nums" style={{ color: 'var(--text-primary)', fontWeight: 600 }}>{t.avg_bureau_credit_score.toFixed(0)}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Data-Grounded Business Insights */}
      <div className="insights-card">
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, color: 'var(--brand-cyan)' }}>
          <Sparkles size={20} />
          <h3 style={{ fontSize: '1rem', fontWeight: 700 }}>Data-Grounded Business Insights & Executive Summary</h3>
        </div>
        <div className="insights-list">
          <div className="insight-item">
            <ArrowUpRight size={16} style={{ color: 'var(--brand-cyan)', flexShrink: 0, marginTop: 3 }} />
            <div>
              <strong>Balanced Portfolio Decision Funnel:</strong> The portfolio underwriting outcome is evenly divided at 
              {' '}<span className="tabular-nums">49.171%</span> Approved (49,171 loans) and <span className="tabular-nums">50.829%</span> Rejected (50,829 loans), 
              representing an institutional discipline across 100,000 evaluated originations.
            </div>
          </div>
          <div className="insight-item">
            <ArrowUpRight size={16} style={{ color: 'var(--brand-cyan)', flexShrink: 0, marginTop: 3 }} />
            <div>
              <strong>Channel Conversion Variance:</strong> The <strong>Online</strong> channel generated the largest volume (30,039 applications) 
              and the highest approval rate at <span className="tabular-nums">50.48%</span>, while the <strong>Agent</strong> channel produced the lowest approval rate at <span className="tabular-nums">47.38%</span> (9,676 approvals out of 20,422).
            </div>
          </div>
          <div className="insight-item">
            <ArrowUpRight size={16} style={{ color: 'var(--brand-cyan)', flexShrink: 0, marginTop: 3 }} />
            <div>
              <strong>Strict Risk-Tier Separation:</strong> Applications categorized as <strong>Low Risk</strong> achieved a <span className="tabular-nums">97.41%</span> approval rate 
              (12,922 approved out of 13,266), while <strong>High Risk</strong> applications faced a <span className="tabular-nums">97.59%</span> rejection rate (only 914 approvals out of 37,859).
            </div>
          </div>
          <div className="insight-item">
            <ArrowUpRight size={16} style={{ color: 'var(--brand-cyan)', flexShrink: 0, marginTop: 3 }} />
            <div>
              <strong>Substantial Haircut on Approved Capital:</strong> Underwriters approved loans with an aggregate haircut of <span className="tabular-nums">20.3155%</span>, 
              reducing 6.73B CU in eligible requested principal down to 5.36B CU in sanctioned principal, representing <span className="tabular-nums">1.37B CU</span> in risk mitigation.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
