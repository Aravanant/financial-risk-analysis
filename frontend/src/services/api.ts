/**
 * RiskLens AI — API Client Service
 * 
 * Provides typed HTTP requests connecting the React frontend directly to the FastAPI backend.
 * Uses configurable base URL via VITE_API_BASE_URL (defaults to empty string for proxy or http://127.0.0.1:8000).
 */

import type {
  HealthResponse,
  PortfolioKPIs,
  ChannelPerformanceItem,
  LoanPurposeItem,
  HaircutResponse,
  RiskTierItem,
  DataQualityResponse,
  PaginatedApplicationsResponse,
  ApplicationSummary,
  ApplicationFilterParams,
  ServicingDemoResponse
} from '../types/api';

const BASE_URL = import.meta.env.VITE_API_BASE_URL !== undefined 
  ? import.meta.env.VITE_API_BASE_URL 
  : '';

class ApiService {
  private async request<T>(endpoint: string, options?: RequestInit): Promise<T> {
    const url = `${BASE_URL}${endpoint}`;
    try {
      const response = await fetch(url, {
        headers: {
          'Content-Type': 'application/json',
          ...(options?.headers || {})
        },
        ...options
      });

      if (!response.ok) {
        let errorDetail = `Request failed with status ${response.status}`;
        try {
          const errorJson = await response.json();
          if (errorJson.detail) {
            errorDetail = typeof errorJson.detail === 'string' 
              ? errorJson.detail 
              : JSON.stringify(errorJson.detail);
          }
        } catch {
          // Non-JSON response
        }
        throw new Error(errorDetail);
      }

      return await response.json();
    } catch (err: any) {
      if (err instanceof TypeError && err.message.includes('fetch')) {
        throw new Error(
          `Unable to connect to RiskLens API at ${url}. Ensure the FastAPI backend is running.`,
          { cause: err }
        );
      }
      throw err;
    }
  }

  // 1. Health
  async getHealth(): Promise<HealthResponse> {
    return this.request<HealthResponse>('/health');
  }

  // 2. Portfolio KPIs
  async getOverview(): Promise<PortfolioKPIs> {
    return this.request<PortfolioKPIs>('/api/v1/overview');
  }

  // 3. Channels
  async getChannels(): Promise<ChannelPerformanceItem[]> {
    return this.request<ChannelPerformanceItem[]>('/api/v1/channels');
  }

  // 4. Loan Purposes
  async getLoanPurposes(): Promise<LoanPurposeItem[]> {
    return this.request<LoanPurposeItem[]>('/api/v1/loan-purposes');
  }

  // 5. Haircut
  async getHaircut(): Promise<HaircutResponse> {
    return this.request<HaircutResponse>('/api/v1/haircut');
  }

  // 6. Risk Tiers
  async getRiskTiers(): Promise<RiskTierItem[]> {
    return this.request<RiskTierItem[]>('/api/v1/risk-tiers');
  }

  // 7. Data Quality
  async getDataQuality(): Promise<DataQualityResponse> {
    return this.request<DataQualityResponse>('/api/v1/data-quality');
  }

  // 8. Applications Paginated
  async getApplications(params: ApplicationFilterParams = {}): Promise<PaginatedApplicationsResponse> {
    const query = new URLSearchParams();
    if (params.page !== undefined) query.set('page', String(params.page));
    if (params.page_size !== undefined) query.set('page_size', String(params.page_size));
    if (params.decision) query.set('decision', params.decision);
    if (params.channel) query.set('channel', params.channel);
    if (params.loan_purpose) query.set('loan_purpose', params.loan_purpose);
    if (params.risk_tier) query.set('risk_tier', params.risk_tier);
    if (params.has_invalid_financials !== undefined) {
      query.set('has_invalid_financials', String(params.has_invalid_financials));
    }
    if (params.sort_by) query.set('sort_by', params.sort_by);
    if (params.sort_order) query.set('sort_order', params.sort_order);

    const queryString = query.toString();
    const endpoint = `/api/v1/applications${queryString ? `?${queryString}` : ''}`;
    return this.request<PaginatedApplicationsResponse>(endpoint);
  }

  // 9. Single Application by ID
  async getApplicationById(id: number): Promise<ApplicationSummary> {
    return this.request<ApplicationSummary>(`/api/v1/applications/${id}`);
  }

  // 10. Quarantined Servicing Demo
  async getServicingDemoRecord(id: number): Promise<ServicingDemoResponse> {
    return this.request<ServicingDemoResponse>(`/api/v1/demo/servicing-snapshot/${id}`);
  }
}

export const api = new ApiService();
