import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import type { RiskTierItem } from '../types/api';
import { formatPct, formatInt } from '../utils/formatters';
import { AlertTriangle, AlertCircle, Sparkles } from 'lucide-react';

export const RiskView: React.FC = () => {
  const [tiers, setTiers] = useState<RiskTierItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadRiskTiers() {
      try {
        setLoading(true);
        setError(null);
        const data = await api.getRiskTiers();
        setTiers(data);
      } catch (err: any) {
        setError(err.message || 'Failed to load risk tier metrics.');
      } finally {
        setLoading(false);
      }
    }
    loadRiskTiers();
  }, []);

  if (loading) {
    return (
      <div className="view-body">
        <div className="card" style={{ textAlign: 'center', padding: '60px 20px' }}>
          <p style={{ color: 'var(--text-secondary)' }}>Loading source risk tier scorecard metrics...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="view-body">
        <div className="notice-box notice-warning">
          <AlertTriangle size={20} />
          <div>
            <strong>Unable to Load Risk Tier Analysis</strong>
            <p>{error}</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="view-body">
      {/* Critical Methodology Notice */}
      <div className="notice-box notice-warning" style={{ marginBottom: 24 }}>
        <AlertCircle size={22} style={{ flexShrink: 0, marginTop: 2, color: 'var(--color-warning)' }} />
        <div>
          <strong style={{ fontSize: '0.92rem' }}>Audit Mandate: Scorecard Labeling Notice</strong>
          <p style={{ marginTop: 4, fontSize: '0.84rem', lineHeight: 1.5 }}>
            The <code>proprietary_risk_score</code> in this dataset is an <strong>uncalibrated institutional scorecard rating on a 0–100 scale</strong>, 
            derived from internal risk heuristics. <strong>It is NOT a calibrated probability of default.</strong> Under no circumstances should a score of 
            e.g. <code>23.7</code> be labeled or treated as a 23.7% default probability. Tiers represent the source-provided <code>Default_Risk</code> classification.
          </p>
        </div>
      </div>

      {/* Risk Tier Cards */}
      <div className="grid-three-col" style={{ marginBottom: 24 }}>
        {tiers.map((t) => {
          const isLow = t.risk_tier === 'Low';
          const isMed = t.risk_tier === 'Medium';
          const badgeClass = isLow ? 'badge-tier-low' : isMed ? 'badge-tier-medium' : 'badge-tier-high';
          const themeColor = isLow ? 'var(--color-success)' : isMed ? 'var(--color-warning)' : 'var(--color-danger)';

          return (
            <div key={t.risk_tier} className="card" style={{ borderTop: `4px solid ${themeColor}` }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                <div>
                  <span className={`badge ${badgeClass}`} style={{ fontSize: '0.82rem', padding: '4px 12px' }}>
                    {t.risk_tier} Risk Tier
                  </span>
                  <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: 4 }}>
                    Source Default_Risk
                  </div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div className="tabular-nums" style={{ fontSize: '1.6rem', fontWeight: 700, color: themeColor }}>
                    {formatPct(t.tier_approval_rate_pct)}
                  </div>
                  <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>Approval Rate</div>
                </div>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: 12, marginTop: 16 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 12px', backgroundColor: 'var(--bg-surface-elevated)', borderRadius: 'var(--radius-sm)' }}>
                  <span style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>Total Originations:</span>
                  <span className="tabular-nums" style={{ fontWeight: 600 }}>{formatInt(t.total_applications)} ({((t.total_applications / 100000) * 100).toFixed(1)}%)</span>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 12px', backgroundColor: 'var(--bg-surface-elevated)', borderRadius: 'var(--radius-sm)' }}>
                  <span style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>Approved vs Rejected:</span>
                  <span className="tabular-nums" style={{ fontWeight: 600 }}>
                    <span style={{ color: 'var(--color-success)' }}>{formatInt(t.approved_count)}</span> / <span style={{ color: 'var(--color-danger)' }}>{formatInt(t.rejected_count)}</span>
                  </span>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 12px', backgroundColor: 'var(--bg-surface-elevated)', borderRadius: 'var(--radius-sm)' }}>
                  <span style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>Avg Proprietary Score:</span>
                  <span className="tabular-nums" style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                    {t.avg_proprietary_risk_score.toFixed(2)} / 100
                  </span>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 12px', backgroundColor: 'var(--bg-surface-elevated)', borderRadius: 'var(--radius-sm)' }}>
                  <span style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>Avg Bureau Credit Score:</span>
                  <span className="tabular-nums" style={{ fontWeight: 600, color: 'var(--brand-cyan)' }}>
                    {t.avg_bureau_credit_score.toFixed(1)} pts
                  </span>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 12px', backgroundColor: 'var(--bg-surface-elevated)', borderRadius: 'var(--radius-sm)' }}>
                  <span style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>Avg Normalized Score:</span>
                  <span className="tabular-nums" style={{ fontWeight: 600, color: 'var(--text-muted)' }}>
                    {t.avg_normalized_risk_score.toFixed(4)}
                  </span>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Decision Bifurcation Visualizer */}
      <div className="card" style={{ marginBottom: 24 }}>
        <div className="card-title-group">
          <div>
            <div className="card-title">Risk Tier Decision Bifurcation & Volume Allocation</div>
            <div className="card-subtitle">Visualizing the 100,000 application population across risk tiers</div>
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
          {tiers.map((t) => (
            <div key={t.risk_tier}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6, fontSize: '0.86rem' }}>
                <span style={{ fontWeight: 600 }}>{t.risk_tier} Risk Tier ({formatInt(t.total_applications)} loans)</span>
                <span className="tabular-nums">
                  <strong style={{ color: 'var(--color-success)' }}>{formatPct(t.tier_approval_rate_pct)} Approved</strong>
                  {' '}({formatInt(t.approved_count)})
                </span>
              </div>
              <div style={{ display: 'flex', width: '100%', height: 16, borderRadius: 'var(--radius-sm)', overflow: 'hidden' }}>
                <div 
                  style={{ 
                    width: `${t.tier_approval_rate_pct}%`, 
                    backgroundColor: 'var(--color-success)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '0.72rem',
                    color: '#000',
                    fontWeight: 700
                  }}
                >
                  {t.tier_approval_rate_pct > 8 ? `${t.tier_approval_rate_pct.toFixed(1)}%` : ''}
                </div>
                <div 
                  style={{ 
                    width: `${100 - t.tier_approval_rate_pct}%`, 
                    backgroundColor: 'var(--color-danger)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '0.72rem',
                    color: '#fff',
                    fontWeight: 700
                  }}
                >
                  {(100 - t.tier_approval_rate_pct) > 8 ? `${(100 - t.tier_approval_rate_pct).toFixed(1)}%` : ''}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Analytical Insights */}
      <div className="insights-card">
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, color: 'var(--brand-cyan)' }}>
          <Sparkles size={18} />
          <h3 style={{ fontSize: '0.95rem', fontWeight: 700 }}>Risk Tier Underwriting Observations</h3>
        </div>
        <div className="insights-list">
          <div className="insight-item">
            <span>•</span>
            <div>
              <strong>Extreme Policy Polarization at the Tails:</strong> Underwriting decisioning exhibits strict discipline at the extremities: 
              <span className="tabular-nums"> 97.41%</span> of Low Risk loans are approved, while <span className="tabular-nums">97.59%</span> of High Risk loans are rejected.
            </div>
          </div>
          <div className="insight-item">
            <span>•</span>
            <div>
              <strong>Medium Tier Represents the Core Operational Margin:</strong> Capturing <span className="tabular-nums">48,875 originations (48.88%)</span>, 
              the Medium tier is the central battleground where underwriters exercised discretionary scrutiny, approving <span className="tabular-nums">72.30%</span> and rejecting <span className="tabular-nums">27.70%</span>.
            </div>
          </div>
          <div className="insight-item">
            <span>•</span>
            <div>
              <strong>Bureau vs Proprietary Score Monotonicity:</strong> Credit bureau scores decrease strictly monotonically across tiers: 
              Low (<span className="tabular-nums">768.0</span>) &gt; Medium (<span className="tabular-nums">712.0</span>) &gt; High (<span className="tabular-nums">605.8</span>), 
              confirming strong alignment between third-party bureau histories and internal credit committee risk assignments.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
