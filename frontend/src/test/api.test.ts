import { describe, it, expect, vi, beforeEach } from 'vitest';
import { api } from '@/lib/api';

describe('ZAPRICA API Client & Fixture Isolation', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('gracefully falls back to labeled dev fixtures when backend is unreachable', async () => {
    // When fetch fails, api client falls back to fixtures with isFixture: true
    global.fetch = vi.fn().mockRejectedValue(new Error('Connection refused'));

    const res = await api.getInvestigations();
    expect(res.isFixture).toBe(true);
    expect(res.data.investigations.length).toBeGreaterThan(0);
    expect(res.data.investigations[0].is_fixture).toBe(true);
  });

  it('returns live data with isFixture: false when backend responds successfully', async () => {
    const mockLiveCases = [
      {
        id: 'inv-live-100',
        name: 'Live Cyber Threat Assessment',
        description: 'Test case from real backend',
        seed_entity: 'threat.test',
        seed_entity_type: 'domain',
        status: 'active',
        authorized_use_confirmed: true,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        entity_count: 5,
        evidence_count: 2,
      },
    ];

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ investigations: mockLiveCases, total: 1 }),
    } as Response);

    const res = await api.getInvestigations();
    expect(res.isFixture).toBe(false);
    expect(res.data.investigations.length).toBe(1);
    expect(res.data.investigations[0].id).toBe('inv-live-100');
  });

  it('can create an investigation in fixture mode and returns populated record', async () => {
    global.fetch = vi.fn().mockRejectedValue(new Error('Offline'));

    const created = await api.createInvestigation({
      name: 'Test Operation Phoenix',
      seed_entity: 'phoenix-recon.net',
      seed_entity_type: 'domain',
      authorized_use_confirmed: true,
    });

    expect(created.isFixture).toBe(true);
    expect(created.data.name).toBe('Test Operation Phoenix');
    expect(created.data.seed_entity).toBe('phoenix-recon.net');
    expect(created.data.status).toBe('active');
  });

  it('executes tools and returns simulated result with entities count when offline', async () => {
    global.fetch = vi.fn().mockRejectedValue(new Error('Offline'));

    const execRes = await api.executeTool({
      tool_name: 'dns_lookup',
      parameters: { domain: 'target.net', record_type: 'A' },
    });

    expect(execRes.isFixture).toBe(true);
    expect(execRes.data.success).toBe(true);
    expect(execRes.data.tool_name).toBe('dns_lookup');
    expect(execRes.data.result).toHaveProperty('records');
  });
});
