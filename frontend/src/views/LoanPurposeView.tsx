import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import type { LoanPurposeItem } from '../types/api';
import { formatCU, formatPct, formatInt } from '../utils/formatters';
import { ArrowUpDown, AlertTriangle, PieChart, Sparkles } from 'lucide-react';

export const LoanPurposeView: React.FC = () => {
  const [purposes, setPurposes] = useState<LoanPurposeItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [sortField, setSortField] = useState<keyof LoanPurposeItem>('total_applications');
  const [sortAsc, setSortAsc] = useState<boolean>(false);

  useEffect(() => {
    async function loadPurposes() {
      try {
        setLoading(true);
        setError(null);
        const data = await api.getLoanPurposes();
        setPurposes(data);
      } catch (err: any) {
        setError(err.message || 'Failed to load loan purpose metrics.');
      } finally {
        setLoading(false);
      }
    }
    loadPurposes();
  }, []);

  const handleSort = (field: keyof LoanPurposeItem) => {
    if (sortField === field) {
      setSortAsc(!sortAsc);
    } else {
      setSortField(field);
      setSortAsc(false);
    }
  };

  const sortedPurposes = [...purposes].sort((a, b) => {
    const valA = a[sortField];
    const valB = b[sortField];
    if (typeof valA === 'string' && typeof valB === 'string') {
      return sortAsc ? valA.localeCompare(valB) : valB.localeCompare(valA);
    }
    const numA = Number(valA);
    const numB = Number(valB);
    return sortAsc ? numA - numB : numB - numA;
  });

  if (loading) {
    return (
      <div className="view-body">
        <div className="card" style={{ textAlign: 'center', padding: '60px 20px' }}>
          <p style={{ color: 'var(--text-secondary)' }}>Loading verified loan purpose analytics...</p>
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
            <strong>Unable to Load Loan Purpose Analysis</strong>
            <p>{error}</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="view-body">
      {/* Purpose Quick Overview Cards (Top 4 Volume) */}
      <div className="grid-kpis">
        {purposes.slice(0, 4).map((p) => (
          <div key={p.purpose_id} className="card kpi-card">
            <div className="kpi-header">
              <span>{p.purpose_name}</span>
              <PieChart size={16} style={{ color: 'var(--brand-cyan)' }} />
            </div>
            <div className="kpi-value tabular-nums">{formatInt(p.total_applications)}</div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', marginTop: 8 }}>
              <span style={{ color: 'var(--text-muted)' }}>Approval Rate:</span>
              <span className="badge badge-approved tabular-nums">{formatPct(p.approval_rate_pct)}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', marginTop: 6 }}>
              <span style={{ color: 'var(--text-muted)' }}>Haircut Rate:</span>
              <span className="badge badge-neutral tabular-nums" style={{ color: 'var(--color-warning)' }}>
                {formatPct(p.aggregate_haircut_pct)}
              </span>
            </div>
          </div>
        ))}
      </div>

      {/* Purpose Haircut Comparison Chart / Bars */}
      <div className="card" style={{ marginBottom: 24 }}>
        <div className="card-title-group">
          <div>
            <div className="card-title">Haircut Rate Comparison Across All 8 Categories</div>
            <div className="card-subtitle">Showing underwriting haircut rate (requested vs sanctioned difference for eligible approved loans)</div>
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          {[...purposes].sort((a, b) => b.aggregate_haircut_pct - a.aggregate_haircut_pct).map((p) => (
            <div key={p.purpose_id}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 5 }}>
                <span style={{ fontWeight: 600, fontSize: '0.86rem' }}>{p.purpose_name}</span>
                <div style={{ fontSize: '0.82rem' }} className="tabular-nums">
                  <span style={{ color: 'var(--color-warning)', fontWeight: 700 }}>{p.aggregate_haircut_pct.toFixed(2)}% Haircut</span>
                  <span style={{ color: 'var(--text-muted)', marginLeft: 8 }}>({formatCU(p.haircut_total_cu, true)} reduction)</span>
                </div>
              </div>
              <div className="progress-bar-bg" style={{ height: 10 }}>
                <div 
                  className="progress-bar-fill" 
                  style={{ 
                    width: `${(p.aggregate_haircut_pct / 30) * 100}%`, 
                    backgroundColor: p.aggregate_haircut_pct > 24 ? 'var(--color-danger)' : 'var(--color-warning)' 
                  }} 
                />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Complete Sortable Purpose Table */}
      <div className="card" style={{ marginBottom: 24 }}>
        <div className="card-title-group">
          <div>
            <div className="card-title">Loan Purpose Underwriting & Haircut Ledger</div>
            <div className="card-subtitle">Reconciles all 8 verified source categories to portfolio totals</div>
          </div>
        </div>

        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th style={{ cursor: 'pointer' }} onClick={() => handleSort('purpose_name')}>
                  Purpose Name <ArrowUpDown size={12} style={{ display: 'inline', marginLeft: 4 }} />
                </th>
                <th style={{ cursor: 'pointer' }} onClick={() => handleSort('total_applications')}>
                  Total Apps <ArrowUpDown size={12} style={{ display: 'inline', marginLeft: 4 }} />
                </th>
                <th style={{ cursor: 'pointer' }} onClick={() => handleSort('approved_applications')}>
                  Approved <ArrowUpDown size={12} style={{ display: 'inline', marginLeft: 4 }} />
                </th>
                <th style={{ cursor: 'pointer' }} onClick={() => handleSort('approval_rate_pct')}>
                  Appr Rate <ArrowUpDown size={12} style={{ display: 'inline', marginLeft: 4 }} />
                </th>
                <th style={{ cursor: 'pointer' }} onClick={() => handleSort('haircut_eligible_count')}>
                  Eligible Count <ArrowUpDown size={12} style={{ display: 'inline', marginLeft: 4 }} />
                </th>
                <th style={{ cursor: 'pointer' }} onClick={() => handleSort('haircut_eligible_requested_cu')}>
                  Eligible Requested <ArrowUpDown size={12} style={{ display: 'inline', marginLeft: 4 }} />
                </th>
                <th style={{ cursor: 'pointer' }} onClick={() => handleSort('haircut_eligible_sanctioned_cu')}>
                  Eligible Sanctioned <ArrowUpDown size={12} style={{ display: 'inline', marginLeft: 4 }} />
                </th>
                <th style={{ cursor: 'pointer' }} onClick={() => handleSort('haircut_total_cu')}>
                  Haircut (CU) <ArrowUpDown size={12} style={{ display: 'inline', marginLeft: 4 }} />
                </th>
                <th style={{ cursor: 'pointer' }} onClick={() => handleSort('aggregate_haircut_pct')}>
                  Haircut % <ArrowUpDown size={12} style={{ display: 'inline', marginLeft: 4 }} />
                </th>
              </tr>
            </thead>
            <tbody>
              {sortedPurposes.map((p) => (
                <tr key={p.purpose_id}>
                  <td style={{ fontWeight: 600 }}>{p.purpose_name}</td>
                  <td className="tabular-nums">{formatInt(p.total_applications)}</td>
                  <td className="tabular-nums" style={{ color: 'var(--color-success)' }}>{formatInt(p.approved_applications)}</td>
                  <td className="tabular-nums">
                    <span className="badge badge-approved">{formatPct(p.approval_rate_pct)}</span>
                  </td>
                  <td className="tabular-nums">{formatInt(p.haircut_eligible_count)}</td>
                  <td className="tabular-nums">{formatCU(p.haircut_eligible_requested_cu, true)}</td>
                  <td className="tabular-nums" style={{ color: 'var(--color-success)' }}>{formatCU(p.haircut_eligible_sanctioned_cu, true)}</td>
                  <td className="tabular-nums" style={{ color: 'var(--color-warning)' }}>{formatCU(p.haircut_total_cu, true)}</td>
                  <td className="tabular-nums">
                    <span className="badge badge-neutral" style={{ color: 'var(--color-warning)', fontWeight: 700 }}>
                      {formatPct(p.aggregate_haircut_pct)}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr>
                <td>Total (8 Categories)</td>
                <td className="tabular-nums">{formatInt(purposes.reduce((s, p) => s + p.total_applications, 0))}</td>
                <td className="tabular-nums" style={{ color: 'var(--color-success)' }}>{formatInt(purposes.reduce((s, p) => s + p.approved_applications, 0))}</td>
                <td className="tabular-nums">49.17%</td>
                <td className="tabular-nums">{formatInt(purposes.reduce((s, p) => s + p.haircut_eligible_count, 0))}</td>
                <td className="tabular-nums">{formatCU(purposes.reduce((s, p) => s + p.haircut_eligible_requested_cu, 0), true)}</td>
                <td className="tabular-nums" style={{ color: 'var(--color-success)' }}>{formatCU(purposes.reduce((s, p) => s + p.haircut_eligible_sanctioned_cu, 0), true)}</td>
                <td className="tabular-nums" style={{ color: 'var(--color-warning)' }}>{formatCU(purposes.reduce((s, p) => s + p.haircut_total_cu, 0), true)}</td>
                <td className="tabular-nums" style={{ color: 'var(--color-warning)', fontWeight: 700 }}>20.32% (Aggregate)</td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>

      {/* Purpose Findings */}
      <div className="insights-card">
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, color: 'var(--brand-cyan)' }}>
          <Sparkles size={18} />
          <h3 style={{ fontSize: '0.95rem', fontWeight: 700 }}>Key Loan Purpose Observations</h3>
        </div>
        <div className="insights-list">
          <div className="insight-item">
            <span>•</span>
            <div>
              <strong>Car Loans Highest Approval & Highest Haircut:</strong> Car loan applications exhibited the highest approval rate (<span className="tabular-nums">61.55%</span>) 
              among all categories, but also suffered the steepest aggregate haircut (<span className="tabular-nums">26.29%</span>), with sanctioned principal cut by over a quarter.
            </div>
          </div>
          <div className="insight-item">
            <span>•</span>
            <div>
              <strong>Vehicle Loans Lowest Approval:</strong> Applications filed under the distinct <strong>Vehicle</strong> category experienced the lowest approval rate 
              at <span className="tabular-nums">45.54%</span> (4,593 approvals out of 10,086), contrasting sharply with the narrower <strong>Car</strong> category.
            </div>
          </div>
          <div className="insight-item">
            <span>•</span>
            <div>
              <strong>Major Concentration in Debt Consolidation & Business:</strong> Together, <strong>Debt Consolidation</strong> (14,236) and <strong>Business</strong> (14,269) 
              account for <span className="tabular-nums">28.5%</span> of total origination demand and <span className="tabular-nums">391.18M CU</span> in total underwriting reductions.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
