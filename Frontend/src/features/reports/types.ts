// NOTE: The backend source for GET /api/v1/reports/analytics was not available
// in this environment for direct inspection. AnalyticsData is typed broadly so
// the UI can render whatever the backend actually returns without field-name
// assumptions. Verify and tighten these types against the real Pydantic schema
// before shipping to production.
export type AnalyticsData = Record<string, unknown>;

export interface AnalyticsResponse {
  // Envelope data field — matches ApiResponse<AnalyticsData>
  [key: string]: unknown;
}
