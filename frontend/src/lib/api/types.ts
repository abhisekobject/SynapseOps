// Common Types

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pages: number;
}

// Health & State

export interface SystemSnapshot {
  timestamp: string;
  services: Record<string, ServiceState>;
  degraded_services: string[];
  system_status: 'healthy' | 'degraded' | 'critical';
}

export interface ServiceState {
  service_id: string;
  status: 'healthy' | 'degraded' | 'unavailable' | 'unknown';
  metrics: Record<string, number>;
  active_failures: string[];
  last_updated: string;
}

export interface StateTransition {
  id: string;
  service_id: string;
  previous_status: string;
  new_status: string;
  reason: string;
  created_at: string;
}

// Events

export interface Event {
  id: string;
  event_type: string;
  service_id: string;
  severity: 'info' | 'warning' | 'error' | 'critical';
  status: 'active' | 'cleared';
  message: string;
  correlation_id: string | null;
  trace_id: string | null;
  created_at: string;
  updated_at: string;
  evidence: Record<string, any>;
}

// Anomalies

export interface Anomaly {
  id: string;
  incident_id: string | null;
  anomaly_type: 'metric' | 'log_pattern' | 'trace' | 'event';
  severity: 'low' | 'medium' | 'high';
  status: 'open' | 'correlated' | 'resolved' | 'dismissed';
  service_name: string;
  metric_name: string | null;
  observed_value: number | null;
  baseline_value: number | null;
  confidence: number;
  description: string | null;
  detected_at: string;
}

// Incidents

export interface Incident {
  id: string;
  title: string;
  description: string | null;
  severity: 'low' | 'medium' | 'high' | 'critical';
  status: 'detected' | 'investigating' | 'diagnosed' | 'recovering' | 'resolved' | 'escalated' | 'closed';
  affected_services: string[];
  probable_root_cause: string | null;
  detected_at: string;
  resolved_at: string | null;
}

// Intelligence (RCA & Dependencies)

export interface DependencyGraphData {
  nodes: string[];
  edges: Record<string, string[]>;
}

export interface RCAResult {
  analysis_id: string;
  timestamp: string;
  candidates: RCACandidate[];
  window_minutes: number;
  analyzed_events: number;
}

export interface RCACandidate {
  service_id: string;
  score: number;
  severity: string;
  evidence_count: number;
  primary_evidence: string[];
  dependency_depth: number;
}

// Reasoning

export interface IncidentReasoningResult {
  reasoning_id: string;
  incident_id: string;
  timestamp: string;
  summary: string;
  facts: string[];
  observations: string[];
  hypotheses: string[];
  recommended_actions: RecommendedAction[];
  uncertainty_factors: string[];
  provider_name: string;
  provider_model: string;
}

export interface RecommendedAction {
  action_type: string;
  target: string;
  description: string;
  expected_outcome: string;
  risk_level: string;
}

// Recovery & Safety

export interface RecoveryPlan {
  plan_id: string;
  incident_id: string;
  target_service: string;
  action: ActionParameters;
  risk_classification: RiskClassification;
  created_at: string;
  verification_conditions: VerificationCondition[];
  lineage: PlanLineage;
}

export interface ActionParameters {
  action_type: string;
  target: string;
  parameters: Record<string, any>;
  reversible: boolean;
}

export interface RiskClassification {
  level: 'low' | 'medium' | 'high' | 'critical';
  blast_radius: string;
  estimated_downtime_seconds: number;
  requires_human_approval: boolean;
  reasons: string[];
}

export interface VerificationCondition {
  metric: string;
  operator: string;
  target_value: number;
  timeout_seconds: number;
}

export interface PlanLineage {
  reasoning_id: string;
  rca_id: string | null;
}

export interface PolicyDecision {
  decision_id: string;
  plan_id: string;
  plan_hash: string;
  decision: 'allow' | 'deny' | 'requires_approval';
  reasons: string[];
  evaluated_at: string;
  policy_version: string;
}

export interface ApprovalRequestResponse {
  approval_id: string;
  plan_id: string;
  plan_hash: string;
  status: 'pending' | 'approved' | 'rejected' | 'expired';
  requested_by: string;
  requested_at: string;
  expires_at: string;
  reviewed_by?: string;
  reviewed_at?: string;
}

// Execution & Verification

export interface ExecutionResult {
  execution_id: string;
  plan_id: string;
  approval_id: string;
  status: 'pending' | 'executing' | 'succeeded' | 'failed' | 'cancelled';
  started_at: string;
  completed_at: string | null;
  error_message: string | null;
}

// Memory & Learning

export interface Experience {
  experience_id: string;
  incident_id: string | null;
  target_service: string;
  action_type: string;
  action_parameters: Record<string, any>;
  environment: string;
  is_simulated: boolean;
  expected_outcome: string | null;
  observed_outcome: string;
  assessment: 'success' | 'partial' | 'failure' | 'unknown';
  execution_id: string | null;
  verification_id: string | null;
  timestamp: string;
  fingerprint: string;
}

export interface ExperienceLearningSignal {
  signal_id: string;
  experience_id: string;
  incident_id: string | null;
  target: string;
  action: string;
  environment: string;
  is_simulated: boolean;
  outcome: 'success' | 'partial' | 'failure' | 'unknown';
  verification_passed: boolean | null;
  created_at: string;
  schema_version: string;
}

export interface OperationalKnowledge {
  knowledge_id: string;
  target: string;
  action: string;
  environment: string;
  is_simulated: boolean | null;
  total_experiences: number;
  successful_outcomes: number;
  partial_outcomes: number;
  failed_outcomes: number;
  unknown_outcomes: number;
  verification_passes: number;
  verification_failures: number;
  observed_effectiveness: number | null;
  first_observed: string;
  last_observed: string;
  last_updated: string;
  schema_version: string;
}
