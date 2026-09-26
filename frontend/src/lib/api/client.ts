import * as Types from './types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api/v1';

class ApiClientError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = 'ApiClientError';
  }
}

async function fetchApi<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = endpoint.startsWith('http') ? endpoint : `${API_BASE_URL}${endpoint}`;
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  });

  if (!response.ok) {
    const errorText = await response.text();
    let errorMessage = `HTTP Error ${response.status}`;
    try {
      const errorJson = JSON.parse(errorText);
      errorMessage = errorJson.detail || errorMessage;
    } catch {
      // Ignored
    }
    throw new ApiClientError(response.status, errorMessage);
  }

  return response.json();
}

export const api = {
  // Health
  getHealth: () => fetchApi<{status: string, app: string, environment: string}>('http://localhost:8000/health'),
  
  // State
  getSystemState: () => fetchApi<Types.SystemSnapshot>('/state'),
  getServices: () => fetchApi<Types.ServiceState[]>('/state/services'),
  
  // Events
  getEvents: (page = 1, limit = 50) => fetchApi<Types.PaginatedResponse<Types.Event>>(`/events?page=${page}&limit=${limit}`),
  getActiveEvents: () => fetchApi<Types.Event[]>('/events/active'),
  
  // Anomalies
  getAnomalies: (page = 1, limit = 50) => fetchApi<Types.PaginatedResponse<Types.Anomaly>>(`/anomalies?page=${page}&limit=${limit}`),
  
  // Incidents
  getIncidents: (page = 1, limit = 50) => fetchApi<Types.PaginatedResponse<Types.Incident>>(`/incidents?page=${page}&limit=${limit}`),
  getIncident: (id: string) => fetchApi<Types.Incident>(`/incidents/${id}`),
  
  // Intelligence
  getDependencies: () => fetchApi<Types.DependencyGraphData>('/intelligence/dependencies'),
  getServiceDependencies: (serviceId: string) => fetchApi<any>(`/intelligence/dependencies/${serviceId}`),
  analyzeRCA: () => fetchApi<Types.RCAResult>('/intelligence/rca/analyze'),
  
  // Reasoning
  getIncidentReasoning: () => fetchApi<Types.IncidentReasoningResult>('/intelligence/incident-reasoning'),
  
  // Recovery
  createRecoveryPlan: (reasoning: Types.IncidentReasoningResult) => 
    fetchApi<Types.RecoveryPlan>('/intelligence/recovery-plan', {
      method: 'POST',
      body: JSON.stringify(reasoning)
    }),
    
  // Safety
  evaluatePolicy: (plan: Types.RecoveryPlan) => 
    fetchApi<Types.PolicyDecision>('/intelligence/safety/policy/evaluate', {
      method: 'POST',
      body: JSON.stringify(plan)
    }),
    
  requestApproval: (plan: Types.RecoveryPlan) =>
    fetchApi<Types.ApprovalRequestResponse>('/intelligence/safety/approvals', {
      method: 'POST',
      body: JSON.stringify(plan)
    }),
    
  approvePlan: (approvalId: string, plan: Types.RecoveryPlan) =>
    fetchApi<Types.ApprovalRequestResponse>(`/intelligence/safety/approvals/${approvalId}/approve`, {
      method: 'POST',
      body: JSON.stringify(plan)
    }),
    
  // Execution
  executePlan: (approvalId: string, plan: Types.RecoveryPlan) =>
    fetchApi<Types.ExecutionResult[]>(`/intelligence/execution/execute?approval_id=${approvalId}`, {
      method: 'POST',
      body: JSON.stringify(plan)
    }),

  // Memory
  getExperiences: (page = 1, limit = 50) => fetchApi<any>(`/intelligence/memory/experiences?page=${page}&limit=${limit}`),
  
  // Learning
  getLearningSignals: (page = 1, limit = 50) => fetchApi<any>(`/intelligence/learning/signals?page=${page}&limit=${limit}`)
    .then(res => Array.isArray(res) ? { items: res, total: res.length, page: 1, pages: 1 } : res),
  getOperationalKnowledge: (page = 1, limit = 50) => fetchApi<any>(`/intelligence/learning/knowledge?page=${page}&limit=${limit}`)
    .then(res => Array.isArray(res) ? { items: res, total: res.length, page: 1, pages: 1 } : res),
  
  // Simulation
  getActiveFailures: () => fetchApi<any>('/simulation/state').then(res => res.active_scenarios),
  injectFailure: (target: string, type: string) => 
    fetchApi<any>('/simulation/failures/inject', {
      method: 'POST',
      body: JSON.stringify({ target: target, failure_type: type })
    }),
  clearFailure: (target: string, type: string) =>
    fetchApi<any>('/simulation/failures', {
      method: 'DELETE',
      body: JSON.stringify({ target: target })
    })
};
