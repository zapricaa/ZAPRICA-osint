import {
  Investigation,
  InvestigationCreate,
  InvestigationUpdate,
  InvestigationListResponse,
  Entity,
  Evidence,
  EvidenceCreate,
  ActivityLog,
  GraphResponse,
  Tool,
  ToolExecuteRequest,
  ToolExecuteResponse,
  HealthResponse,
} from '@/types';
import {
  FIXTURE_INVESTIGATIONS,
  FIXTURE_ENTITIES,
  FIXTURE_EVIDENCE,
  FIXTURE_ACTIVITY,
  FIXTURE_GRAPHS,
  FIXTURE_TOOLS,
} from './fixtures';

const API_BASE_URL = typeof window !== 'undefined' 
  ? '/api' 
  : (process.env.BACKEND_API_URL || 'http://localhost:8000/api');

export interface ApiStatus {
  isLive: boolean;
  checked: boolean;
  database?: string;
  error?: string;
}

// In-memory store for user-created items in fixture mode during active session
const memoryInvestigations: Investigation[] = [...FIXTURE_INVESTIGATIONS];
const memoryEntities: Record<string, Entity[]> = { ...FIXTURE_ENTITIES };
const memoryEvidence: Record<string, Evidence[]> = { ...FIXTURE_EVIDENCE };
const memoryActivity: Record<string, ActivityLog[]> = { ...FIXTURE_ACTIVITY };
const memoryGraphs: Record<string, GraphResponse> = { ...FIXTURE_GRAPHS };

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  async checkHealth(): Promise<HealthResponse | null> {
    try {
      const res = await fetch(`${this.baseUrl}/health`, {
        cache: 'no-store',
        signal: AbortSignal.timeout(3000),
      });
      if (!res.ok) return null;
      return await res.json();
    } catch {
      return null;
    }
  }

  async getInvestigations(
    status?: string,
    limit: number = 50,
    offset: number = 0
  ): Promise<{ data: InvestigationListResponse; isFixture: boolean }> {
    try {
      const params = new URLSearchParams();
      if (status) params.append('status', status);
      params.append('limit', limit.toString());
      params.append('offset', offset.toString());

      const res = await fetch(`${this.baseUrl}/investigations?${params.toString()}`, {
        cache: 'no-store',
        signal: AbortSignal.timeout(3500),
      });

      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data: InvestigationListResponse = await res.json();
      return { data, isFixture: false };
    } catch {
      // Fallback to clearly labeled development fixtures
      let filtered = [...memoryInvestigations];
      if (status) {
        filtered = filtered.filter((i) => i.status === status);
      }
      return {
        data: {
          investigations: filtered.slice(offset, offset + limit),
          total: filtered.length,
        },
        isFixture: true,
      };
    }
  }

  async getInvestigation(id: string): Promise<{ data: Investigation; isFixture: boolean }> {
    try {
      const res = await fetch(`${this.baseUrl}/investigations/${id}`, {
        cache: 'no-store',
        signal: AbortSignal.timeout(3500),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      return { data, isFixture: false };
    } catch {
      const found = memoryInvestigations.find((i) => i.id === id);
      if (found) {
        return { data: found, isFixture: true };
      }
      // If not in fixtures, create an ephemeral placeholder marked as fixture
      const placeholder: Investigation = {
        id,
        name: `Investigation ${id}`,
        description: 'Auto-generated fallback record for offline development inspection.',
        seed_entity: 'unknown-target.org',
        seed_entity_type: 'domain',
        status: 'active',
        authorized_use_confirmed: true,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        entity_count: 1,
        evidence_count: 0,
        is_fixture: true,
      };
      return { data: placeholder, isFixture: true };
    }
  }

  async createInvestigation(
    payload: InvestigationCreate
  ): Promise<{ data: Investigation; isFixture: boolean }> {
    try {
      const res = await fetch(`${this.baseUrl}/investigations`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        signal: AbortSignal.timeout(4000),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      return { data, isFixture: false };
    } catch {
      // Offline fixture simulation
      const newId = `inv-local-${Date.now().toString(36)}`;
      const now = new Date().toISOString();
      const created: Investigation = {
        id: newId,
        name: payload.name,
        description: payload.description || null,
        seed_entity: payload.seed_entity,
        seed_entity_type: payload.seed_entity_type,
        status: 'active',
        authorized_use_confirmed: payload.authorized_use_confirmed,
        created_at: now,
        updated_at: now,
        entity_count: 1,
        evidence_count: 0,
        is_fixture: true,
      };
      memoryInvestigations.unshift(created);

      // Seed entity
      const seedEnt: Entity = {
        id: `ent-seed-${Date.now()}`,
        investigation_id: newId,
        entity_type: payload.seed_entity_type,
        value: payload.seed_entity,
        normalized_value: payload.seed_entity.toLowerCase(),
        source: 'user_input',
        confidence: 'confirmed',
        first_seen: now,
        last_seen: now,
        metadata: { seed: true },
      };
      memoryEntities[newId] = [seedEnt];
      memoryEvidence[newId] = [];
      memoryActivity[newId] = [
        {
          id: `act-${Date.now()}`,
          investigation_id: newId,
          action: 'investigation_created',
          actor: 'user',
          details: { seed_entity: payload.seed_entity, seed_type: payload.seed_entity_type },
          timestamp: now,
        },
      ];
      memoryGraphs[newId] = {
        nodes: [
          {
            id: seedEnt.id,
            label: seedEnt.value,
            entity_type: seedEnt.entity_type,
            value: seedEnt.value,
            confidence: seedEnt.confidence,
          },
        ],
        edges: [],
      };

      return { data: created, isFixture: true };
    }
  }

  async updateInvestigation(
    id: string,
    payload: InvestigationUpdate
  ): Promise<{ data: Investigation; isFixture: boolean }> {
    try {
      const res = await fetch(`${this.baseUrl}/investigations/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        signal: AbortSignal.timeout(4000),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      return { data, isFixture: false };
    } catch {
      const idx = memoryInvestigations.findIndex((i) => i.id === id);
      if (idx !== -1) {
        memoryInvestigations[idx] = {
          ...memoryInvestigations[idx],
          ...(payload.name && { name: payload.name }),
          ...(payload.description !== undefined && { description: payload.description }),
          ...(payload.status && { status: payload.status }),
          updated_at: new Date().toISOString(),
        };
        return { data: memoryInvestigations[idx], isFixture: true };
      }
      throw new Error('Investigation not found');
    }
  }

  async deleteInvestigation(id: string): Promise<{ success: boolean; isFixture: boolean }> {
    try {
      const res = await fetch(`${this.baseUrl}/investigations/${id}`, {
        method: 'DELETE',
        signal: AbortSignal.timeout(4000),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return { success: true, isFixture: false };
    } catch {
      const idx = memoryInvestigations.findIndex((i) => i.id === id);
      if (idx !== -1) {
        memoryInvestigations.splice(idx, 1);
      }
      return { success: true, isFixture: true };
    }
  }

  async getEntities(investigationId: string): Promise<{ data: Entity[]; isFixture: boolean }> {
    try {
      const res = await fetch(`${this.baseUrl}/investigations/${investigationId}/entities`, {
        cache: 'no-store',
        signal: AbortSignal.timeout(3500),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      return { data, isFixture: false };
    } catch {
      return { data: memoryEntities[investigationId] || [], isFixture: true };
    }
  }

  async getEvidence(investigationId: string): Promise<{ data: Evidence[]; isFixture: boolean }> {
    try {
      const res = await fetch(`${this.baseUrl}/investigations/${investigationId}/evidence`, {
        cache: 'no-store',
        signal: AbortSignal.timeout(3500),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      return { data, isFixture: false };
    } catch {
      return { data: memoryEvidence[investigationId] || [], isFixture: true };
    }
  }

  async createEvidence(
    investigationId: string,
    payload: EvidenceCreate
  ): Promise<{ data: Evidence; isFixture: boolean }> {
    try {
      const res = await fetch(`${this.baseUrl}/investigations/${investigationId}/evidence`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        signal: AbortSignal.timeout(4000),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      return { data, isFixture: false };
    } catch {
      const now = new Date().toISOString();
      const ev: Evidence = {
        id: `ev-local-${Date.now()}`,
        investigation_id: investigationId,
        source_url: payload.source_url || null,
        tool_name: payload.tool_name || null,
        collection_method: payload.collection_method || 'manual_entry',
        content_type: payload.content_type || 'text/plain',
        sha256_hash: 'c5d157297e21a719c62985387431e50f53139fe0c609c25da722a4f40778f244',
        storage_ref: `local://evidence_store/${investigationId}`,
        collected_at: now,
        status: 'collected',
        raw_content: payload.raw_content || null,
      };
      if (!memoryEvidence[investigationId]) memoryEvidence[investigationId] = [];
      memoryEvidence[investigationId].unshift(ev);
      return { data: ev, isFixture: true };
    }
  }

  async getActivityLogs(
    investigationId: string
  ): Promise<{ data: ActivityLog[]; isFixture: boolean }> {
    try {
      const res = await fetch(`${this.baseUrl}/investigations/${investigationId}/activity`, {
        cache: 'no-store',
        signal: AbortSignal.timeout(3500),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      return { data, isFixture: false };
    } catch {
      return { data: memoryActivity[investigationId] || [], isFixture: true };
    }
  }

  async getGraph(investigationId: string): Promise<{ data: GraphResponse; isFixture: boolean }> {
    try {
      const res = await fetch(`${this.baseUrl}/investigations/${investigationId}/graph`, {
        cache: 'no-store',
        signal: AbortSignal.timeout(3500),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      return { data, isFixture: false };
    } catch {
      const graph = memoryGraphs[investigationId] || { nodes: [], edges: [] };
      return { data: graph, isFixture: true };
    }
  }

  async getTools(): Promise<{ data: Tool[]; isFixture: boolean }> {
    try {
      const res = await fetch(`${this.baseUrl}/tools`, {
        cache: 'no-store',
        signal: AbortSignal.timeout(3500),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      return { data, isFixture: false };
    } catch {
      return { data: FIXTURE_TOOLS, isFixture: true };
    }
  }

  async executeTool(
    payload: ToolExecuteRequest
  ): Promise<{ data: ToolExecuteResponse; isFixture: boolean }> {
    try {
      const res = await fetch(`${this.baseUrl}/tools/execute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        signal: AbortSignal.timeout(10000),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      return { data, isFixture: false };
    } catch {
      // Mock execution when backend is offline
      const mockResult: Record<string, unknown> = {
        tool: payload.tool_name,
        target: payload.parameters.domain || payload.parameters.url || payload.parameters.hostname || 'target',
        simulated: true,
        notice: 'Executed in isolated local fixture mode because backend is offline.',
        timestamp: new Date().toISOString(),
      };

      if (payload.tool_name === 'dns_lookup') {
        mockResult.records = ['93.184.216.34', '2606:2800:220:1:248:1893:25c8:1946'];
        mockResult.record_type = payload.parameters.record_type || 'A';
      } else if (payload.tool_name === 'http_metadata') {
        mockResult.status_code = 200;
        mockResult.server = 'cloudflare';
        mockResult.security_headers = { hsts: true, x_frame_options: 'SAMEORIGIN' };
      } else if (payload.tool_name === 'tls_certificate') {
        mockResult.issuer = { organizationName: "Let's Encrypt" };
        mockResult.subject_alt_names = [`DNS:${payload.parameters.hostname || 'target.com'}`];
      }

      return {
        data: {
          success: true,
          tool_name: payload.tool_name,
          result: mockResult,
          error: null,
          evidence_id: `ev-sim-${Date.now()}`,
          entities_found: 2,
        },
        isFixture: true,
      };
    }
  }
}

export const api = new ApiClient(API_BASE_URL);
