import { apiClient } from "./client";

export interface DashboardKpi {
  total_scans: number;
  last_30d_scans: number;
  unique_cards: number;
  active_members: number;
}

export interface TimelinePoint {
  day: string;
  count: number;
}

export interface RegionStats {
  region: string;
  count: number;
}

export interface DeviceStats {
  device_type: string;
  count: number;
}

export interface TopCard {
  card_id: string;
  last_name: string;
  first_name: string;
  membership_no: string;
  scans: number;
}

export interface DashboardData {
  kpi: DashboardKpi;
  by_day: TimelinePoint[];
  top_regions: RegionStats[];
  top_devices: DeviceStats[];
  top_cards: TopCard[];
}

export interface CardAnalytics {
  card_id: string;
  total_scans: number;
  last_scan: string | null;
  by_day: TimelinePoint[];
  by_region: RegionStats[];
  by_device: DeviceStats[];
}

export interface AnalyticsParams {
  from?: string;
  to?: string;
}

export interface TopActiveUser {
  card_id: string;
  last_name: string;
  first_name: string;
  middle_name?: string | null;
  category_name?: string | null;
  membership_no: string;
  scans: number;
  top_region?: string | null;
  top_device?: string | null;
}

export interface TopActiveUsersResponse {
  items: TopActiveUser[];
  total: number;
  page: number;
  page_size: number;
}

export interface TopActiveParams {
  from?: string;
  to?: string;
  page?: number;
  page_size?: number;
}

export const analyticsApi = {
  dashboard: (params?: AnalyticsParams) =>
    apiClient.get<DashboardData>("/analytics/dashboard", { params }),
  card: (id: string, params?: AnalyticsParams) =>
    apiClient.get<CardAnalytics>(`/analytics/cards/${id}`, { params }),
  topActive: (params?: TopActiveParams) =>
    apiClient.get<TopActiveUsersResponse>("/analytics/top-active", { params }),
  report: (params?: { from?: string; to?: string }) =>
    apiClient.get<Blob>("/analytics/report.xlsx", { params, responseType: "blob" }),
  cardReport: (id: string, params?: { from?: string; to?: string }) =>
    apiClient.get<Blob>(`/analytics/cards/${id}/report.xlsx`, {
      params,
      responseType: "blob",
    }),
};
