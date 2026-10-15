'use client';

import React, { useState, useEffect } from 'react';
import { useAppStore } from '@/lib/store';
import { Tool, ToolExecuteResponse } from '@/types';
import { 
  Terminal, 
  Play, 
  CheckCircle2, 
  AlertCircle, 
  Loader2, 
  Sparkles, 
  Hash, 
  Globe, 
  Server, 
  Lock
} from 'lucide-react';

interface Props {
  investigationId: string;
  seedEntity: string;
}

export const ToolConsole: React.FC<Props> = ({ investigationId, seedEntity }) => {
  const { tools, fetchTools, executeTool, isSaving } = useAppStore();

  const [selectedToolName, setSelectedToolName] = useState<string>('dns_lookup');
  const [params, setParams] = useState<Record<string, string>>({});
  const [lastResult, setLastResult] = useState<ToolExecuteResponse | null>(null);

  useEffect(() => {
    fetchTools();
  }, [fetchTools]);

  const activeTool = tools.find((t) => t.name === selectedToolName);

  // Initialize or update parameters based on selected tool
  useEffect(() => {
    if (!activeTool) return;
    const initial: Record<string, string> = {};
    if (selectedToolName === 'dns_lookup') {
      initial.domain = seedEntity.replace(/^https?:\/\//, '').split('/')[0];
      initial.record_type = 'A';
    } else if (selectedToolName === 'http_metadata') {
      initial.url = seedEntity.startsWith('http') ? seedEntity : `https://${seedEntity}`;
    } else if (selectedToolName === 'tls_certificate') {
      initial.hostname = seedEntity.replace(/^https?:\/\//, '').split('/')[0];
      initial.port = '443';
    } else if (selectedToolName === 'rdap_lookup') {
      initial.domain = seedEntity.replace(/^https?:\/\//, '').split('/')[0];
    } else if (selectedToolName === 'webpage_metadata') {
      initial.url = seedEntity.startsWith('http') ? seedEntity : `https://${seedEntity}`;
    }
    setParams(initial);
  }, [selectedToolName, seedEntity, activeTool]);

  const handleRun = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeTool) return;

    // Convert types if needed (e.g., port to number)
    const formattedParams: Record<string, unknown> = { ...params };
    if (formattedParams.port) {
      formattedParams.port = parseInt(formattedParams.port as string, 10) || 443;
    }

    const res = await executeTool({
      tool_name: selectedToolName,
      parameters: formattedParams,
      investigation_id: investigationId,
    });

    if (res) {
      setLastResult(res);
    }
  };

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1.8fr', gap: '1.5rem', alignItems: 'start' }}>
      {/* Tool Configuration Panel */}
      <div className="glass-panel" style={{ padding: '1.5rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem', marginBottom: '1.25rem' }}>
          <div style={{
            width: '32px',
            height: '32px',
            borderRadius: '8px',
            background: 'rgba(0, 240, 255, 0.12)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}>
            <Terminal size={17} color="var(--cyber-cyan)" />
          </div>
          <div>
            <h3 style={{ fontSize: '1rem', fontWeight: '700', color: 'var(--text-main)' }}>
              MCP Tool Execution Console
            </h3>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>
              Dispatch standardized JSON-RPC tools to enrich this investigation
            </p>
          </div>
        </div>

        <form onSubmit={handleRun}>
          {/* Tool Selector */}
          <div style={{ marginBottom: '1.25rem' }}>
            <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: '600', color: 'var(--text-muted)', marginBottom: '0.4rem' }}>
              Select Autonomous Tool
            </label>
            <select
              className="input-field"
              value={selectedToolName}
              onChange={(e) => setSelectedToolName(e.target.value)}
              disabled={isSaving}
              style={{ cursor: 'pointer' }}
            >
              <option value="dns_lookup">DNS Lookup (A, AAAA, MX, NS, TXT)</option>
              <option value="http_metadata">HTTP Response Headers & Security Posture</option>
              <option value="tls_certificate">TLS/SSL x509 Certificate & SANs</option>
              <option value="rdap_lookup">RDAP Registration & Contacts</option>
              <option value="webpage_metadata">Webpage Title, OpenGraph & Linked Domains</option>
            </select>
          </div>

          {/* Description */}
          {activeTool && (
            <div style={{
              background: 'rgba(255, 255, 255, 0.03)',
              borderRadius: '6px',
              padding: '0.75rem',
              fontSize: '0.75rem',
              color: 'var(--text-muted)',
              marginBottom: '1.25rem',
              border: '1px solid var(--border-subtle)',
              lineHeight: '1.45',
            }}>
              {activeTool.description}
            </div>
          )}

          {/* Dynamic Parameters */}
          {selectedToolName === 'dns_lookup' && (
            <>
              <div style={{ marginBottom: '1rem' }}>
                <label style={{ display: 'block', fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: '0.35rem' }}>
                  Domain Name *
                </label>
                <input
                  type="text"
                  className="input-field font-mono"
                  value={params.domain || ''}
                  onChange={(e) => setParams({ ...params, domain: e.target.value })}
                  disabled={isSaving}
                  required
                />
              </div>
              <div style={{ marginBottom: '1.25rem' }}>
                <label style={{ display: 'block', fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: '0.35rem' }}>
                  Record Type
                </label>
                <select
                  className="input-field"
                  value={params.record_type || 'A'}
                  onChange={(e) => setParams({ ...params, record_type: e.target.value })}
                  disabled={isSaving}
                >
                  <option value="A">A (IPv4 Address)</option>
                  <option value="AAAA">AAAA (IPv6 Address)</option>
                  <option value="MX">MX (Mail Exchange)</option>
                  <option value="NS">NS (Name Server)</option>
                  <option value="TXT">TXT (Text Records)</option>
                  <option value="CNAME">CNAME (Canonical Name)</option>
                  <option value="SOA">SOA (Start of Authority)</option>
                </select>
              </div>
            </>
          )}

          {selectedToolName === 'http_metadata' && (
            <div style={{ marginBottom: '1.25rem' }}>
              <label style={{ display: 'block', fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: '0.35rem' }}>
                URL to Inspect *
              </label>
              <input
                type="text"
                className="input-field font-mono"
                value={params.url || ''}
                onChange={(e) => setParams({ ...params, url: e.target.value })}
                disabled={isSaving}
                required
              />
            </div>
          )}

          {selectedToolName === 'tls_certificate' && (
            <div style={{ display: 'grid', gridTemplateColumns: '3fr 1fr', gap: '0.75rem', marginBottom: '1.25rem' }}>
              <div>
                <label style={{ display: 'block', fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: '0.35rem' }}>
                  Hostname *
                </label>
                <input
                  type="text"
                  className="input-field font-mono"
                  value={params.hostname || ''}
                  onChange={(e) => setParams({ ...params, hostname: e.target.value })}
                  disabled={isSaving}
                  required
                />
              </div>
              <div>
                <label style={{ display: 'block', fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: '0.35rem' }}>
                  Port
                </label>
                <input
                  type="number"
                  className="input-field font-mono"
                  value={params.port || '443'}
                  onChange={(e) => setParams({ ...params, port: e.target.value })}
                  disabled={isSaving}
                />
              </div>
            </div>
          )}

          {selectedToolName === 'rdap_lookup' && (
            <div style={{ marginBottom: '1.25rem' }}>
              <label style={{ display: 'block', fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: '0.35rem' }}>
                Domain Name *
              </label>
              <input
                type="text"
                className="input-field font-mono"
                value={params.domain || ''}
                onChange={(e) => setParams({ ...params, domain: e.target.value })}
                disabled={isSaving}
                required
              />
            </div>
          )}

          {selectedToolName === 'webpage_metadata' && (
            <div style={{ marginBottom: '1.25rem' }}>
              <label style={{ display: 'block', fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: '0.35rem' }}>
                Target URL *
              </label>
              <input
                type="text"
                className="input-field font-mono"
                value={params.url || ''}
                onChange={(e) => setParams({ ...params, url: e.target.value })}
                disabled={isSaving}
                required
              />
            </div>
          )}

          <button
            type="submit"
            className="btn btn-primary"
            disabled={isSaving}
            style={{ width: '100%', gap: '0.5rem' }}
          >
            {isSaving ? (
              <>
                <Loader2 size={16} className="animate-spin" />
                <span>Executing OSINT Tool...</span>
              </>
            ) : (
              <>
                <Play size={15} />
                <span>Execute & Correlate Graph</span>
              </>
            )}
          </button>
        </form>
      </div>

      {/* Execution Results Output Console */}
      <div className="glass-panel" style={{ padding: '1.5rem', display: 'flex', flexDirection: 'column', height: '100%' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
          <h3 style={{ fontSize: '0.95rem', fontWeight: '700', color: 'var(--text-main)' }}>
            Execution Telemetry & Output
          </h3>
          {lastResult && (
            <span className={`badge ${lastResult.success ? 'badge-active' : 'badge-failed'}`}>
              {lastResult.success ? 'Execution Success' : 'Execution Failed'}
            </span>
          )}
        </div>

        {lastResult ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem', flex: 1 }}>
            {/* Stats summary banner */}
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '1.25rem',
              background: 'rgba(0, 240, 255, 0.05)',
              border: '1px solid rgba(0, 240, 255, 0.2)',
              borderRadius: '8px',
              padding: '0.75rem 1rem',
              fontSize: '0.78rem',
            }}>
              <div>
                <span style={{ color: 'var(--text-muted)' }}>Entities Extracted: </span>
                <strong style={{ color: 'var(--cyber-emerald)' }}>{lastResult.entities_found}</strong>
              </div>
              <div style={{ color: 'var(--border-subtle)' }}>|</div>
              <div>
                <span style={{ color: 'var(--text-muted)' }}>Evidence ID: </span>
                <strong className="font-mono" style={{ color: 'var(--cyber-violet)' }}>
                  {lastResult.evidence_id || 'Captured'}
                </strong>
              </div>
            </div>

            {/* Raw JSON viewer */}
            <pre style={{
              flex: 1,
              background: '#04070e',
              border: '1px solid var(--border-subtle)',
              borderRadius: '8px',
              padding: '1rem',
              fontSize: '0.75rem',
              color: 'var(--cyber-cyan)',
              maxHeight: '420px',
              overflowY: 'auto',
              lineHeight: '1.5',
            }}>
              {JSON.stringify(lastResult.result, null, 2)}
            </pre>
          </div>
        ) : (
          <div style={{
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '3rem',
            textAlign: 'center',
            color: 'var(--text-dim)',
            background: 'rgba(0, 0, 0, 0.2)',
            borderRadius: '8px',
            border: '1px dashed var(--border-subtle)',
          }}>
            <Terminal size={32} style={{ opacity: 0.4, marginBottom: '0.85rem' }} />
            <p style={{ fontSize: '0.85rem', maxWidth: '340px' }}>
              Select a tool on the left and click <strong>Execute & Correlate Graph</strong> to dispatch an automated OSINT reconnaissance query.
            </p>
          </div>
        )}
      </div>
    </div>
  );
};
