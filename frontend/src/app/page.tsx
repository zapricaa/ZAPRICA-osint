'use client';

import React, { useEffect } from 'react';
import { useAppStore } from '@/lib/store';
import { Header } from '@/components/Header';
import { StatsCards } from '@/components/StatsCards';
import { InvestigationList } from '@/components/InvestigationList';
import { InvestigationWorkspace } from '@/components/InvestigationWorkspace';
import { CaseCreationModal } from '@/components/CaseCreationModal';
import { ToolRunnerModal } from '@/components/ToolRunnerModal';
import { AlertCircle, X } from 'lucide-react';

export default function Home() {
  const { 
    activeInvestigation, 
    errorMessage, 
    clearError, 
    fetchInvestigations, 
    checkSystemHealth 
  } = useAppStore();

  useEffect(() => {
    checkSystemHealth();
    fetchInvestigations();
  }, [checkSystemHealth, fetchInvestigations]);

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* Navigation Header */}
      <Header />

      {/* Global Error Banner */}
      {errorMessage && (
        <div style={{
          background: 'rgba(244, 63, 94, 0.15)',
          borderBottom: '1px solid rgba(244, 63, 94, 0.35)',
          padding: '0.65rem 1.5rem',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', color: 'var(--cyber-rose)', fontSize: '0.82rem' }}>
            <AlertCircle size={16} />
            <span>{errorMessage}</span>
          </div>
          <button 
            onClick={clearError}
            className="btn btn-secondary btn-sm"
            style={{ padding: '0.2rem', borderRadius: '4px' }}
          >
            <X size={14} />
          </button>
        </div>
      )}

      {/* Main Content Area */}
      <main style={{ flex: 1, padding: '2rem 0' }}>
        <div className="container">
          {activeInvestigation ? (
            <InvestigationWorkspace />
          ) : (
            <div>
              {/* Metrics & Status */}
              <StatsCards />

              {/* Case Listing & Filtering */}
              <InvestigationList />
            </div>
          )}
        </div>
      </main>

      {/* Modals */}
      <CaseCreationModal />
      <ToolRunnerModal />

      {/* Footer */}
      <footer style={{
        borderTop: '1px solid var(--border-subtle)',
        padding: '1.25rem 0',
        background: 'rgba(6, 9, 17, 0.6)',
        marginTop: 'auto',
      }}>
        <div className="container" style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '1rem',
          fontSize: '0.75rem',
          color: 'var(--text-dim)',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span style={{ fontWeight: '700', color: 'var(--text-muted)' }}>ZAPRICA</span>
            <span>•</span>
            <span>AI-Powered Autonomous OSINT Investigation Platform</span>
          </div>
          <div>
            DPDP Act Section 3(c)(ii) Compliant • Immutable SHA-256 Ledger • MCP JSON-RPC 2.0
          </div>
        </div>
      </footer>
    </div>
  );
}
