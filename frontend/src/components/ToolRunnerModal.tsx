'use client';

import React, { useState, useEffect } from 'react';
import { useAppStore } from '@/lib/store';
import { 
  X, 
  Terminal, 
  Play, 
  Loader2, 
  CheckCircle2, 
  AlertCircle, 
  Copy, 
  Check, 
  Sparkles
} from 'lucide-react';
import { ToolExecuteResponse } from '@/types';

export const ToolRunnerModal: React.FC = () => {
  const { 
    isToolModalOpen, 
    closeToolModal, 
    tools, 
    fetchTools, 
    executeTool, 
    isSaving,
    investigations,
    activeInvestigation
  } = useAppStore();

  const [toolName, setToolName] = useState<string>('dns_lookup');
  const [targetInvId, setTargetInvId] = useState<string>('');
  const [params, setParams] = useState<Record<string, string>>({ domain: 'example.com', record_type: 'A' });
  const [result, setResult] = useState<ToolExecuteResponse | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    fetchTools();
  }, [fetchTools]);

  useEffect(() => {
    if (activeInvestigation) {
      setTargetInvId(activeInvestigation.id);
    }
  }, [activeInvestigation]);

  useEffect(() => {
    if (toolName === 'dns_lookup') {
      setParams({ domain: 'example.com', record_type: 'A' });
    } else if (toolName === 'http_metadata') {
      setParams({ url: 'https://example.com' });
    } else if (toolName === 'tls_certificate') {
      setParams({ hostname: 'example.com', port: '443' });
    } else if (toolName === 'rdap_lookup') {
      setParams({ domain: 'example.com' });
    } else if (toolName === 'webpage_metadata') {
      setParams({ url: 'https://example.com' });
    }
  }, [toolName]);

  if (!isToolModalOpen) return null;

  const handleRun = async (e: React.FormEvent) => {
    e.preventDefault();
    const formattedParams: Record<string, unknown> = { ...params };
    if (formattedParams.port) {
      formattedParams.port = parseInt(formattedParams.port as string, 10) || 443;
    }

    const res = await executeTool({
      tool_name: toolName,
      parameters: formattedParams,
      investigation_id: targetInvId || undefined,
    });

    if (res) {
      setResult(res);
    }
  };

  const copyResult = () => {
    if (!result?.result) return;
    navigator.clipboard.writeText(JSON.stringify(result.result, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="modal-overlay" onClick={closeToolModal}>
      <div 
        className="modal-content" 
        onClick={(e) => e.stopPropagation()} 
        style={{ maxWidth: '800px' }}
        role="dialog"
        aria-modal="true"
        aria-labelledby="tool-modal-title"
      >
        {/* Header */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '1.25rem 1.5rem',
          borderBottom: '1px solid var(--border-subtle)',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
            <div style={{
              width: '32px',
              height: '32px',
              borderRadius: '8px',
              background: 'rgba(0, 240, 255, 0.12)',
              border: '1px solid var(--border-glow)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}>
              <Terminal size={17} color="var(--cyber-cyan)" />
            </div>
            <div>
              <h2 id="tool-modal-title" style={{ fontSize: '1.05rem', fontWeight: '700', color: 'var(--text-main)' }}>
                MCP OSINT Tool Execution Console
              </h2>
              <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                Execute verified discovery tools compliant with Model Context Protocol
              </p>
            </div>
          </div>
          <button onClick={closeToolModal} className="btn btn-secondary btn-sm" aria-label="Close dialog">
            <X size={16} />
          </button>
        </div>

        {/* Body */}
        <div style={{ padding: '1.5rem', display: 'grid', gridTemplateColumns: '1.1fr 1.3fr', gap: '1.5rem' }}>
          {/* Controls */}
          <form onSubmit={handleRun}>
            <div style={{ marginBottom: '1rem' }}>
              <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: '600', color: 'var(--text-muted)', marginBottom: '0.35rem' }}>
                Tool Module
              </label>
              <select
                className="input-field"
                value={toolName}
                onChange={(e) => setToolName(e.target.value)}
                disabled={isSaving}
              >
                <option value="dns_lookup">dns_lookup (A, AAAA, MX, NS, TXT)</option>
                <option value="http_metadata">http_metadata (Headers, Server, TLS)</option>
                <option value="tls_certificate">tls_certificate (SANs, Issuer, Validity)</option>
                <option value="rdap_lookup">rdap_lookup (Registrar, Contacts, NS)</option>
                <option value="webpage_metadata">webpage_metadata (Title, OG, Linked Domains)</option>
              </select>
            </div>

            <div style={{ marginBottom: '1rem' }}>
              <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: '600', color: 'var(--text-muted)', marginBottom: '0.35rem' }}>
                Target Investigation (Optional Attachment)
              </label>
              <select
                className="input-field"
                value={targetInvId}
                onChange={(e) => setTargetInvId(e.target.value)}
                disabled={isSaving}
              >
                <option value="">-- Standalone Run (No Case Link) --</option>
                {investigations.map((inv) => (
                  <option key={inv.id} value={inv.id}>
                    {inv.name} ({inv.seed_entity})
                  </option>
                ))}
              </select>
            </div>

            {/* Parameter Fields */}
            {toolName === 'dns_lookup' && (
              <>
                <div style={{ marginBottom: '1rem' }}>
                  <label style={{ display: 'block', fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: '0.35rem' }}>
                    Domain
                  </label>
                  <input
                    type="text"
                    className="input-field font-mono"
                    value={params.domain || ''}
                    onChange={(e) => setParams({ ...params, domain: e.target.value })}
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
                  >
                    <option value="A">A</option>
                    <option value="AAAA">AAAA</option>
                    <option value="MX">MX</option>
                    <option value="NS">NS</option>
                    <option value="TXT">TXT</option>
                    <option value="CNAME">CNAME</option>
                  </select>
                </div>
              </>
            )}

            {(toolName === 'http_metadata' || toolName === 'webpage_metadata') && (
              <div style={{ marginBottom: '1.25rem' }}>
                <label style={{ display: 'block', fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: '0.35rem' }}>
                  Target URL
                </label>
                <input
                  type="text"
                  className="input-field font-mono"
                  value={params.url || ''}
                  onChange={(e) => setParams({ ...params, url: e.target.value })}
                  required
                />
              </div>
            )}

            {toolName === 'tls_certificate' && (
              <div style={{ display: 'grid', gridTemplateColumns: '3fr 1fr', gap: '0.75rem', marginBottom: '1.25rem' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: '0.35rem' }}>
                    Hostname
                  </label>
                  <input
                    type="text"
                    className="input-field font-mono"
                    value={params.hostname || ''}
                    onChange={(e) => setParams({ ...params, hostname: e.target.value })}
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
                  />
                </div>
              </div>
            )}

            {toolName === 'rdap_lookup' && (
              <div style={{ marginBottom: '1.25rem' }}>
                <label style={{ display: 'block', fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: '0.35rem' }}>
                  Domain
                </label>
                <input
                  type="text"
                  className="input-field font-mono"
                  value={params.domain || ''}
                  onChange={(e) => setParams({ ...params, domain: e.target.value })}
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
                  <span>Dispatching Query...</span>
                </>
              ) : (
                <>
                  <Play size={15} />
                  <span>Execute Tool</span>
                </>
              )}
            </button>
          </form>

          {/* Result Output Terminal */}
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
              <span style={{ fontSize: '0.75rem', fontWeight: '600', color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                Telemetry Stream
              </span>
              {result && (
                <button
                  type="button"
                  onClick={copyResult}
                  className="btn btn-secondary btn-sm"
                  style={{ padding: '0.2rem 0.5rem', fontSize: '0.72rem', gap: '0.3rem' }}
                >
                  {copied ? <Check size={12} color="var(--cyber-emerald)" /> : <Copy size={12} />}
                  <span>{copied ? 'Copied' : 'Copy JSON'}</span>
                </button>
              )}
            </div>

            <pre style={{
              flex: 1,
              background: '#04070e',
              border: '1px solid var(--border-subtle)',
              borderRadius: '8px',
              padding: '1rem',
              fontSize: '0.75rem',
              color: 'var(--cyber-cyan)',
              maxHeight: '360px',
              minHeight: '260px',
              overflowY: 'auto',
              lineHeight: '1.5',
            }}>
              {result ? JSON.stringify(result.result, null, 2) : '// Awaiting command execution output...'}
            </pre>
          </div>
        </div>
      </div>
    </div>
  );
};
