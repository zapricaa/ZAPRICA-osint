'use client';

import React, { useEffect } from 'react';
import { useAppStore } from '@/lib/store';
import { 
  ShieldAlert, 
  PlusCircle, 
  Activity, 
  Terminal, 
  Search,
  Database,
  CheckCircle2,
  AlertTriangle
} from 'lucide-react';

export const Header: React.FC = () => {
  const { 
    isLiveBackend, 
    health, 
    checkSystemHealth, 
    openCreateModal, 
    openToolModal,
    searchQuery,
    setSearchQuery,
    activeInvestigation,
    setActiveTab,
  } = useAppStore();

  useEffect(() => {
    checkSystemHealth();
    const interval = setInterval(checkSystemHealth, 20000);
    return () => clearInterval(interval);
  }, [checkSystemHealth]);

  return (
    <header style={{
      borderBottom: '1px solid var(--border-subtle)',
      background: 'rgba(6, 9, 17, 0.85)',
      backdropFilter: 'blur(16px)',
      position: 'sticky',
      top: 0,
      zIndex: 100,
    }}>
      <div className="container" style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        height: '70px',
        gap: '1rem',
      }}>
        {/* Brand */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.85rem' }}>
          <div style={{
            width: '38px',
            height: '38px',
            borderRadius: '10px',
            background: 'linear-gradient(135deg, rgba(0, 240, 255, 0.2) 0%, rgba(139, 92, 246, 0.2) 100%)',
            border: '1px solid var(--border-glow)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 0 15px rgba(0, 240, 255, 0.3)',
          }}>
            <ShieldAlert size={22} color="var(--cyber-cyan)" />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span style={{ 
                fontSize: '1.25rem', 
                fontWeight: '800', 
                letterSpacing: '0.08em',
                background: 'linear-gradient(135deg, #00f0ff 0%, #38bdf8 50%, #8b5cf6 100%)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
              }}>
                ZAPRICA
              </span>
              <span style={{
                fontSize: '0.65rem',
                padding: '0.15rem 0.45rem',
                borderRadius: '4px',
                background: 'rgba(255, 255, 255, 0.08)',
                color: 'var(--text-muted)',
                fontWeight: '600',
                letterSpacing: '0.05em',
              }}>
                OSINT PLATFORM
              </span>
            </div>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)', letterSpacing: '0.02em' }}>
              Autonomous AI Intelligence & Evidence Provenance
            </div>
          </div>
        </div>

        {/* Global Search */}
        <div style={{ flex: 1, maxWidth: '420px', position: 'relative' }}>
          <Search size={16} color="var(--text-dim)" style={{
            position: 'absolute',
            left: '0.85rem',
            top: '50%',
            transform: 'translateY(-50%)',
          }} />
          <input
            type="text"
            className="input-field"
            placeholder="Search cases, seed targets, indicators..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{ paddingLeft: '2.4rem', height: '38px' }}
          />
        </div>

        {/* Status Indicators & Actions */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.85rem' }}>
          {/* Backend Connection Status Badge */}
          <div 
            title={isLiveBackend ? `Connected to FastAPI Backend (${health?.database || 'sqlite'})` : 'Backend offline. Running with labeled dev fixtures.'}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              padding: '0.35rem 0.75rem',
              borderRadius: '8px',
              background: isLiveBackend ? 'rgba(16, 185, 129, 0.1)' : 'rgba(245, 158, 11, 0.12)',
              border: `1px solid ${isLiveBackend ? 'rgba(16, 185, 129, 0.3)' : 'rgba(245, 158, 11, 0.4)'}`,
              fontSize: '0.75rem',
              fontWeight: '500',
            }}
          >
            <div className={`status-dot ${isLiveBackend ? 'status-dot-active' : 'status-dot-paused'}`} />
            {isLiveBackend ? (
              <span style={{ color: 'var(--cyber-emerald)', display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                <CheckCircle2 size={13} />
                LIVE API (8000)
              </span>
            ) : (
              <span style={{ color: 'var(--cyber-amber)', display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                <AlertTriangle size={13} />
                FIXTURE MODE
              </span>
            )}
          </div>

          {/* Tool Runner Modal Button */}
          <button
            onClick={() => openToolModal()}
            className="btn btn-secondary btn-sm"
            style={{ height: '38px', gap: '0.4rem' }}
            title="Launch MCP OSINT Tool Console"
          >
            <Terminal size={15} color="var(--cyber-cyan)" />
            <span>Tool Console</span>
          </button>

          {/* New Investigation Button */}
          <button
            onClick={openCreateModal}
            className="btn btn-primary btn-sm"
            style={{ height: '38px', gap: '0.4rem' }}
          >
            <PlusCircle size={16} />
            <span>New Investigation</span>
          </button>
        </div>
      </div>
    </header>
  );
};
