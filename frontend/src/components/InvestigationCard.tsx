'use client';

import React from 'react';
import { Investigation } from '@/types';
import { useAppStore } from '@/lib/store';
import { 
  Globe, 
  Server, 
  Mail, 
  User, 
  Building2, 
  Hash, 
  Link2, 
  FileCheck, 
  ArrowRight, 
  Trash2, 
  PauseCircle, 
  PlayCircle,
  Clock,
  Fingerprint
} from 'lucide-react';

interface Props {
  investigation: Investigation;
}

export const InvestigationCard: React.FC<Props> = ({ investigation }) => {
  const { fetchInvestigationDetails, updateInvestigation, deleteInvestigation } = useAppStore();

  const getEntityIcon = (type: string) => {
    switch (type) {
      case 'domain': return <Globe size={13} color="var(--entity-domain)" />;
      case 'ip_address': return <Server size={13} color="var(--entity-ip)" />;
      case 'email': return <Mail size={13} color="var(--entity-email)" />;
      case 'person': return <User size={13} color="var(--entity-person)" />;
      case 'organization': return <Building2 size={13} color="var(--entity-organization)" />;
      case 'file_hash': return <Hash size={13} color="var(--entity-hash)" />;
      default: return <Link2 size={13} color="var(--cyber-cyan)" />;
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'active':
        return (
          <span className="badge badge-active">
            <span className="status-dot status-dot-active" />
            Active
          </span>
        );
      case 'paused':
        return (
          <span className="badge badge-paused">
            <span className="status-dot status-dot-paused" />
            Paused
          </span>
        );
      case 'completed':
        return (
          <span className="badge badge-completed">
            Completed
          </span>
        );
      default:
        return (
          <span className="badge badge-failed">
            {status}
          </span>
        );
    }
  };

  const handleToggleStatus = (e: React.MouseEvent) => {
    e.stopPropagation();
    const newStatus = investigation.status === 'active' ? 'paused' : 'active';
    updateInvestigation(investigation.id, { status: newStatus });
  };

  const handleDelete = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (confirm(`Are you sure you want to delete investigation "${investigation.name}"?`)) {
      deleteInvestigation(investigation.id);
    }
  };

  const formattedDate = new Date(investigation.updated_at).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });

  return (
    <div 
      className="glass-panel"
      onClick={() => fetchInvestigationDetails(investigation.id)}
      style={{
        padding: '1.4rem',
        cursor: 'pointer',
        transition: 'all var(--transition-normal)',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        position: 'relative',
        overflow: 'hidden',
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.borderColor = 'rgba(0, 240, 255, 0.4)';
        e.currentTarget.style.transform = 'translateY(-2px)';
        e.currentTarget.style.boxShadow = '0 12px 30px rgba(0, 0, 0, 0.5), 0 0 15px rgba(0, 240, 255, 0.15)';
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.borderColor = 'var(--border-subtle)';
        e.currentTarget.style.transform = 'none';
        e.currentTarget.style.boxShadow = 'var(--shadow-card)';
      }}
    >
      {investigation.is_fixture && (
        <div style={{
          position: 'absolute',
          top: 0,
          right: 0,
          background: 'rgba(245, 158, 11, 0.18)',
          borderBottomLeftRadius: '8px',
          padding: '0.15rem 0.5rem',
          fontSize: '0.62rem',
          fontWeight: '700',
          color: '#fbbf24',
          letterSpacing: '0.04em',
        }}>
          DEV FIXTURE
        </div>
      )}

      <div>
        {/* Top Header: Status & Seed Type */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem', gap: '0.5rem' }}>
          {getStatusBadge(investigation.status)}
          
          <div style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '0.35rem',
            padding: '0.2rem 0.5rem',
            borderRadius: '6px',
            background: 'rgba(255, 255, 255, 0.05)',
            fontSize: '0.72rem',
            color: 'var(--text-muted)',
            fontWeight: '500',
          }}>
            {getEntityIcon(investigation.seed_entity_type)}
            <span style={{ textTransform: 'capitalize' }}>{investigation.seed_entity_type.replace('_', ' ')}</span>
          </div>
        </div>

        {/* Case Title */}
        <h3 style={{
          fontSize: '1.05rem',
          fontWeight: '600',
          color: 'var(--text-main)',
          marginBottom: '0.45rem',
          lineHeight: '1.35',
        }}>
          {investigation.name}
        </h3>

        {/* Seed Target Value */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '0.4rem',
          fontSize: '0.78rem',
          color: 'var(--cyber-cyan)',
          marginBottom: '0.75rem',
          background: 'rgba(0, 240, 255, 0.05)',
          padding: '0.3rem 0.6rem',
          borderRadius: '6px',
          width: 'fit-content',
          maxWidth: '100%',
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          whiteSpace: 'nowrap',
        }} className="font-mono">
          <Fingerprint size={13} style={{ flexShrink: 0 }} />
          <span>{investigation.seed_entity}</span>
        </div>

        {/* Description */}
        <p style={{
          fontSize: '0.8rem',
          color: 'var(--text-dim)',
          lineHeight: '1.45',
          marginBottom: '1rem',
          display: '-webkit-box',
          WebkitLineClamp: 2,
          WebkitBoxOrient: 'vertical',
          overflow: 'hidden',
        }}>
          {investigation.description || 'No detailed scope provided.'}
        </p>
      </div>

      {/* Footer Stats & Actions */}
      <div style={{
        borderTop: '1px solid var(--border-subtle)',
        paddingTop: '0.85rem',
        marginTop: '0.5rem',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
          <div style={{ display: 'flex', gap: '1rem', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            <span>
              <strong style={{ color: 'var(--text-main)' }}>{investigation.entity_count}</strong> Entities
            </span>
            <span>
              <strong style={{ color: 'var(--text-main)' }}>{investigation.evidence_count}</strong> Evidence
            </span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.7rem', color: 'var(--text-dim)' }}>
            <Clock size={11} />
            <span>{formattedDate}</span>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.5rem' }}>
          <div style={{ display: 'flex', gap: '0.35rem' }}>
            <button
              onClick={handleToggleStatus}
              className="btn btn-secondary btn-sm"
              title={investigation.status === 'active' ? 'Pause investigation' : 'Resume investigation'}
              style={{ padding: '0.3rem 0.55rem' }}
            >
              {investigation.status === 'active' ? (
                <PauseCircle size={14} color="var(--cyber-amber)" />
              ) : (
                <PlayCircle size={14} color="var(--cyber-emerald)" />
              )}
            </button>
            <button
              onClick={handleDelete}
              className="btn btn-secondary btn-sm"
              title="Delete investigation"
              style={{ padding: '0.3rem 0.55rem' }}
            >
              <Trash2 size={14} color="var(--cyber-rose)" />
            </button>
          </div>

          <button
            onClick={() => fetchInvestigationDetails(investigation.id)}
            className="btn btn-outline-cyan btn-sm"
            style={{ fontSize: '0.75rem', padding: '0.35rem 0.75rem' }}
          >
            <span>Workspace</span>
            <ArrowRight size={13} />
          </button>
        </div>
      </div>
    </div>
  );
};
