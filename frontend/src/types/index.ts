export type SeedEntityType =
  | 'domain'
  | 'ip_address'
  | 'url'
  | 'email'
  | 'person'
  | 'organization'
  | 'file_hash'
  | 'phone'
  | 'asn'
  | 'certificate';

export type InvestigationStatus =
  | 'draft'
  | 'active'
  | 'paused'
  | 'completed'
  | 'failed'
  | 'cancelled';

export type EntityConfidence =
  | 'confirmed'
  | 'high'
  | 'medium'
  | 'low'
  | 'observed'
  | 'inferred';

export type RelationshipType =
  | 'resolves_to'
  | 'associated_with'
  | 'mentions'
  | 'registered_by'
  | 'communicates_with'
  | 'contains'
  | 'attributed_to'
  | 'derived_from'
  | 'issued_to';

export interface Investigation {
  id: string;
  name: string;
  description: string | null;
  seed_entity: string;
  seed_entity_type: SeedEntityType;
  status: InvestigationStatus;
  authorized_use_confirmed: boolean;
  created_at: string;
  updated_at: string;
  entity_count: number;
  evidence_count: number;
  is_fixture?: boolean;
}

export interface InvestigationCreate {
  name: string;
  description?: string;
  seed_entity: string;
  seed_entity_type: SeedEntityType;
  authorized_use_confirmed: boolean;
  config?: Record<string, unknown>;
}

export interface InvestigationUpdate {
  name?: string;
  description?: string;
  status?: InvestigationStatus;
  config?: Record<string, unknown>;
}

export interface InvestigationListResponse {
  investigations: Investigation[];
  total: number;
}

export interface Entity {
  id: string;
  investigation_id: string;
  entity_type: SeedEntityType;
  value: string;
  normalized_value: string;
  source: string | null;
  confidence: string;
  first_seen: string;
  last_seen: string;
  metadata?: Record<string, unknown> | null;
}

export interface Relationship {
  id: string;
  source_entity_id: string;
  target_entity_id: string;
  relationship_type: RelationshipType;
  confidence: string;
  evidence_id: string | null;
  created_at: string;
}

export interface Evidence {
  id: string;
  investigation_id: string;
  source_url: string | null;
  tool_name: string | null;
  collection_method: string | null;
  content_type: string | null;
  sha256_hash: string | null;
  storage_ref: string | null;
  collected_at: string;
  status: string;
  raw_content?: string | null;
}

export interface EvidenceCreate {
  source_url?: string;
  tool_name?: string;
  collection_method?: string;
  content_type?: string;
  raw_content?: string;
}

export interface ActivityLog {
  id: string;
  investigation_id: string;
  action: string;
  actor: string;
  details?: Record<string, unknown> | null;
  timestamp: string;
}

export interface GraphNode {
  id: string;
  label: string;
  entity_type: SeedEntityType;
  value: string;
  confidence: string;
  metadata?: Record<string, unknown> | null;
  // Canvas coordinate helpers for react-force-graph
  x?: number;
  y?: number;
  vx?: number;
  vy?: number;
  color?: string;
  val?: number;
}

export interface GraphEdge {
  id: string;
  source: string | { id: string };
  target: string | { id: string };
  relationship_type: string;
  confidence: string;
  evidence_id?: string | null;
}

export interface GraphResponse {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface Tool {
  id: string;
  name: string;
  description: string | null;
  category: string | null;
  input_schema?: {
    type?: string;
    properties?: Record<string, { type?: string; description?: string; default?: unknown }>;
    required?: string[];
  } | null;
  enabled: boolean;
  requires_network: boolean;
  risk_level: string;
}

export interface ToolExecuteRequest {
  tool_name: string;
  parameters: Record<string, unknown>;
  investigation_id?: string;
}

export interface ToolExecuteResponse {
  success: boolean;
  tool_name: string;
  result: Record<string, unknown> | null;
  error?: string | null;
  evidence_id?: string | null;
  entities_found: number;
}

export interface HealthResponse {
  status: string;
  version: string;
  database: string;
  services: {
    shell_worker: string;
    browser_worker: string;
    planner_llm: string;
    extractor_llm: string;
  };
}
