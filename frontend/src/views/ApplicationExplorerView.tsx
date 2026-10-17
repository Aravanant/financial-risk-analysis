import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import type { ApplicationSummary, PaginatedApplicationsResponse } from '../types/api';
import { formatCU, formatPct, formatInt } from '../utils/formatters';
import { 
  Search, 
  ChevronLeft, 
  ChevronRight, 
  X, 
  AlertTriangle, 
  Eye, 
  RotateCcw
} from 'lucide-react';

export const ApplicationExplorerView: React.FC = () => {
  const [data, setData] = useState<PaginatedApplicationsResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Filters state
  const [page, setPage] = useState<number>(1);
  const [pageSize, setPageSize] = useState<number>(25);
  const [decision, setDecision] = useState<string>('');
  const [channel, setChannel] = useState<string>('');
  const [purpose, setPurpose] = useState<string>('');
  const [tier, setTier] = useState<string>('');
  const [hasInvalidFinancials, setHasInvalidFinancials] = useState<string>('');
  const [searchId, setSearchId] = useState<string>('');
  const [sortBy, setSortBy] = useState<string>('application_id');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc');

  // Single application detail drawer state
  const [selectedApp, setSelectedApp] = useState<ApplicationSummary | null>(null);
  const [drawerLoading, setDrawerLoading] = useState<boolean>(false);
  const [searchError, setSearchError] = useState<string | null>(null);

  const loadApplications = async (targetPage = page) => {
    try {
      setLoading(true);
      setError(null);
      setSearchError(null);

      // If user typed a direct application ID in search, fetch that directly
      const trimmedSearch = searchId.trim();
      if (trimmedSearch && !isNaN(Number(trimmedSearch))) {
        try {
          const single = await api.getApplicationById(Number(trimmedSearch));
          setSelectedApp(single);
          setData({
            total_items: 1,
            page: 1,
            page_size: pageSize,
            total_pages: 1,
            items: [single]
          });
          setLoading(false);
          return;
        } catch {
          setSearchError(`Application ID ${trimmedSearch} not found.`);
        }
      }

      const res = await api.getApplications({
        page: targetPage,
        page_size: pageSize,
        decision: (decision || undefined) as any,
        channel: channel || undefined,
        loan_purpose: purpose || undefined,
        risk_tier: tier || undefined,
        has_invalid_financials: hasInvalidFinancials !== '' ? Number(hasInvalidFinancials) : undefined,
        sort_by: sortBy,
        sort_order: sortOrder
      });

      setData(res);
      setPage(res.page);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch application records.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadApplications(1);
  }, [decision, channel, purpose, tier, hasInvalidFinancials, pageSize, sortBy, sortOrder]);

  const handlePageChange = (newPage: number) => {
    if (newPage >= 1 && data && newPage <= data.total_pages) {
      setPage(newPage);
      loadApplications(newPage);
    }
  };

  const resetFilters = () => {
    setDecision('');
    setChannel('');
    setPurpose('');
    setTier('');
    setHasInvalidFinancials('');
    setSearchId('');
    setSortBy('application_id');
    setSortOrder('asc');
    setPage(1);
  };

  const handleSortToggle = (col: string) => {
    if (sortBy === col) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(col);
      setSortOrder('asc');
    }
  };

  const openDetail = async (id: number) => {
    try {
      setDrawerLoading(true);
      const app = await api.getApplicationById(id);
      setSelectedApp(app);
    } catch {
      alert(`Could not load details for application ${id}`);
    } finally {
      setDrawerLoading(false);
    }
  };

  return (
    <div className="view-body">
      {/* Search & Filter Bar */}
      <div className="filter-bar">
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flex: '1 1 240px' }}>
          <Search size={16} style={{ color: 'var(--text-muted)' }} />
          <input 
            type="text"
            className="filter-input"
            style={{ width: '100%' }}
            placeholder="Search Application ID (e.g. 500001)..."
            value={searchId}
            onChange={(e) => setSearchId(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') loadApplications(1); }}
          />
        </div>

        <select 
          className="filter-select"
          value={decision}
          onChange={(e) => setDecision(e.target.value)}
        >
          <option value="">All Decisions</option>
          <option value="Approved">Approved Only</option>
          <option value="Rejected">Rejected Only</option>
        </select>

        <select 
          className="filter-select"
          value={channel}
          onChange={(e) => setChannel(e.target.value)}
        >
          <option value="">All Channels</option>
          <option value="Online">Online</option>
          <option value="Branch">Branch</option>
          <option value="Mobile App">Mobile App</option>
          <option value="Agent">Agent</option>
        </select>

        <select 
          className="filter-select"
          value={purpose}
          onChange={(e) => setPurpose(e.target.value)}
        >
          <option value="">All Purposes (8)</option>
          <option value="Business">Business</option>
          <option value="Car">Car</option>
          <option value="Debt Consolidation">Debt Consolidation</option>
          <option value="Education">Education</option>
          <option value="Home">Home</option>
          <option value="Medical">Medical</option>
          <option value="Personal">Personal</option>
          <option value="Vehicle">Vehicle</option>
        </select>

        <select 
          className="filter-select"
          value={tier}
          onChange={(e) => setTier(e.target.value)}
        >
          <option value="">All Risk Tiers</option>
          <option value="Low">Low Risk</option>
          <option value="Medium">Medium Risk</option>
          <option value="High">High Risk</option>
        </select>

        <select 
          className="filter-select"
          value={hasInvalidFinancials}
          onChange={(e) => setHasInvalidFinancials(e.target.value)}
        >
          <option value="">All Financial Flags</option>
          <option value="1">Corrupted / Flagged Only (104)</option>
          <option value="0">Clean Financials Only</option>
        </select>

        <select 
          className="filter-select"
          value={pageSize}
          onChange={(e) => setPageSize(Number(e.target.value))}
        >
          <option value="25">25 / page</option>
          <option value="50">50 / page</option>
          <option value="100">100 / page</option>
        </select>

        <button 
          className="btn btn-secondary" 
          onClick={() => loadApplications(1)}
          title="Apply search query"
        >
          Search
        </button>

        <button 
          className="btn btn-secondary" 
          onClick={resetFilters}
          title="Reset all filters"
        >
          <RotateCcw size={14} />
          Reset
        </button>
      </div>

      {searchError && (
        <div className="notice-box notice-warning" style={{ marginBottom: 16 }}>
          <AlertTriangle size={18} />
          <span>{searchError} Showing filtered portfolio applications instead.</span>
        </div>
      )}

      {error && (
        <div className="notice-box notice-warning">
          <AlertTriangle size={20} />
          <div>
            <strong>Error Loading Application Records</strong>
            <p>{error}</p>
          </div>
        </div>
      )}

      {/* Main Table Card */}
      <div className="card" style={{ marginBottom: 24 }}>
        <div className="card-title-group">
          <div>
            <div className="card-title">Loan Applications Explorer</div>
            <div className="card-subtitle">
              {data ? (
                <>Showing <strong className="tabular-nums">{data.items.length}</strong> of <strong className="tabular-nums">{formatInt(data.total_items)}</strong> matching records (Page <span className="tabular-nums">{data.page}</span> of <span className="tabular-nums">{data.total_pages}</span>)</>
              ) : 'Loading...'}
            </div>
          </div>
        </div>

        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th style={{ cursor: 'pointer' }} onClick={() => handleSortToggle('application_id')}>
                  App ID {sortBy === 'application_id' && (sortOrder === 'asc' ? '↑' : '↓')}
                </th>
                <th>Decision</th>
                <th style={{ cursor: 'pointer' }} onClick={() => handleSortToggle('requested_loan_amount')}>
                  Requested (CU) {sortBy === 'requested_loan_amount' && (sortOrder === 'asc' ? '↑' : '↓')}
                </th>
                <th style={{ cursor: 'pointer' }} onClick={() => handleSortToggle('sanctioned_approved_amount')}>
                  Sanctioned (CU) {sortBy === 'sanctioned_approved_amount' && (sortOrder === 'asc' ? '↑' : '↓')}
                </th>
                <th>Channel</th>
                <th>Purpose</th>
                <th>Risk Tier</th>
                <th style={{ cursor: 'pointer' }} onClick={() => handleSortToggle('bureau_credit_score')}>
                  Bureau Score {sortBy === 'bureau_credit_score' && (sortOrder === 'asc' ? '↑' : '↓')}
                </th>
                <th style={{ cursor: 'pointer' }} onClick={() => handleSortToggle('proprietary_risk_score')}>
                  Risk Score {sortBy === 'proprietary_risk_score' && (sortOrder === 'asc' ? '↑' : '↓')}
                </th>
                <th>Flags</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={11} style={{ textAlign: 'center', padding: '40px' }}>
                    Loading verified loan application records...
                  </td>
                </tr>
              ) : data && data.items.length > 0 ? (
                data.items.map((app) => (
                  <tr key={app.application_id}>
                    <td className="tabular-nums" style={{ fontWeight: 600 }}>{app.application_id}</td>
                    <td>
                      <span className={`badge ${app.underwriting_decision === 'Approved' ? 'badge-approved' : 'badge-rejected'}`}>
                        {app.underwriting_decision}
                      </span>
                    </td>
                    <td className="tabular-nums">
                      {app.requested_loan_amount !== null ? formatCU(app.requested_loan_amount) : <span className="null-badge">NULL</span>}
                    </td>
                    <td className="tabular-nums">
                      {app.sanctioned_approved_amount !== null ? (
                        <span style={{ color: app.is_approved ? 'var(--color-success)' : 'inherit', fontWeight: app.is_approved ? 600 : 400 }}>
                          {formatCU(app.sanctioned_approved_amount)}
                        </span>
                      ) : (
                        <span className="null-badge">NULL</span>
                      )}
                    </td>
                    <td>{app.channel_name}</td>
                    <td>{app.purpose_name}</td>
                    <td>
                      <span className={`badge badge-tier-${(app.risk_tier || 'medium').toLowerCase()}`}>
                        {app.risk_tier}
                      </span>
                    </td>
                    <td className="tabular-nums">
                      {app.bureau_credit_score !== null ? app.bureau_credit_score : <span className="null-badge">NULL</span>}
                    </td>
                    <td className="tabular-nums">
                      {app.proprietary_risk_score !== null ? app.proprietary_risk_score.toFixed(1) : <span className="null-badge">NULL</span>}
                    </td>
                    <td>
                      {app.has_invalid_financials === 1 ? (
                        <span className="badge badge-flag" title="Corrupted negative balance sanitized">Invalid Fin</span>
                      ) : app.has_missing_sanctioned_amount === 1 ? (
                        <span className="badge badge-neutral" title="Missing sanctioned amount in source">Missing Sanc</span>
                      ) : (
                        <span style={{ color: 'var(--text-muted)' }}>—</span>
                      )}
                    </td>
                    <td>
                      <button 
                        className="btn btn-secondary" 
                        style={{ padding: '4px 10px', fontSize: '0.78rem' }}
                        onClick={() => openDetail(app.application_id)}
                      >
                        <Eye size={12} />
                        View
                      </button>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={11} style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>
                    No loan applications match the specified filter criteria.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination Controls */}
        {data && data.total_pages > 1 && (
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 18, paddingTop: 14, borderTop: '1px solid var(--border-subtle)' }}>
            <span style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
              Page <strong className="tabular-nums">{data.page}</strong> of <strong className="tabular-nums">{data.total_pages}</strong>
            </span>
            <div style={{ display: 'flex', gap: 8 }}>
              <button 
                className="btn btn-secondary"
                disabled={page <= 1 || loading}
                onClick={() => handlePageChange(page - 1)}
              >
                <ChevronLeft size={16} />
                Previous
              </button>
              <button 
                className="btn btn-secondary"
                disabled={page >= data.total_pages || loading}
                onClick={() => handlePageChange(page + 1)}
              >
                Next
                <ChevronRight size={16} />
              </button>
            </div>
          </div>
        )}
      </div>

      {drawerLoading && (
        <div style={{ position: 'fixed', top: 20, right: 24, zIndex: 100, backgroundColor: 'var(--bg-surface-elevated)', border: '1px solid var(--brand-cyan)', padding: '8px 16px', borderRadius: 'var(--radius-md)', fontSize: '0.85rem', color: 'var(--brand-cyan)' }}>
          Loading application detail...
        </div>
      )}

      {/* Application Detail Drawer */}
      {selectedApp && (
        <div className="drawer-backdrop" onClick={() => setSelectedApp(null)}>
          <div className="drawer-panel" onClick={(e) => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', paddingBottom: 16, borderBottom: '1px solid var(--border-subtle)' }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <h2 style={{ fontSize: '1.25rem', fontWeight: 700 }}>Application #{selectedApp.application_id}</h2>
                  <span className={`badge ${selectedApp.underwriting_decision === 'Approved' ? 'badge-approved' : 'badge-rejected'}`}>
                    {selectedApp.underwriting_decision}
                  </span>
                </div>
                <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: 4 }}>
                  Source File Line Order: Ordinal #{selectedApp.source_row_ordinal}
                </div>
              </div>
              <button 
                className="btn btn-secondary" 
                style={{ padding: '6px' }}
                onClick={() => setSelectedApp(null)}
              >
                <X size={18} />
              </button>
            </div>

            {/* Section 1: Underwriting Decision & Capital */}
            <div>
              <div className="detail-section-title">Underwriting Decision & Principal</div>
              <div className="detail-grid">
                <div>
                  <div className="detail-label">Decision:</div>
                  <div className="detail-value">{selectedApp.underwriting_decision} (is_approved: {selectedApp.is_approved})</div>
                </div>
                <div>
                  <div className="detail-label">Sanctioned Amount:</div>
                  <div className="detail-value tabular-nums" style={{ color: selectedApp.is_approved ? 'var(--color-success)' : 'inherit', fontWeight: 700 }}>
                    {selectedApp.sanctioned_approved_amount !== null ? formatCU(selectedApp.sanctioned_approved_amount) : <span className="null-badge">NULL (Missing)</span>}
                  </div>
                </div>
                <div>
                  <div className="detail-label">Requested Loan Amount:</div>
                  <div className="detail-value tabular-nums">{formatCU(selectedApp.requested_loan_amount)}</div>
                </div>
                <div>
                  <div className="detail-label">Requested Tenure:</div>
                  <div className="detail-value tabular-nums">{selectedApp.requested_term_months !== null ? `${selectedApp.requested_term_months} Months` : <span className="null-badge">NULL</span>}</div>
                </div>
                <div>
                  <div className="detail-label">Interest Rate:</div>
                  <div className="detail-value tabular-nums">{formatPct(selectedApp.interest_rate)}</div>
                </div>
                <div>
                  <div className="detail-label">Debt-To-Income (DTI):</div>
                  <div className="detail-value tabular-nums">{formatPct(selectedApp.debt_to_income_ratio)}</div>
                </div>
              </div>
            </div>

            {/* Section 2: Borrower Demographics & Socio-Economics */}
            <div>
              <div className="detail-section-title">Borrower Profile & Demographics</div>
              <div className="detail-grid">
                <div>
                  <div className="detail-label">Applicant Age:</div>
                  <div className="detail-value tabular-nums">{selectedApp.age !== null ? `${selectedApp.age} Years` : <span className="null-badge">NULL (Sanitized)</span>}</div>
                </div>
                <div>
                  <div className="detail-label">Gender:</div>
                  <div className="detail-value">{selectedApp.gender || <span className="null-badge">NULL</span>}</div>
                </div>
                <div>
                  <div className="detail-label">Marital Status:</div>
                  <div className="detail-value">{selectedApp.marital_status || <span className="null-badge">NULL</span>}</div>
                </div>
                <div>
                  <div className="detail-label">Education Level:</div>
                  <div className="detail-value">{selectedApp.education_level || <span className="null-badge">NULL</span>}</div>
                </div>
                <div>
                  <div className="detail-label">Employment Status:</div>
                  <div className="detail-value">{selectedApp.employment_status || <span className="null-badge">NULL</span>}</div>
                </div>
                <div>
                  <div className="detail-label">Job Experience:</div>
                  <div className="detail-value tabular-nums">{selectedApp.job_experience_years !== null ? `${selectedApp.job_experience_years} Years` : <span className="null-badge">NULL</span>}</div>
                </div>
                <div>
                  <div className="detail-label">Household Dependents:</div>
                  <div className="detail-value tabular-nums">{selectedApp.dependents !== null ? selectedApp.dependents : <span className="null-badge">NULL</span>}</div>
                </div>
                <div>
                  <div className="detail-label">Banking Tenure:</div>
                  <div className="detail-value tabular-nums">{selectedApp.bank_account_tenure_months !== null ? `${selectedApp.bank_account_tenure_months} Months` : <span className="null-badge">NULL</span>}</div>
                </div>
              </div>
            </div>

            {/* Section 3: Financial Balance Sheet */}
            <div>
              <div className="detail-section-title">Verified Balance Sheet (CU)</div>
              <div className="detail-grid">
                <div>
                  <div className="detail-label">Annual Income:</div>
                  <div className="detail-value tabular-nums">{formatCU(selectedApp.annual_income)}</div>
                </div>
                <div>
                  <div className="detail-label">Monthly Income (Calculated):</div>
                  <div className="detail-value tabular-nums">{formatCU(selectedApp.monthly_income_calculated)}</div>
                </div>
                <div>
                  <div className="detail-label">Savings Balance:</div>
                  <div className="detail-value tabular-nums">{formatCU(selectedApp.savings_balance)}</div>
                </div>
                <div>
                  <div className="detail-label">Checking Balance:</div>
                  <div className="detail-value tabular-nums">{formatCU(selectedApp.checking_balance)}</div>
                </div>
                <div>
                  <div className="detail-label">Total Assets:</div>
                  <div className="detail-value tabular-nums">{formatCU(selectedApp.total_assets)}</div>
                </div>
                <div>
                  <div className="detail-label">Total Liabilities:</div>
                  <div className="detail-value tabular-nums">{formatCU(selectedApp.total_liabilities)}</div>
                </div>
                <div>
                  <div className="detail-label">Net Worth (Assets - Liab):</div>
                  <div className="detail-value tabular-nums" style={{ fontWeight: 700 }}>{formatCU(selectedApp.net_worth)}</div>
                </div>
                <div>
                  <div className="detail-label">Monthly Debt Servicing:</div>
                  <div className="detail-value tabular-nums">{formatCU(selectedApp.monthly_debt_payment)}</div>
                </div>
              </div>
            </div>

            {/* Section 4: Credit Bureau & Proprietary Scorecard */}
            <div>
              <div className="detail-section-title">Credit Bureau & Institutional Scorecard</div>
              <div className="detail-grid">
                <div>
                  <div className="detail-label">Bureau Credit Score [0, 999]:</div>
                  <div className="detail-value tabular-nums" style={{ fontWeight: 700, color: 'var(--brand-cyan)' }}>
                    {selectedApp.bureau_credit_score !== null ? selectedApp.bureau_credit_score : <span className="null-badge">NULL (Missing)</span>}
                  </div>
                </div>
                <div>
                  <div className="detail-label">Bureau Prior Loan Status:</div>
                  <div className="detail-value">{selectedApp.bureau_prior_loan_status || <span className="null-badge">NULL</span>}</div>
                </div>
                <div>
                  <div className="detail-label">Existing Bureau Loans:</div>
                  <div className="detail-value tabular-nums">{selectedApp.bureau_existing_loans !== null ? selectedApp.bureau_existing_loans : <span className="null-badge">NULL</span>}</div>
                </div>
                <div>
                  <div className="detail-label">Late Payments (2 Yrs):</div>
                  <div className="detail-value tabular-nums">{selectedApp.bureau_late_payments_2yr !== null ? selectedApp.bureau_late_payments_2yr : <span className="null-badge">NULL</span>}</div>
                </div>
                <div>
                  <div className="detail-label">Proprietary Risk Score [0, 100]:</div>
                  <div className="detail-value tabular-nums" style={{ fontWeight: 700 }}>
                    {selectedApp.proprietary_risk_score !== null ? `${selectedApp.proprietary_risk_score.toFixed(1)} / 100` : <span className="null-badge">NULL</span>}
                  </div>
                </div>
                <div>
                  <div className="detail-label">Source Risk Tier:</div>
                  <div className="detail-value">
                    <span className={`badge badge-tier-${(selectedApp.risk_tier || 'medium').toLowerCase()}`}>
                      {selectedApp.risk_tier}
                    </span>
                  </div>
                </div>
              </div>
            </div>

            {/* Section 5: Origination Dimensions & Quality Flags */}
            <div>
              <div className="detail-section-title">Conformed Dimensions & Audit Flags</div>
              <div className="detail-grid">
                <div>
                  <div className="detail-label">Channel:</div>
                  <div className="detail-value">{selectedApp.channel_name}</div>
                </div>
                <div>
                  <div className="detail-label">Loan Purpose:</div>
                  <div className="detail-value">{selectedApp.purpose_name}</div>
                </div>
                <div>
                  <div className="detail-label">Region:</div>
                  <div className="detail-value">{selectedApp.region}</div>
                </div>
                <div>
                  <div className="detail-label">Residential Status:</div>
                  <div className="detail-value">{selectedApp.residential_status}</div>
                </div>
                <div>
                  <div className="detail-label">Property Ownership:</div>
                  <div className="detail-value">{selectedApp.property_ownership}</div>
                </div>
                <div>
                  <div className="detail-label">Invalid Financials Flag:</div>
                  <div className="detail-value">
                    {selectedApp.has_invalid_financials === 1 ? (
                      <span className="badge badge-flag">Flagged (Corrupted Negative)</span>
                    ) : (
                      <span style={{ color: 'var(--color-success)' }}>0 (Clean)</span>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
