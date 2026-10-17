import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import type { ChannelPerformanceItem } from '../types/api';
import { formatCU, formatPct, formatInt } from '../utils/formatters';
import { ArrowUpDown, AlertTriangle, Globe, Building2, Smartphone, UserCheck, TrendingUp, Sparkles } from 'lucide-react';

export const ChannelView: React.FC = () => {
  const [channels, setChannels] = useState<ChannelPerformanceItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [sortField, setSortField] = useState<keyof ChannelPerformanceItem>('total_applications');
  const [sortAsc, setSortAsc] = useState<boolean>(false);

  useEffect(() => {
    async function loadChannels() {
      try {
        setLoading(true);
        setError(null);
        const data = await api.getChannels();
        setChannels(data);
      } catch (err: any) {
        setError(err.message || 'Failed to load channel performance.');
      } finally {
        setLoading(false);
      }
    }
    loadChannels();
  }, []);

  const handleSort = (field: keyof ChannelPerformanceItem) => {
    if (sortField === field) {
      setSortAsc(!sortAsc);
    } else {
      setSortField(field);
      setSortAsc(false);
    }
  };

  const sortedChannels = [...channels].sort((a, b) => {
    const valA = a[sortField];
    const valB = b[sortField];
    if (typeof valA === 'string' && typeof valB === 'string') {
      return sortAsc ? valA.localeCompare(valB) : valB.localeCompare(valA);
    }
    const numA = Number(valA);
    const numB = Number(valB);
    return sortAsc ? numA - numB : numB - numA;
  });

  const getChannelIcon = (name: string) => {
    switch (name) {
      case 'Online': return <Globe size={18} style={{ color: 'var(--brand-cyan)' }} />;
      case 'Branch': return <Building2 size={18} style={{ color: 'var(--brand-blue)' }} />;
      case 'Mobile App': return <Smartphone size={18} style={{ color: 'var(--color-success)' }} />;
      case 'Agent': return <UserCheck size={18} style={{ color: 'var(--brand-purple)' }} />;
      default: return <TrendingUp size={18} />;
    }
  };

  if (loading) {
    return (
      <div className="view-body">
        <div className="card" style={{ textAlign: 'center', padding: '60px 20px' }}>
          <p style={{ color: 'var(--text-secondary)' }}>Loading acquisition channel metrics...</p>
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
            <strong>Unable to Load Channel Performance</strong>
            <p>{error}</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="view-body">
      {/* Channel Cards */}
      <div className="grid-kpis" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))' }}>
        {channels.map((ch) => (
          <div key={ch.channel_id} className="card kpi-card">
            <div className="kpi-header">
              <span>{ch.channel_name}</span>
              {getChannelIcon(ch.channel_name)}
            </div>
            <div className="kpi-value tabular-nums">{formatInt(ch.total_applications)}</div>
            <div style={{ marginTop: 8 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.78rem', marginBottom: 4 }}>
                <span style={{ color: 'var(--text-muted)' }}>Approval Rate:</span>
                <span className="badge badge-approved tabular-nums">{formatPct(ch.approval_rate_pct)}</span>
              </div>
              <div className="progress-bar-bg" style={{ height: 6 }}>
                <div 
                  className="progress-bar-fill" 
                  style={{ width: `${ch.approval_rate_pct}%`, backgroundColor: 'var(--color-success)' }} 
                />
              </div>
            </div>
            <div style={{ marginTop: 12, paddingTop: 10, borderTop: '1px solid var(--border-subtle)', display: 'flex', justifyContent: 'space-between', fontSize: '0.78rem' }}>
              <span style={{ color: 'var(--text-muted)' }}>Sanctioned:</span>
              <span className="tabular-nums" style={{ color: 'var(--text-primary)', fontWeight: 600 }}>{formatCU(ch.total_sanctioned_cu, true)}</span>
            </div>
          </div>
        ))}
      </div>

      {/* Comparative Visualizer */}
      <div className="card" style={{ marginBottom: 24 }}>
        <div className="card-title-group">
          <div>
            <div className="card-title">Channel Conversion & Volume Comparison</div>
            <div className="card-subtitle">Visualizing approved vs rejected loans across each origination source</div>
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
          {channels.map((ch) => {
            const apprPct = ch.approval_rate_pct;
            const rejcPct = 100.0 - apprPct;
            return (
              <div key={ch.channel_id}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    {getChannelIcon(ch.channel_name)}
                    <span style={{ fontWeight: 600, fontSize: '0.9rem' }}>{ch.channel_name}</span>
                    <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                      ({formatInt(ch.total_applications)} originations, {((ch.total_applications / 100000) * 100).toFixed(1)}% share)
                    </span>
                  </div>
                  <div style={{ fontSize: '0.84rem' }} className="tabular-nums">
                    <span style={{ color: 'var(--color-success)', fontWeight: 600 }}>{formatInt(ch.approved_applications)} Appr</span>
                    {' / '}
                    <span style={{ color: 'var(--color-danger)', fontWeight: 600 }}>{formatInt(ch.rejected_applications)} Rej</span>
                  </div>
                </div>

                <div style={{ display: 'flex', width: '100%', height: 16, borderRadius: 'var(--radius-sm)', overflow: 'hidden' }}>
                  <div 
                    style={{ 
                      width: `${apprPct}%`, 
                      backgroundColor: 'var(--color-success)', 
                      display: 'flex', 
                      alignItems: 'center', 
                      justifyContent: 'center',
                      fontSize: '0.7rem',
                      color: '#000',
                      fontWeight: 700 
                    }}
                  >
                    {apprPct.toFixed(1)}%
                  </div>
                  <div 
                    style={{ 
                      width: `${rejcPct}%`, 
                      backgroundColor: 'var(--color-danger)', 
                      display: 'flex', 
                      alignItems: 'center', 
                      justifyContent: 'center',
                      fontSize: '0.7rem',
                      color: '#fff',
                      fontWeight: 700 
                    }}
                  >
                    {rejcPct.toFixed(1)}%
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Sortable Table */}
      <div className="card" style={{ marginBottom: 24 }}>
        <div className="card-title-group">
          <div>
            <div className="card-title">Conformed Channel Performance Table</div>
            <div className="card-subtitle">Click table headers to toggle ascending or descending sorting</div>
          </div>
        </div>

        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th style={{ cursor: 'pointer' }} onClick={() => handleSort('channel_name')}>
                  Channel Name <ArrowUpDown size={12} style={{ display: 'inline', marginLeft: 4 }} />
                </th>
                <th style={{ cursor: 'pointer' }} onClick={() => handleSort('total_applications')}>
                  Total Applications <ArrowUpDown size={12} style={{ display: 'inline', marginLeft: 4 }} />
                </th>
                <th style={{ cursor: 'pointer' }} onClick={() => handleSort('approved_applications')}>
                  Approved <ArrowUpDown size={12} style={{ display: 'inline', marginLeft: 4 }} />
                </th>
                <th style={{ cursor: 'pointer' }} onClick={() => handleSort('rejected_applications')}>
                  Rejected <ArrowUpDown size={12} style={{ display: 'inline', marginLeft: 4 }} />
                </th>
                <th style={{ cursor: 'pointer' }} onClick={() => handleSort('approval_rate_pct')}>
                  Approval Rate <ArrowUpDown size={12} style={{ display: 'inline', marginLeft: 4 }} />
                </th>
                <th style={{ cursor: 'pointer' }} onClick={() => handleSort('total_requested_cu')}>
                  Requested Principal <ArrowUpDown size={12} style={{ display: 'inline', marginLeft: 4 }} />
                </th>
                <th style={{ cursor: 'pointer' }} onClick={() => handleSort('total_sanctioned_cu')}>
                  Sanctioned Principal <ArrowUpDown size={12} style={{ display: 'inline', marginLeft: 4 }} />
                </th>
              </tr>
            </thead>
            <tbody>
              {sortedChannels.map((ch) => (
                <tr key={ch.channel_id}>
                  <td style={{ fontWeight: 600 }}>{ch.channel_name}</td>
                  <td className="tabular-nums">{formatInt(ch.total_applications)}</td>
                  <td className="tabular-nums" style={{ color: 'var(--color-success)' }}>{formatInt(ch.approved_applications)}</td>
                  <td className="tabular-nums" style={{ color: 'var(--color-danger)' }}>{formatInt(ch.rejected_applications)}</td>
                  <td className="tabular-nums">
                    <span className="badge badge-approved">{formatPct(ch.approval_rate_pct)}</span>
                  </td>
                  <td className="tabular-nums">{formatCU(ch.total_requested_cu)}</td>
                  <td className="tabular-nums" style={{ color: 'var(--color-success)' }}>{formatCU(ch.total_sanctioned_cu)}</td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr>
                <td>Portfolio Total</td>
                <td className="tabular-nums">{formatInt(channels.reduce((s, c) => s + c.total_applications, 0))}</td>
                <td className="tabular-nums" style={{ color: 'var(--color-success)' }}>{formatInt(channels.reduce((s, c) => s + c.approved_applications, 0))}</td>
                <td className="tabular-nums" style={{ color: 'var(--color-danger)' }}>{formatInt(channels.reduce((s, c) => s + c.rejected_applications, 0))}</td>
                <td className="tabular-nums">49.17% (Aggregate)</td>
                <td className="tabular-nums">{formatCU(channels.reduce((s, c) => s + c.total_requested_cu, 0))}</td>
                <td className="tabular-nums" style={{ color: 'var(--color-success)' }}>{formatCU(channels.reduce((s, c) => s + c.total_sanctioned_cu, 0))}</td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>

      {/* Descriptive Findings */}
      <div className="insights-card">
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, color: 'var(--brand-cyan)' }}>
          <Sparkles size={18} />
          <h3 style={{ fontSize: '0.95rem', fontWeight: 700 }}>Descriptive Channel Insights</h3>
        </div>
        <div className="insights-list">
          <div className="insight-item">
            <span>•</span>
            <div>
              <strong>Online Origination Dominance:</strong> With 30,039 applications, the Online channel captures <span className="tabular-nums">30.04%</span> of total 
              portfolio flow and demonstrates the highest approval rate at <span className="tabular-nums">50.48%</span>.
            </div>
          </div>
          <div className="insight-item">
            <span>•</span>
            <div>
              <strong>Agent Channel Underperformance:</strong> The Agent channel originated 20,422 applications (<span className="tabular-nums">20.42%</span> of volume) 
              with an approval rate of <span className="tabular-nums">47.38%</span>, trailing the Online channel by <span className="tabular-nums">3.10 percentage points</span>.
            </div>
          </div>
          <div className="insight-item">
            <span>•</span>
            <div>
              <strong>Capital Sanction Spread:</strong> Total capital sanctioned via the Online channel (<span className="tabular-nums">1.62B CU</span>) exceeds 
              the Agent channel (<span className="tabular-nums">1.11B CU</span>) by <span className="tabular-nums">511.47M CU</span> (45.9% higher).
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
