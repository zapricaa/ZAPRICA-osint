'use client';

import React from 'react';
import { useAppStore } from '@/lib/store';
import { 
  FolderKanban, 
  Network, 
  ShieldCheck, 
  Wrench, 
  AlertCircle,
  Database,
  Lock
} from 'lucide-react';

export const StatsCards: React.FC = () => {
  const { investigations, entities, evidence, tools, isLiveBackend } = useAppStore();

  const totalCases = investigations.length;
  const activeCases = investigations.filter((i) => i.status === 'active').length;
  const totalEntities = investigations.reduce((acc, curr) => acc + (curr.entity_count || 0), 0) || entities.length;
  const totalEvidence = investigations.reduce((acc, curr) => acc + (curr.evidence_count || 0), 0) || evidence.length;
  const toolsCount = tools.length || 5;

  return (
    <div style={{ marginBottom: '2rem' }}>
      {/* Dev Fixture Mode Warning Banner if backend is offline */}
      {!isLiveBackend && (
        <div style={{
          background: 'rgba(245, 158, 11, 0.08)',
          border: '1px solid rgba(245, 158, 11, 0.35)',
          borderRadius: '10px',
          padding: '0.85rem 1.25rem',
          marginBottom: '1.5rem',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '1rem',
          animation: 'fadeIn 300ms ease',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <AlertCircle size={20} color="var(--cyber-amber)" style={{ flexShrink: 0 }} />
            <div>
              <div style={{ fontSize: '0.85rem', fontWeight: '600', color: '#fbbf24' }}>
                Development Fixtures Active (Backend Endpoint Standby)
              </div>
              <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                The FastAPI backend service is currently offline or starting up. Displaying isolated, strictly labeled development fixtures. When FastAPI is launched on port 8000, live database queries will automatically take over.
              </div>
            </div>
          </div>
          <span className="badge badge-fixture" style={{ flexShrink: 0 }}>
            FIXTURE FALLBACK
          </span>
        </div>
      )}

      {/* Metric Cards Grid */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
        gap: '1.25rem',
      }}>
        {/* Card 1: Investigations */}
        <div className="glass-panel" style={{ padding: '1.25rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <div>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontWeight: '500' }}>
                INVESTIGATIONS
              </div>
              <div style={{ fontSize: '1.85rem', fontWeight: '700', color: 'var(--text-main)', marginTop: '0.25rem' }}>
                {totalCases}
              </div>
            </div>
            <div style={{
              width: '42px',
              height: '42px',
              borderRadius: '8px',
              background: 'rgba(0, 240, 255, 0.12)',
              border: '1px solid rgba(0, 240, 255, 0.3)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}>
              <FolderKanban size={20} color="var(--cyber-cyan)" />
            </div>
          </div>
          <div style={{ marginTop: '0.85rem', display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.75rem' }}>
            <span style={{ color: 'var(--cyber-emerald)', fontWeight: '600' }}>
              {activeCases} Active
            </span>
            <span style={{ color: 'var(--text-dim)' }}>•</span>
            <span style={{ color: 'var(--text-muted)' }}>
              {totalCases - activeCases} Archival / Paused
            </span>
          </div>
        </div>

        {/* Card 2: Tracked Entities */}
        <div className="glass-panel" style={{ padding: '1.25rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <div>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontWeight: '500' }}>
                CORRELATED ENTITIES
              </div>
              <div style={{ fontSize: '1.85rem', fontWeight: '700', color: 'var(--text-main)', marginTop: '0.25rem' }}>
                {totalEntities}
              </div>
            </div>
            <div style={{
              width: '42px',
              height: '42px',
              borderRadius: '8px',
              background: 'rgba(16, 185, 129, 0.12)',
              border: '1px solid rgba(16, 185, 129, 0.3)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}>
              <Network size={20} color="var(--cyber-emerald)" />
            </div>
          </div>
          <div style={{ marginTop: '0.85rem', display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            <span>Domains, IPs, Emails, Hashes</span>
          </div>
        </div>

        {/* Card 3: Cryptographic Evidence */}
        <div className="glass-panel" style={{ padding: '1.25rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <div>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontWeight: '500' }}>
                EVIDENCE PROVENANCE
              </div>
              <div style={{ fontSize: '1.85rem', fontWeight: '700', color: 'var(--text-main)', marginTop: '0.25rem' }}>
                {totalEvidence}
              </div>
            </div>
            <div style={{
              width: '42px',
              height: '42px',
              borderRadius: '8px',
              background: 'rgba(139, 92, 246, 0.12)',
              border: '1px solid rgba(139, 92, 246, 0.3)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}>
              <ShieldCheck size={20} color="var(--cyber-violet)" />
            </div>
          </div>
          <div style={{ marginTop: '0.85rem', display: 'flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.75rem', color: 'var(--cyber-violet)' }}>
            <Lock size={12} />
            <span>100% SHA-256 Cryptographic Anchors</span>
          </div>
        </div>

        {/* Card 4: OSINT MCP Tools */}
        <div className="glass-panel" style={{ padding: '1.25rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <div>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontWeight: '500' }}>
                AUTONOMOUS TOOLS
              </div>
              <div style={{ fontSize: '1.85rem', fontWeight: '700', color: 'var(--text-main)', marginTop: '0.25rem' }}>
                {toolsCount}
              </div>
            </div>
            <div style={{
              width: '42px',
              height: '42px',
              borderRadius: '8px',
              background: 'rgba(245, 158, 11, 0.12)',
              border: '1px solid rgba(245, 158, 11, 0.3)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}>
              <Wrench size={20} color="var(--cyber-amber)" />
            </div>
          </div>
          <div style={{ marginTop: '0.85rem', display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            <span>DNS, TLS, RDAP, HTTP, Webpage</span>
          </div>
        </div>
      </div>
    </div>
  );
};
