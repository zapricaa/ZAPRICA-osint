'use client';

import React, { useEffect, useMemo } from 'react';
import { useAppStore } from '@/lib/store';
import { InvestigationCard } from './InvestigationCard';
import { 
  Filter, 
  RotateCw, 
  FolderPlus, 
  SearchX, 
  Layers
} from 'lucide-react';

export const InvestigationList: React.FC = () => {
  const { 
    investigations, 
    fetchInvestigations, 
    isLoading, 
    statusFilter, 
    setStatusFilter, 
    searchQuery,
    openCreateModal 
  } = useAppStore();

  useEffect(() => {
    fetchInvestigations();
  }, [fetchInvestigations]);

  // Client-side text search filtering
  const filteredInvestigations = useMemo(() => {
    let result = investigations;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      result = result.filter(
        (inv) =>
          inv.name.toLowerCase().includes(q) ||
          (inv.description && inv.description.toLowerCase().includes(q)) ||
          inv.seed_entity.toLowerCase().includes(q) ||
          inv.seed_entity_type.toLowerCase().includes(q)
      );
    }
    return result;
  }, [investigations, searchQuery]);

  const filterTabs = [
    { label: 'All Cases', value: null },
    { label: 'Active', value: 'active' },
    { label: 'Paused', value: 'paused' },
    { label: 'Completed', value: 'completed' },
  ];

  return (
    <div>
      {/* List Controls & Filters */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '1rem',
        marginBottom: '1.5rem',
      }}>
        {/* Status Filter Pills */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '0.4rem',
          background: 'rgba(11, 17, 30, 0.6)',
          padding: '0.3rem',
          borderRadius: '10px',
          border: '1px solid var(--border-subtle)',
        }}>
          {filterTabs.map((tab) => (
            <button
              key={tab.label}
              onClick={() => setStatusFilter(tab.value)}
              className="btn btn-sm"
              style={{
                borderRadius: '7px',
                background: statusFilter === tab.value ? 'rgba(0, 240, 255, 0.15)' : 'transparent',
                color: statusFilter === tab.value ? 'var(--cyber-cyan)' : 'var(--text-muted)',
                fontWeight: statusFilter === tab.value ? '600' : '400',
                border: `1px solid ${statusFilter === tab.value ? 'rgba(0, 240, 255, 0.3)' : 'transparent'}`,
              }}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Right side controls: Count & Refresh */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.85rem' }}>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-dim)' }}>
            Showing <strong style={{ color: 'var(--text-main)' }}>{filteredInvestigations.length}</strong> cases
          </span>

          <button
            onClick={() => fetchInvestigations()}
            className="btn btn-secondary btn-sm"
            style={{ padding: '0.35rem 0.65rem' }}
            title="Refresh from API"
            disabled={isLoading}
          >
            <RotateCw size={14} className={isLoading ? 'animate-spin' : ''} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Grid of Cards or Empty State */}
      {filteredInvestigations.length > 0 ? (
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))',
          gap: '1.25rem',
        }}>
          {filteredInvestigations.map((inv) => (
            <InvestigationCard key={inv.id} investigation={inv} />
          ))}
        </div>
      ) : (
        /* Empty State */
        <div className="glass-panel" style={{
          padding: '4rem 2rem',
          textAlign: 'center',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
        }}>
          <div style={{
            width: '64px',
            height: '64px',
            borderRadius: '50%',
            background: 'rgba(255, 255, 255, 0.03)',
            border: '1px solid var(--border-subtle)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            marginBottom: '1.25rem',
          }}>
            {searchQuery ? (
              <SearchX size={28} color="var(--text-dim)" />
            ) : (
              <Layers size={28} color="var(--cyber-cyan)" />
            )}
          </div>

          <h3 style={{ fontSize: '1.15rem', fontWeight: '600', color: 'var(--text-main)', marginBottom: '0.5rem' }}>
            {searchQuery ? 'No matching investigations found' : 'No investigations initiated yet'}
          </h3>

          <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', maxWidth: '420px', marginBottom: '1.5rem', lineHeight: '1.5' }}>
            {searchQuery 
              ? `No records found matching "${searchQuery}". Try adjusting your keywords or clearing the filter.`
              : 'Start your first autonomous OSINT intelligence case by providing a target domain, IP, email, or hash.'}
          </p>

          <button onClick={openCreateModal} className="btn btn-primary">
            <FolderPlus size={16} />
            <span>Create New Investigation</span>
          </button>
        </div>
      )}
    </div>
  );
};
