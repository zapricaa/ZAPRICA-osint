'use client';

import React from 'react';
import { useAppStore, WorkspaceTab } from '@/lib/store';
import { IntelligenceGraph } from './graph/IntelligenceGraph';
import { EntitiesTable } from './workspace/EntitiesTable';
import { EvidenceLedger } from './workspace/EvidenceLedger';
import { ActivityTimeline } from './workspace/ActivityTimeline';
import { ToolConsole } from './workspace/ToolConsole';
import { 
  ArrowLeft, 
  Share2, 
  Network, 
  Table, 
  ShieldCheck, 
  Clock, 
  Terminal, 
  PauseCircle, 
  PlayCircle,
  Globe,
  Server,
  Fingerprint,
  RotateCw,
  Trash2
} from 'lucide-react';

export const InvestigationWorkspace: React.FC = () => {
  const { 
    activeInvestigation, 
    activeTab, 
    setActiveTab, 
    fetchInvestigationDetails,
    updateInvestigation,
    deleteInvestigation,
    entities,
    evidence,
    activityLogs,
    isLoading
  } = useAppStore();

  if (!activeInvestigation) return null;

  const handleToggleStatus = () => {
    const nextStatus = activeInvestigation.status === 'active' ? 'paused' : 'active';
    updateInvestigation(activeInvestigation.id, { status: nextStatus });
  };

  const handleDelete = () => {
    if (confirm(`Are you sure you want to delete investigation "${activeInvestigation.name}"?`)) {
      deleteInvestigation(activeInvestigation.id);
    }
  };

  const tabs: { id: WorkspaceTab; label: string; icon: React.ReactNode; count?: number }[] = [
    { id: 'graph', label: 'Intelligence Graph', icon: <Network size={15} /> },
    { id: 'entities', label: 'Correlated Entities', icon: <Table size={15} />, count: entities.length },
    { id: 'evidence', label: 'Cryptographic Evidence', icon: <ShieldCheck size={15} />, count: evidence.length },
    { id: 'activity', label: 'Audit Timeline', icon: <Clock size={15} />, count: activityLogs.length },
    { id: 'tools', label: 'OSINT Tool Console', icon: <Terminal size={15} /> },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', animation: 'fadeIn 200ms ease' }}>
      {/* Top Workspace Bar */}
      <div className="glass-panel" style={{ padding: '1.25rem 1.5rem' }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '1rem',
          marginBottom: '0.85rem',
        }}>
          {/* Back button & Title */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <button
              onClick={() => useAppStore.setState({ activeInvestigation: null })}
              className="btn btn-secondary btn-sm"
              style={{ padding: '0.4rem 0.65rem' }}
              title="Return to investigations dashboard"
            >
              <ArrowLeft size={16} />
              <span>Back</span>
            </button>

            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
                <h1 style={{ fontSize: '1.35rem', fontWeight: '700', color: 'var(--text-main)' }}>
                  {activeInvestigation.name}
                </h1>
                <span className={`badge ${activeInvestigation.status === 'active' ? 'badge-active' : 'badge-paused'}`}>
                  {activeInvestigation.status}
                </span>
                {activeInvestigation.is_fixture && (
                  <span className="badge badge-fixture">
                    DEV FIXTURE
                  </span>
                )}
              </div>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
                {activeInvestigation.description || 'Target intelligence exploration & correlation'}
              </p>
            </div>
          </div>

          {/* Action buttons */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
            <button
              onClick={() => fetchInvestigationDetails(activeInvestigation.id)}
              className="btn btn-secondary btn-sm"
              disabled={isLoading}
              title="Refresh case data"
            >
              <RotateCw size={14} className={isLoading ? 'animate-spin' : ''} />
              <span>Sync</span>
            </button>

            <button
              onClick={handleToggleStatus}
              className="btn btn-secondary btn-sm"
              title={activeInvestigation.status === 'active' ? 'Pause investigation' : 'Resume investigation'}
            >
              {activeInvestigation.status === 'active' ? (
                <>
                  <PauseCircle size={14} color="var(--cyber-amber)" />
                  <span>Pause</span>
                </>
              ) : (
                <>
                  <PlayCircle size={14} color="var(--cyber-emerald)" />
                  <span>Resume</span>
                </>
              )}
            </button>

            <button
              onClick={handleDelete}
              className="btn btn-danger btn-sm"
              title="Delete case"
            >
              <Trash2 size={14} />
              <span>Delete</span>
            </button>
          </div>
        </div>

        {/* Seed Target & Entity Pills */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '1rem',
          fontSize: '0.78rem',
          paddingTop: '0.75rem',
          borderTop: '1px solid var(--border-subtle)',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: 'var(--cyber-cyan)' }}>
            <Fingerprint size={14} />
            <span style={{ color: 'var(--text-muted)' }}>Target Seed:</span>
            <strong className="font-mono">{activeInvestigation.seed_entity}</strong>
            <span style={{
              fontSize: '0.68rem',
              padding: '0.1rem 0.4rem',
              background: 'rgba(0, 240, 255, 0.1)',
              borderRadius: '4px',
              textTransform: 'uppercase',
            }}>
              {activeInvestigation.seed_entity_type}
            </span>
          </div>

          <div style={{ color: 'var(--border-subtle)' }}>•</div>

          <div style={{ color: 'var(--text-muted)' }}>
            Correlation Count: <strong style={{ color: 'var(--text-main)' }}>{entities.length}</strong> Entities
          </div>

          <div style={{ color: 'var(--border-subtle)' }}>•</div>

          <div style={{ color: 'var(--text-muted)' }}>
            Evidence Anchors: <strong style={{ color: 'var(--text-main)' }}>{evidence.length}</strong> Stamped
          </div>
        </div>
      </div>

      {/* Tabs Navigation */}
      <div className="glass-panel" style={{ padding: '0', overflow: 'hidden' }}>
        <div className="tabs-nav">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`tab-btn ${activeTab === tab.id ? 'active' : ''}`}
            >
              {tab.icon}
              <span>{tab.label}</span>
              {tab.count !== undefined && (
                <span style={{
                  fontSize: '0.68rem',
                  padding: '0.1rem 0.45rem',
                  borderRadius: '9999px',
                  background: activeTab === tab.id ? 'rgba(0, 240, 255, 0.2)' : 'rgba(255, 255, 255, 0.08)',
                  color: activeTab === tab.id ? 'var(--cyber-cyan)' : 'var(--text-muted)',
                  fontWeight: '600',
                }}>
                  {tab.count}
                </span>
              )}
            </button>
          ))}
        </div>

        {/* Tab Content Panes */}
        <div style={{ padding: '1.25rem' }}>
          {activeTab === 'graph' && <IntelligenceGraph />}
          {activeTab === 'entities' && <EntitiesTable entities={entities} />}
          {activeTab === 'evidence' && (
            <EvidenceLedger evidence={evidence} investigationId={activeInvestigation.id} />
          )}
          {activeTab === 'activity' && <ActivityTimeline activityLogs={activityLogs} />}
          {activeTab === 'tools' && (
            <ToolConsole 
              investigationId={activeInvestigation.id} 
              seedEntity={activeInvestigation.seed_entity} 
            />
          )}
        </div>
      </div>
    </div>
  );
};
