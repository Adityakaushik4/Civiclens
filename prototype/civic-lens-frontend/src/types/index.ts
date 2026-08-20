export type Category =
  | 'ROAD_DAMAGE'
  | 'GARBAGE_UNCOLLECTED'
  | 'STREETLIGHT_DEFECT'
  | 'WATER_LEAKAGE'
  | 'DRAINAGE_BLOCKAGE'
  | 'SEWAGE_OVERFLOW'
  | 'PARK_MAINTENANCE'
  | 'TRAFFIC_SIGNAL_FAULT'
  | 'OTHER';

export type Department =
  | 'Roads & PWD'
  | 'Sanitation & Waste Management'
  | 'Water Supply'
  | 'Electrical / Street Lighting'
  | 'Drainage & Sewerage'
  | 'Public Health'
  | 'Traffic & Road Safety'
  | 'Parks & Horticulture'
  | 'Street Cleaning'
  | 'Public Toilets'
  | 'Encroachment / Illegal Construction'
  | 'Building & Infrastructure'
  | 'Environment / Pollution'
  | 'Animal Control'
  | 'Fire & Emergency Services'
  | 'Municipal Administration'
  | 'Other / General';

export type ConfidenceStatus = 'ACCEPTED' | 'REVIEW_RECOMMENDED' | 'LOW_CONFIDENCE';

export type DuplicateAction = 'AUTOMATIC_MERGE' | 'HUMAN_REVIEW_RECOMMENDED' | 'NEW_MASTER_ISSUE';

export interface ComplaintAnalysisRequest {
  text: string;
}

export interface ComplaintAnalysis {
  original_text: string;
  original_language: string;
  normalized_text: string;
  language: string;
  category: Category;
  subcategory: string;
  severity: number;
  safety_risk: boolean;
  public_impact: number;
  location_description?: string;
  summary: string;
  confidence: number;
  confidence_status: ConfidenceStatus;
  language_confidence?: number;
  language_detector?: string;
  language_disagreement?: boolean;
}

export interface TranscriptionResult {
  text: string;
  language: string;
  confidence: number;
  provider: string;
}

export interface AudioComplaintAnalysisResponse {
  input_type: 'audio';
  transcription: TranscriptionResult;
  analysis: ComplaintAnalysis;
}

export interface VisualAnalysis {
  visible_issue: boolean;
  category: Category;
  subcategory: string;
  severity: number;
  safety_risk: boolean;
  public_impact: number;
  description: string;
  confidence: number;
}

export interface ImageComplaintAnalysisResponse {
  input_type: 'image';
  visual_analysis: VisualAnalysis;
  analysis: ComplaintAnalysis;
  evidence_disagreement?: boolean;
  disagreement_reason?: string;
}

export interface MasterIssueModel {
  id: str;
  title: string;
  category: Category;
  subcategory: string;
  status: string;
  severity_score: number;
  citizen_reporter_count: number;
  latitude: number;
  longitude: number;
  address_description?: string;
  description?: string;
  department?: string;
  priority_level?: string;
  is_overdue?: boolean;
  created_at: string;
}

export type str = string;

export interface ScoreBreakdown {
  geographic_distance_meters: number;
  spatial_score: number;
  semantic_similarity: number;
  category_match_score: number;
  temporal_score: number;
  total_score: number;
  normalized_weights_used?: boolean;
}

export interface DuplicateCheckResponse {
  action: DuplicateAction;
  matched_master_issue_id?: string;
  master_issue?: MasterIssueModel;
  total_score: number;
  score_breakdown: ScoreBreakdown;
  citizen_reporter_count: number;
  review_id?: string;
}

export interface PriorityAssessmentResult {
  issue_id: string;
  priority_score: number;
  priority_level: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  calculated_at: string;
  formula_version?: string;
  factors?: any;
  score_computation_log?: string;
  // Aliases for compatibility
  final_priority_score?: number;
  priority_tier?: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
}

export interface RoutingDecisionResult {
  decision_id?: string;
  issue_id: string;
  category?: Category;
  subcategory?: string;
  priority_score?: number;
  priority_level?: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  primary_department?: string;
  responsible_unit?: string;
  escalation_department?: string;
  selection_reason?: string;
  routed_at: string;
  sla?: {
    policy_id: string;
    status: string;
    acknowledgement_minutes: number;
    resolution_minutes: number;
    acknowledgement_deadline: string;
    resolution_deadline: string;
  };
  // Aliases for compatibility
  assigned_department?: string;
  jurisdiction_id?: string;
  sla_policy_id?: string;
  acknowledgement_deadline?: string;
  resolution_deadline?: string;
  routing_confidence?: number;
  explanation?: string;
}

export interface IssueLifecycleRecord {
  issue_id: string;
  current_state: 'REPORTED' | 'ROUTED' | 'ACKNOWLEDGED' | 'IN_PROGRESS' | 'AWAITING_VERIFICATION' | 'RESOLVED' | 'REOPENED' | 'ESCALATED';
  department: string;
  acknowledged_by?: string;
  acknowledged_at?: string;
  assigned_operator_id?: string;
  started_at?: string;
  completed_at?: string;
  resolved_at?: string;
  escalated_at?: string;
  escalation_count: number;
  reopen_count: number;
  history: Array<{
    state: string;
    timestamp: string;
    actor: string;
    notes?: string;
  }>;
}

