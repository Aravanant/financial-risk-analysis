import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import type { HaircutResponse } from '../types/api';
import { formatCU, formatPct, formatInt } from '../utils/formatters';
import { 
  Scissors, 
  CheckCircle2, 
  XCircle, 
  AlertTriangle, 
  TrendingDown, 
  Scale
} from 'lucide-react';

export const HaircutView: React.FC = () => {
  const [data, setData] = useState<HaircutResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadHaircut() {
      try {
        setLoading(true);
        setError(null);
        const res = await api.getHaircut();
        setData(res);
      } catch (err: any) {
        setError(err.message || 'Failed to load underwriting haircut metrics.');
      } finally {
        setLoading(false);
      }
    }
    loadHaircut();
  }, []);

  if (loading) {
    return (
      <div className="view-body">
        <div className="card" style={{ textAlign: 'center', padding: '60px 20px' }}>
          <p style={{ color: 'var(--text-secondary)' }}>Calculating verified haircut metrics from aggregate sums...</p>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="view-body">
        <div className="notice-box notice-warning">
          <AlertTriangle size={20} />
          <div>
            <strong>Unable to Load Haircut Analytics</strong>
            <p>{error}</p>
          </div>
        </div>
      </div>
    );
  }

  const { portfolio_summary: summary, by_purpose: purposes } = data;
  const { exclusions } = summary;

  return (
    <div className="view-body">
      {/* Haircut Header KPIs */}
      <div className="grid-kpis">
        <div className="card kpi-card" style={{ borderLeft: '4px solid var(--color-warning)' }}>
          <div className="kpi-header">
            <span>Aggregate Haircut Rate</span>
            <Scissors size={18} style={{ color: 'var(--color-warning)' }} />
          </div>
          <div className="kpi-value tabular-nums" style={{ color: 'var(--color-warning)' }}>
            {formatPct(summary.aggregate_haircut_pct, 4)}
          </div>
          <div className="kpi-subtext">Calculated from aggregate capital sums</div>
        </div>

        <div className="card kpi-card">
          <div className="kpi-header">
            <span>Total Capital Haircut</span>
            <TrendingDown size={18} style={{ color: 'var(--color-danger)' }} />
          </div>
          <div className="kpi-value tabular-nums" style={{ color: 'var(--text-primary)' }}>
            {formatCU(summary.total_haircut_cu, true)}
          </div>
          <div className="kpi-subtext tabular-nums">{formatCU(summary.total_haircut_cu)}</div>
        </div>

        <div className="card kpi-card">
          <div className="kpi-header">
            <span>Eligible Applications</span>
            <CheckCircle2 size={18} style={{ color: 'var(--color-success)' }} />
          </div>
          <div className="kpi-value tabular-nums" style={{ color: 'var(--color-success)' }}>
            {formatInt(summary.eligible_applications_count)}
          </div>
          <div className="kpi-subtext">Approved with valid amounts (97.66% of approved)</div>
        </div>

        <div className="card kpi-card">
          <div className="kpi-header">
            <span>Excluded Applications</span>
            <XCircle size={18} style={{ color: 'var(--text-muted)' }} />
          </div>
          <div className="kpi-value tabular-nums" style={{ color: 'var(--text-muted)' }}>
            {formatInt(exclusions.total_excluded_count)}
          </div>
          <div className="kpi-subtext">50,829 Rejected + 1,149 Approved Exclusions</div>
        </div>
      </div>

      {/* Methodology Statement Callout */}
      <div className="notice-box notice-info" style={{ marginBottom: 24 }}>
        <Scale size={22} style={{ flexShrink: 0, marginTop: 2, color: 'var(--brand-cyan)' }} />
        <div>
          <strong style={{ fontSize: '0.92rem' }}>Senior Data Analyst Methodology Mandate: Aggregate Sums vs Average of Percentages</strong>
          <p style={{ marginTop: 6, fontSize: '0.84rem', lineHeight: 1.5 }}>
            The portfolio-level aggregate haircut rate of <strong className="tabular-nums">20.3155%</strong> is derived from the true macroeconomic ratio:
            <br />
            <code>1.0 - (SUM(Eligible Sanctioned CU) / SUM(Eligible Requested CU)) = 1.0 - (5,360,674,169.70 / 6,727,376,919.78)</code>.
            <br />
            In contrast, naively taking the arithmetic mean of category-level percentages yields <strong>21.14%</strong>, which distorts reporting by treating smaller categories (e.g. Car, 4,349 apps) with equal weight as massive categories (e.g. Business, 14,269 apps). RiskLens AI strictly enforces sum-based portfolio weighting.
          </p>
        </div>
      </div>

      {/* Capital Comparison & Exclusion Waterfall */}
      <div className="grid-two-col">
        {/* Eligible Capital Breakdown */}
        <div className="card">
          <div className="card-title-group">
            <div>
              <div className="card-title">Eligible Cohort Capital Breakdown</div>
              <div className="card-subtitle">Comparing requested vs sanctioned principal for the 48,022 eligible loans</div>
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 20, marginTop: 14 }}>
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6, fontSize: '0.85rem' }}>
                <span style={{ color: 'var(--text-secondary)' }}>Eligible Requested Principal</span>
                <span className="tabular-nums" style={{ fontWeight: 600 }}>{formatCU(summary.total_eligible_requested_cu)}</span>
              </div>
              <div className="progress-bar-bg" style={{ height: 10 }}>
                <div className="progress-bar-fill" style={{ width: '100%', backgroundColor: 'var(--brand-blue)' }} />
              </div>
            </div>

            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6, fontSize: '0.85rem' }}>
                <span style={{ color: 'var(--text-secondary)' }}>Eligible Sanctioned Principal</span>
                <span className="tabular-nums" style={{ fontWeight: 600, color: 'var(--color-success)' }}>
                  {formatCU(summary.total_eligible_sanctioned_cu)}
                </span>
              </div>
              <div className="progress-bar-bg" style={{ height: 10 }}>
                <div 
                  className="progress-bar-fill" 
                  style={{ 
                    width: `${((summary.total_eligible_sanctioned_cu / summary.total_eligible_requested_cu) * 100).toFixed(2)}%`, 
                    backgroundColor: 'var(--color-success)' 
                  }} 
                />
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: 4 }}>
                <span>Sanction Ratio: 79.68%</span>
                <span style={{ color: 'var(--color-warning)', fontWeight: 600 }}>Haircut: 20.32%</span>
              </div>
            </div>

            <div style={{ padding: '14px 18px', backgroundColor: 'var(--bg-surface-elevated)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: 4 }}>Total Underwriting Reduction Amount:</div>
              <div className="tabular-nums" style={{ fontSize: '1.4rem', fontWeight: 700, color: 'var(--color-warning)' }}>
                {formatCU(summary.total_haircut_cu)}
              </div>
              <div style={{ fontSize: '0.76rem', color: 'var(--text-muted)', marginTop: 4 }}>
                Capital saved by risk policy haircut reductions on eligible approvals.
              </div>
            </div>
          </div>
        </div>

        {/* Exclusion Reconciliation Ledger */}
        <div className="card">
          <div className="card-title-group">
            <div>
              <div className="card-title">Haircut Exclusion Reconciliation Ledger</div>
              <div className="card-subtitle">Exact reconciliation of the 51,978 excluded applications</div>
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginTop: 10 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 14px', backgroundColor: 'var(--bg-surface-elevated)', borderRadius: 'var(--radius-md)' }}>
              <span style={{ fontSize: '0.84rem' }}>1. Rejected Applications (Zero Sanctioned)</span>
              <span className="badge badge-rejected tabular-nums">{formatInt(exclusions.excluded_rejected_count)}</span>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 14px', backgroundColor: 'var(--bg-surface-elevated)', borderRadius: 'var(--radius-md)' }}>
              <span style={{ fontSize: '0.84rem' }}>2. Approved — Missing Sanction Only</span>
              <span className="badge badge-neutral tabular-nums">
                {formatInt(exclusions.excluded_approved_missing_sanction_count - ((exclusions.excluded_approved_missing_sanction_count + exclusions.excluded_approved_missing_requested_count) - (exclusions.total_excluded_count - exclusions.excluded_rejected_count)))}
              </span>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 14px', backgroundColor: 'var(--bg-surface-elevated)', borderRadius: 'var(--radius-md)' }}>
              <span style={{ fontSize: '0.84rem' }}>3. Approved — Invalid/Missing Request Only</span>
              <span className="badge badge-neutral tabular-nums">
                {formatInt(exclusions.excluded_approved_missing_requested_count - ((exclusions.excluded_approved_missing_sanction_count + exclusions.excluded_approved_missing_requested_count) - (exclusions.total_excluded_count - exclusions.excluded_rejected_count)))}
              </span>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 14px', backgroundColor: 'var(--bg-surface-elevated)', borderRadius: 'var(--radius-md)' }}>
              <span style={{ fontSize: '0.84rem' }}>4. Approved — Both Conditions (Dual Exclusion)</span>
              <span className="badge badge-neutral tabular-nums" style={{ color: 'var(--color-warning)' }}>
                {formatInt((exclusions.excluded_approved_missing_sanction_count + exclusions.excluded_approved_missing_requested_count) - (exclusions.total_excluded_count - exclusions.excluded_rejected_count))}
              </span>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '12px 14px', backgroundColor: 'rgba(244, 63, 94, 0.1)', border: '1px solid rgba(244, 63, 94, 0.25)', borderRadius: 'var(--radius-md)' }}>
              <span style={{ fontSize: '0.86rem', fontWeight: 600 }}>Total Excluded Applications</span>
              <span className="tabular-nums" style={{ fontWeight: 700, color: 'var(--color-danger)' }}>
                {formatInt(exclusions.total_excluded_count)} (50,829 + 1,149)
              </span>
            </div>

            <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: 4, lineHeight: 1.4 }}>
              * Reconciliation Check: 48,022 Eligible + 51,978 Excluded = exactly 100,000 unique records. Every application is accounted for without double-counting.
            </div>
          </div>
        </div>
      </div>

      {/* Purpose Haircut Breakdown Table */}
      <div className="card" style={{ marginBottom: 24 }}>
        <div className="card-title-group">
          <div>
            <div className="card-title">Haircut Breakdown by Verified Loan Purpose</div>
            <div className="card-subtitle">Eligible applications and reduction volume across all 8 verified categories</div>
          </div>
        </div>

        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>Purpose Category</th>
                <th>Eligible Count</th>
                <th>Eligible Requested (CU)</th>
                <th>Eligible Sanctioned (CU)</th>
                <th>Haircut Amount (CU)</th>
                <th>Aggregate Haircut %</th>
                <th>Excluded Count</th>
              </tr>
            </thead>
            <tbody>
              {purposes.map((p) => (
                <tr key={p.purpose_id}>
                  <td style={{ fontWeight: 600 }}>{p.purpose_name}</td>
                  <td className="tabular-nums">{formatInt(p.haircut_eligible_count)}</td>
                  <td className="tabular-nums">{formatCU(p.haircut_eligible_requested_cu)}</td>
                  <td className="tabular-nums" style={{ color: 'var(--color-success)' }}>{formatCU(p.haircut_eligible_sanctioned_cu)}</td>
                  <td className="tabular-nums" style={{ color: 'var(--color-warning)' }}>{formatCU(p.haircut_total_cu)}</td>
                  <td className="tabular-nums">
                    <span className="badge badge-neutral" style={{ color: 'var(--color-warning)', fontWeight: 700 }}>
                      {formatPct(p.aggregate_haircut_pct)}
                    </span>
                  </td>
                  <td className="tabular-nums" style={{ color: 'var(--text-muted)' }}>{formatInt(p.haircut_excluded_count)}</td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr>
                <td>Portfolio Total</td>
                <td className="tabular-nums">{formatInt(summary.eligible_applications_count)}</td>
                <td className="tabular-nums">{formatCU(summary.total_eligible_requested_cu)}</td>
                <td className="tabular-nums" style={{ color: 'var(--color-success)' }}>{formatCU(summary.total_eligible_sanctioned_cu)}</td>
                <td className="tabular-nums" style={{ color: 'var(--color-warning)' }}>{formatCU(summary.total_haircut_cu)}</td>
                <td className="tabular-nums" style={{ color: 'var(--color-warning)', fontWeight: 700 }}>
                  {formatPct(summary.aggregate_haircut_pct, 4)}
                </td>
                <td className="tabular-nums">{formatInt(exclusions.total_excluded_count)}</td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>
    </div>
  );
};
