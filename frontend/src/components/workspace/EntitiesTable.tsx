'use client';

import React, { useState } from 'react';
import { Entity, SeedEntityType } from '@/types';
import { useAppStore } from '@/lib/store';
import { 
  Globe, 
  Server, 
  Mail, 
  User, 
  Building2, 
  Hash, 
  Link2, 
  Copy, 
  Check, 
  Terminal, 
  Search,
  Filter
} from 'lucide-react';

interface Props {
  entities: Entity[];
}

export const EntitiesTable: React.FC<Props> = ({ entities }) => {
  const { openToolModal } = useAppStore();
  const [filterType, setFilterType] = useState<string>('all');
  const [search, setSearch] = useState('');
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const copyToClipboard = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const getEntityIcon = (type: string) => {
    switch (type) {
      case 'domain': return <Globe size={14} color="var(--entity-domain)" />;
      case 'ip_address': return <Server size={14} color="var(--entity-ip)" />;
      case 'email': return <Mail size={14} color="var(--entity-email)" />;
      case 'person': return <User size={14} color="var(--entity-person)" />;
      case 'organization': return <Building2 size={14} color="var(--entity-organization)" />;
      case 'file_hash': return <Hash size={14} color="var(--entity-hash)" />;
      default: return <Link2 size={14} color="var(--cyber-cyan)" />;
    }
  };

  const filtered = entities.filter((e) => {
    const matchesType = filterType === 'all' || e.entity_type === filterType;
    const matchesSearch = !search.trim() || 
      e.value.toLowerCase().includes(search.toLowerCase()) ||
      (e.source && e.source.toLowerCase().includes(search.toLowerCase()));
    return matchesType && matchesSearch;
  });

  return (
    <div className="glass-panel" style={{ padding: '1.25rem' }}>
      {/* Table Toolbar */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '0.85rem',
        marginBottom: '1rem',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flex: 1, maxWidth: '400px' }}>
          <div style={{ position: 'relative', width: '100%' }}>
            <Search size={14} color="var(--text-dim)" style={{ position: 'absolute', left: '0.75rem', top: '50%', transform: 'translateY(-50%)' }} />
            <input
              type="text"
              className="input-field"
              placeholder="Filter entities by value or source..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              style={{ paddingLeft: '2.2rem', height: '36px', fontSize: '0.8rem' }}
            />
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Filter size={14} color="var(--text-dim)" />
          <select
            className="input-field"
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
            style={{ height: '36px', fontSize: '0.8rem', padding: '0.3rem 0.6rem', cursor: 'pointer' }}
          >
            <option value="all">All Types ({entities.length})</option>
            <option value="domain">Domains</option>
            <option value="ip_address">IP Addresses</option>
            <option value="email">Emails</option>
            <option value="person">Persons</option>
            <option value="organization">Organizations</option>
            <option value="file_hash">File Hashes</option>
          </select>
        </div>
      </div>

      {/* Table Container */}
      <div style={{ overflowX: 'auto' }}>
        <table className="data-table">
          <thead>
            <tr>
              <th>Type</th>
              <th>Indicator Value</th>
              <th>Provenance Source</th>
              <th>Confidence</th>
              <th>First Seen</th>
              <th style={{ textAlign: 'right' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {filtered.length > 0 ? (
              filtered.map((item) => (
                <tr key={item.id}>
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                      {getEntityIcon(item.entity_type)}
                      <span style={{ fontSize: '0.75rem', textTransform: 'capitalize', color: 'var(--text-muted)' }}>
                        {item.entity_type.replace('_', ' ')}
                      </span>
                    </div>
                  </td>
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <span className="font-mono" style={{ fontSize: '0.82rem', color: 'var(--cyber-cyan)', fontWeight: '500' }}>
                        {item.value}
                      </span>
                      <button
                        onClick={() => copyToClipboard(item.value, item.id)}
                        className="btn btn-secondary btn-sm"
                        style={{ padding: '0.2rem', borderRadius: '4px' }}
                        title="Copy indicator value"
                      >
                        {copiedId === item.id ? <Check size={12} color="var(--cyber-emerald)" /> : <Copy size={12} />}
                      </button>
                    </div>
                  </td>
                  <td>
                    <span style={{
                      fontSize: '0.75rem',
                      padding: '0.2rem 0.5rem',
                      borderRadius: '4px',
                      background: 'rgba(255, 255, 255, 0.05)',
                      color: 'var(--text-muted)',
                    }}>
                      {item.source || 'user_input'}
                    </span>
                  </td>
                  <td>
                    <span className={`badge ${item.confidence === 'confirmed' || item.confidence === 'high' ? 'badge-active' : 'badge-paused'}`} style={{ fontSize: '0.68rem' }}>
                      {item.confidence}
                    </span>
                  </td>
                  <td style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>
                    {new Date(item.first_seen).toLocaleDateString('en-US', {
                      month: 'short',
                      day: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </td>
                  <td style={{ textAlign: 'right' }}>
                    <button
                      onClick={() => openToolModal()}
                      className="btn btn-secondary btn-sm"
                      style={{ fontSize: '0.72rem', padding: '0.25rem 0.55rem' }}
                      title="Run OSINT tool against this entity"
                    >
                      <Terminal size={12} color="var(--cyber-cyan)" />
                      <span>Pivot</span>
                    </button>
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={6} style={{ textAlign: 'center', padding: '2.5rem', color: 'var(--text-dim)' }}>
                  No entities match the current criteria.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
