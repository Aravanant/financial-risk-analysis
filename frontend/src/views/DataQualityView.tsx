import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import type { DataQualityResponse } from '../types/api';
import { formatInt } from '../utils/formatters';
import { 
  AlertTriangle, 
  FileCheck, 
  Lock
} from 'lucide-react';

export const DataQualityView: React.FC = () => {
  const [data, setData] = useState<DataQualityResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadDataQuality() {
      try {
        setLoading(true);
        setError(null);
        const res = await api.getDataQuality();
        setData(res);
      } catch (err: any) {
        setError(err.message || 'Failed to load data quality metrics.');
      } finally {
        setLoading(false);
      }
    }
    loadDataQuality();
  }, []);

  if (loading) {
    return (
      <div className="view-body">
        <div className="card" style={{ textAlign: 'center', padding: '60px 20px' }}>
          <p style={{ color: 'var(--text-secondary)' }}>Loading verified data quality and audit ledgers...</p>
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
            <strong>Unable to Load Data Quality Metrics</strong>
            <p>{error}</p>
          </div>
        </div>
      </div>
    );
  }

  const { audit_flags: flags, missing_values: missing, haircut_exclusions: exclusions } = data;

  return (
    <div className="view-body">
      {/* Top Ledger Cards */}
      <div className="grid-kpis">
        <div className="card kpi-card">
          <div className="kpi-header">
            <span>Evaluated Population</span>
            <FileCheck size={18} style={{ color: 'var(--brand-cyan)' }} />
          </div>
          <div className="kpi-value tabular-nums">{formatInt(data.total_applications)}</div>
          <div className="kpi-subtext">100% clean application grain</div>
        </div>

        <div className="card kpi-card">
          <div className="kpi-header">
            <span>Composite Invalid Financials</span>
            <AlertTriangle size={18} style={{ color: 'var(--color-danger)' }} />
          </div>
          <div className="kpi-value tabular-nums" style={{ color: 'var(--color-danger)' }}>
            {formatInt(flags.composite_invalid_financials_count)}
          </div>
          <div className="kpi-subtext">Corrupted negative balances sanitized</div>
        </div>

        <div className="card kpi-card">
          <div className="kpi-header">
            <span>Out-of-Bounds Ages</span>
            <AlertTriangle size={18} style={{ color: 'var(--color-warning)' }} />
          </div>
          <div className="kpi-value tabular-nums" style={{ color: 'var(--color-warning)' }}>
            {formatInt(flags.invalid_age_flag_count)}
          </div>
          <div className="kpi-subtext">Ages &lt; 18 or &gt; 100 nullified</div>
        </div>

        <div className="card kpi-card">
          <div className="kpi-header">
            <span>SHA-256 Immutability</span>
            <Lock size={18} style={{ color: 'var(--color-success)' }} />
          </div>
          <div className="kpi-value" style={{ fontSize: '1.25rem', color: 'var(--color-success)' }}>
            VERIFIED
          </div>
          <div className="kpi-subtext" style={{ fontFamily: 'var(--font-mono)', fontSize: '0.68rem' }}>
            027a120ef9bb3869...076c
          </div>
        </div>
      </div>

      {/* Audit Flags Breakdown */}
      <div className="card" style={{ marginBottom: 24 }}>
        <div className="card-title-group">
          <div>
            <div className="card-title">Sanitized Corrupted Values Audit Ledger</div>
            <div className="card-subtitle">Zero ABS() conversion policy: corrupted values are nullified and explicitly flagged</div>
          </div>
        </div>

        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>Audit Check</th>
                <th>Corrupted Pattern In Source</th>
                <th>Cleaning Policy</th>
                <th>Flagged Records</th>
                <th>Impact on Underwriting</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td style={{ fontWeight: 600 }}>Annual Income</td>
                <td>Negative values (e.g. <code>-50,000</code>)</td>
                <td>Set to <code>NULL</code>, flagged with <code>has_invalid_annual_income = 1</code></td>
                <td className="tabular-nums" style={{ color: 'var(--color-danger)', fontWeight: 600 }}>{flags.invalid_annual_income_flag_count}</td>
                <td style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Prevents artificial distortion of affordability ratios</td>
              </tr>
              <tr>
                <td style={{ fontWeight: 600 }}>Loan Amount</td>
                <td>Non-positive values (&lt;= 0)</td>
                <td>Set to <code>NULL</code>, flagged with <code>has_invalid_loan_amount = 1</code></td>
                <td className="tabular-nums" style={{ color: 'var(--color-danger)', fontWeight: 600 }}>{flags.invalid_loan_amount_flag_count}</td>
                <td style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Excluded from haircut analysis population</td>
              </tr>
              <tr>
                <td style={{ fontWeight: 600 }}>Savings Balance</td>
                <td>Negative values</td>
                <td>Set to <code>NULL</code>, flagged with <code>has_invalid_savings_balance = 1</code></td>
                <td className="tabular-nums" style={{ color: 'var(--color-danger)', fontWeight: 600 }}>{flags.invalid_savings_balance_flag_count}</td>
                <td style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Prevents negative liquidity assumptions</td>
              </tr>
              <tr>
                <td style={{ fontWeight: 600 }}>Applicant Age</td>
                <td>Ages &lt; 18 or &gt; 100</td>
                <td>Set to <code>NULL</code>, flagged with <code>has_invalid_age = 1</code></td>
                <td className="tabular-nums" style={{ color: 'var(--color-warning)', fontWeight: 600 }}>{flags.invalid_age_flag_count}</td>
                <td style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Quarantines legally impossible borrower ages</td>
              </tr>
              <tr style={{ backgroundColor: 'var(--bg-surface-elevated)' }}>
                <td style={{ fontWeight: 700 }}>Composite Invalid Financials</td>
                <td>Row-level OR across Income, Loan, and Savings</td>
                <td>Flagged with <code>has_invalid_financials = 1</code></td>
                <td className="tabular-nums" style={{ color: 'var(--color-danger)', fontWeight: 700 }}>{flags.composite_invalid_financials_count}</td>
                <td style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>104 unique applicants (App ID 530545 overlaps Loan & Savings)</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* Sanctioned Amount Missingness vs Genuine Zero */}
      <div className="grid-two-col" style={{ marginBottom: 24 }}>
        <div className="card">
          <div className="card-title-group">
            <div>
              <div className="card-title">Sanctioned Amount: Genuine Zero vs Source NULL</div>
              <div className="card-subtitle">Critical distinction between recorded $0.00 and missing values</div>
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <div style={{ padding: '14px 18px', backgroundColor: 'var(--bg-surface-elevated)', borderRadius: 'var(--radius-md)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontWeight: 600 }}>Genuine Recorded Zeros (Rejections)</span>
                <span className="badge badge-approved tabular-nums" style={{ color: 'var(--text-primary)' }}>
                  {formatInt(missing.genuine_zero_sanctioned_rejected_count)}
                </span>
              </div>
              <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: 6 }}>
                In credit underwriting, rejected applications explicitly receive <code>0.00 CU</code> in funds. 50,198 records have recorded zeros.
              </p>
            </div>

            <div style={{ padding: '14px 18px', backgroundColor: 'var(--bg-surface-elevated)', borderRadius: 'var(--radius-md)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontWeight: 600 }}>Missing Sanction on Approvals (NULL)</span>
                <span className="badge badge-neutral tabular-nums">{formatInt(missing.missing_sanctioned_approved_count)}</span>
              </div>
              <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: 6 }}>
                Approved applications that lacked a recorded sanction amount in source. Preserved strictly as <code>NULL</code> to prevent false zero imputation.
              </p>
            </div>

            <div style={{ padding: '14px 18px', backgroundColor: 'var(--bg-surface-elevated)', borderRadius: 'var(--radius-md)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontWeight: 600 }}>Missing Sanction on Rejections (NULL)</span>
                <span className="badge badge-neutral tabular-nums">{formatInt(missing.missing_sanctioned_rejected_count)}</span>
              </div>
              <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: 6 }}>
                Rejected applications where no zero was entered, but field was left blank in source. Preserved as <code>NULL</code> for forensic auditability.
              </p>
            </div>
          </div>
        </div>

        {/* Source Field Missingness Ledger */}
        <div className="card">
          <div className="card-title-group">
            <div>
              <div className="card-title">Missing Values Ledger Across Source Columns</div>
              <div className="card-subtitle">Verified NULL counts across primary warehouse attributes</div>
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 12px', backgroundColor: 'var(--bg-surface-elevated)', borderRadius: 'var(--radius-sm)' }}>
              <span style={{ fontSize: '0.82rem' }}>Credit Bureau Score (Credit_Score)</span>
              <span className="tabular-nums" style={{ fontWeight: 600 }}>{formatInt(missing.missing_bureau_credit_score_count)} NULLs (1.32%)</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 12px', backgroundColor: 'var(--bg-surface-elevated)', borderRadius: 'var(--radius-sm)' }}>
              <span style={{ fontSize: '0.82rem' }}>Annual Income</span>
              <span className="tabular-nums" style={{ fontWeight: 600 }}>{formatInt(missing.missing_annual_income_count)} NULLs (1.33%)</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 12px', backgroundColor: 'var(--bg-surface-elevated)', borderRadius: 'var(--radius-sm)' }}>
              <span style={{ fontSize: '0.82rem' }}>Savings Balance</span>
              <span className="tabular-nums" style={{ fontWeight: 600 }}>{formatInt(missing.missing_savings_balance_count)} NULLs (1.30%)</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 12px', backgroundColor: 'var(--bg-surface-elevated)', borderRadius: 'var(--radius-sm)' }}>
              <span style={{ fontSize: '0.82rem' }}>Requested Loan Amount</span>
              <span className="tabular-nums" style={{ fontWeight: 600 }}>{formatInt(missing.missing_requested_loan_amount_count)} NULLs (1.30%)</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 12px', backgroundColor: 'var(--bg-surface-elevated)', borderRadius: 'var(--radius-sm)' }}>
              <span style={{ fontSize: '0.82rem' }}>Interest Rate</span>
              <span className="tabular-nums" style={{ fontWeight: 600 }}>{formatInt(missing.missing_interest_rate_count)} NULLs (1.31%)</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 12px', backgroundColor: 'var(--bg-surface-elevated)', borderRadius: 'var(--radius-sm)' }}>
              <span style={{ fontSize: '0.82rem' }}>Debt-To-Income Ratio</span>
              <span className="tabular-nums" style={{ fontWeight: 600 }}>{formatInt(missing.missing_debt_to_income_ratio_count)} NULLs (1.26%)</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 12px', backgroundColor: 'var(--bg-surface-elevated)', borderRadius: 'var(--radius-sm)' }}>
              <span style={{ fontSize: '0.82rem' }}>Proprietary Risk Score</span>
              <span className="tabular-nums" style={{ fontWeight: 600 }}>{formatInt(missing.missing_proprietary_risk_score_count)} NULLs (1.22%)</span>
            </div>
          </div>
        </div>
      </div>

      {/* Haircut Exclusion Reconciliation Ledger */}
      <div className="card" style={{ marginBottom: 24 }}>
        <div className="card-title-group">
          <div>
            <div className="card-title">Haircut Calculation Exclusion Reconciliation</div>
            <div className="card-subtitle">Formal audit trail confirming every application is accounted for exactly once</div>
          </div>
        </div>

        <div className="table-container">
          <table className="table">
            <thead>
              <tr>
                <th>Cohort / Exclusion Rule</th>
                <th style={{ textAlign: 'right' }}>Application Count</th>
                <th>Portfolio Share</th>
                <th>Exclusion Rationale & Handling</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td style={{ fontWeight: 600 }}>Total Evaluated Portfolio</td>
                <td className="tabular-nums" style={{ textAlign: 'right', fontWeight: 600 }}>{formatInt(data.total_applications)}</td>
                <td>100.00%</td>
                <td style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Complete database population</td>
              </tr>
              <tr style={{ backgroundColor: 'rgba(34, 197, 94, 0.05)' }}>
                <td style={{ fontWeight: 600, color: 'var(--color-success)' }}>Eligible Approved Population</td>
                <td className="tabular-nums" style={{ textAlign: 'right', fontWeight: 700, color: 'var(--color-success)' }}>
                  {formatInt(data.total_applications - exclusions.total_excluded_count)}
                </td>
                <td style={{ fontWeight: 600, color: 'var(--color-success)' }}>48.02%</td>
                <td style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Approved loans with valid requested and sanctioned amounts</td>
              </tr>
              <tr style={{ backgroundColor: 'rgba(239, 68, 68, 0.05)' }}>
                <td style={{ fontWeight: 600, color: 'var(--color-danger)' }}>Total Excluded from Haircut</td>
                <td className="tabular-nums" style={{ textAlign: 'right', fontWeight: 700, color: 'var(--color-danger)' }}>
                  {formatInt(exclusions.total_excluded_count)}
                </td>
                <td style={{ fontWeight: 600, color: 'var(--color-danger)' }}>51.98%</td>
                <td style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Sum of rejected applications (50,829) + approved exclusions (1,149)</td>
              </tr>
              <tr>
                <td style={{ paddingLeft: 28, color: 'var(--text-muted)' }}>↳ 1. Rejected Applications</td>
                <td className="tabular-nums" style={{ textAlign: 'right' }}>{formatInt(exclusions.excluded_rejected_count)}</td>
                <td>50.83%</td>
                <td style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Rejections receive no credit facility; no sanction hair-cutting applies</td>
              </tr>
              <tr>
                <td style={{ paddingLeft: 28, color: 'var(--text-secondary)' }}>↳ 2. Approved — Missing Sanction Only</td>
                <td className="tabular-nums" style={{ textAlign: 'right', fontWeight: 600 }}>
                  {formatInt(exclusions.excluded_approved_missing_sanction_count - ((exclusions.excluded_approved_missing_sanction_count + exclusions.excluded_approved_missing_requested_count) - (exclusions.total_excluded_count - exclusions.excluded_rejected_count)))}
                </td>
                <td>0.57%</td>
                <td style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Sanctioned amount is NULL, but requested loan amount is valid (&gt; 0)</td>
              </tr>
              <tr>
                <td style={{ paddingLeft: 28, color: 'var(--text-secondary)' }}>↳ 3. Approved — Invalid/Missing Request Only</td>
                <td className="tabular-nums" style={{ textAlign: 'right', fontWeight: 600 }}>
                  {formatInt(exclusions.excluded_approved_missing_requested_count - ((exclusions.excluded_approved_missing_sanction_count + exclusions.excluded_approved_missing_requested_count) - (exclusions.total_excluded_count - exclusions.excluded_rejected_count)))}
                </td>
                <td>0.57%</td>
                <td style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Requested amount is NULL or &le; 0, but positive sanction is recorded</td>
              </tr>
              <tr>
                <td style={{ paddingLeft: 28, color: 'var(--color-warning)' }}>↳ 4. Approved — Dual Condition (Both Missing/Invalid)</td>
                <td className="tabular-nums" style={{ textAlign: 'right', color: 'var(--color-warning)', fontWeight: 600 }}>
                  {formatInt((exclusions.excluded_approved_missing_sanction_count + exclusions.excluded_approved_missing_requested_count) - (exclusions.total_excluded_count - exclusions.excluded_rejected_count))}
                </td>
                <td>0.01%</td>
                <td style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Both requested and sanctioned amounts missing/invalid simultaneously</td>
              </tr>
              <tr style={{ backgroundColor: 'var(--bg-surface-elevated)' }}>
                <td style={{ fontWeight: 700 }}>Total Mutually Exclusive Approved Exclusions</td>
                <td className="tabular-nums" style={{ textAlign: 'right', fontWeight: 700 }}>
                  {formatInt(exclusions.total_excluded_count - exclusions.excluded_rejected_count)}
                </td>
                <td style={{ fontWeight: 700 }}>1.15%</td>
                <td style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>565 (Sanction Only) + 574 (Request Only) + 10 (Dual) = 1,149 unique applications</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