export interface PublicIssueView {
  public_id: string;
  issue_id: string;
  category: Category | string;
  subcategory: string;
  fuzzed_latitude: number;
  fuzzed_longitude: number;
  public_location_description: string;
  status: string;
  priority_level: string;
  department_name: string;
  citizen_report_count: number;
  public_evidence_urls: string[];
  public_timeline: PublicTimelineEntry[];
  updated_at: string;
}

export interface PublicTimelineEntry {
  timestamp: string;
  event: string;
  public_note?: string;
}

export interface GroundedQAResponse {
  answer: string;
  grounded: boolean;
  citations: Array<{
    document_title: string;
    issuing_authority: string;
    section: string;
    source_reference: string;
  }>;
  confidence: number;
}

export interface CivicAnalyticsSnapshot {
  snapshot_id?: string;
  jurisdiction_id?: string | null;
  period_name?: string;
  total_master_issues?: number;
  total_citizen_reports?: number;
  total_issues_reported?: number;
  total_issues_resolved?: number;
  pending_verification_count?: number;
  resolved_today_count?: number;
  reopened_count?: number;
  overdue_count?: number;
  resolution_rate?: number;
  resolution_rate_percent?: number;
  sla_breach_rate?: number;
  sla_compliance_percent?: number;
  average_resolution_hours?: number;
  reopening_rate?: number;
  category_distribution?: Record<string, number>;
  category_counts?: Record<string, number>;
  department_distribution?: Record<string, number>;
  priority_distribution?: Record<string, number>;
  status_counts?: Record<string, number>;
  created_at?: string;
  generated_at?: string;
}

export interface CivicHotspot {
  hotspot_id: string;
  jurisdiction_id?: string | null;
  ward_name?: string;
  category: Category;
  center_latitude: number;
  center_longitude: number;
  radius_meters: number;
  master_issue_count: number;
  citizen_report_count: number;
  severity_score_weighted: number;
  vulnerable_location_near: boolean;
  suppressed_publicly: boolean;
  linked_master_issue_ids: string[];
  created_at: string;
}

export interface CivicProjectOpportunity {
  opportunity_id: string;
  jurisdiction_id?: string | null;
  title: string;
  description?: string;
  category: Category | string;
  department?: string | null;
  hotspot_id?: string;
  affected_area_description?: string;
  suggested_budget?: number | null;
  total_citizen_reports?: number;
  complaint_count?: number;
  linked_master_issue_ids?: string[];
  estimated_priority_avg?: number;
  priority_score?: number;
  status?: string;
  created_at?: string;
}

export interface CitizenProposal {
  proposal_id: string;
  jurisdiction_id: string;
  title: string;
  description: string;
  category: Category;
  opportunity_id?: string;
  author_citizen_id: string;
  requested_budget: number;
  cost_status: 'ESTIMATED' | 'VERIFIED';
  status: 'DRAFT' | 'SUBMITTED' | 'UNDER_REVIEW' | 'ELIGIBLE' | 'INELIGIBLE' | 'FUNDED' | 'REJECTED';
  created_at: string;
}

export interface AIDraftProposalResponse {
  opportunity_id: string;
  suggested_title: string;
  suggested_description: string;
  linked_master_issue_ids: string[];
  total_citizen_reports: number;
}

export interface ProposalEligibility {
  eligibility_id: string;
  proposal_id: string;
  cycle_id: string;
  is_eligible: boolean;
  rule_results: Record<string, boolean>;
  evaluation_notes: string;
  evaluated_at: string;
}

export interface ProposalScore {
  proposal_id: string;
  community_support_score: number;
  cost_efficiency_score: number;
  severity_mitigation_score: number;
  hotspot_alignment_score: number;
  feasibility_score: number;
  equity_impact_score: number;
  final_composite_score: number;
  score_explanation: string;
}

export interface BudgetCycle {
  cycle_id: string;
  jurisdiction_id: string;
  cycle_name: string;
  total_budget: number;
  min_project_cost: number;
  max_project_cost: number;
  voting_start_time: string;
  voting_end_time: string;
  max_votes_per_citizen: number;
  status: string;
  active: boolean;
}

export interface BudgetAllocationResult {
  cycle_id: string;
  total_budget_available: number;
  total_budget_allocated: number;
  remaining_unallocated_budget: number;
  funded_proposals: Array<{
    proposal_id: string;
    title: string;
    requested_budget: number;
    score: number;
  }>;
  unfunded_proposals: Array<{
    proposal_id: string;
    title: string;
    requested_budget: number;
    score: number;
    reason_unfunded: string;
  }>;
  algorithm_used: string;
  allocated_at: string;
}
export interface CandidateLocation { display_name: string; latitude: number; longitude: number; confidence: number; is_in_jurisdiction?: boolean; source?: string; }
export interface LocationClues { village_locality?: string; ward?: string; road_street?: string; landmark?: string; city_district?: string; raw_query: string; confidence: number; }
export interface LocationExtractionResponse { clues: LocationClues; candidates: CandidateLocation[]; }
export interface AudioTranscriptionResponse { input_type: 'audio'; transcription: TranscriptionResult; }
