'use client';

import React, { useState } from 'react';
import { Evidence } from '@/types';
import { useAppStore } from '@/lib/store';
import { 
  ShieldCheck, 
  Lock, 
  Copy, 
  Check, 
  Eye, 
  Plus, 
  X, 
  FileCode, 
  ExternalLink,
  Calendar,
  Wrench,
  Loader2
} from 'lucide-react';
import { api } from '@/lib/api';

interface Props {
  evidence: Evidence[];
  investigationId: string;
}

export const EvidenceLedger: React.FC<Props> = ({ evidence, investigationId }) => {
  const { fetchInvestigationDetails } = useAppStore();
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [selectedArtifact, setSelectedArtifact] = useState<Evidence | null>(null);
  const [isAddOpen, setIsAddOpen] = useState(false);

  // Form state for manual evidence
  const [sourceUrl, setSourceUrl] = useState('');
  const [toolName, setToolName] = useState('manual_entry');
  const [rawContent, setRawContent] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const copyHash = (hash: string, id: string) => {
    navigator.clipboard.writeText(hash);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleAddEvidence = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!rawContent.trim()) return;

    setIsSubmitting(true);
    try {
      await api.createEvidence(investigationId, {
        source_url: sourceUrl.trim() || undefined,
        tool_name: toolName,
        collection_method: 'analyst_ingestion',
        content_type: 'application/json',
        raw_content: rawContent.trim(),
      });
      await fetchInvestigationDetails(investigationId);
      setIsAddOpen(false);
      setSourceUrl('');
      setRawContent('');
    } catch (err) {
      console.error(err);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      {/* Cryptographic Guarantee Banner */}
      <div style={{
        background: 'linear-gradient(135deg, rgba(139, 92, 246, 0.1) 0%, rgba(0, 240, 255, 0.08) 100%)',
        border: '1px solid rgba(139, 92, 246, 0.3)',
        borderRadius: '10px',
        padding: '1rem 1.25rem',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '1rem',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <div style={{
            width: '36px',
            height: '36px',
            borderRadius: '8px',
            background: 'rgba(139, 92, 246, 0.2)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}>
            <Lock size={18} color="var(--cyber-violet)" />
          </div>
          <div>
            <div style={{ fontSize: '0.85rem', fontWeight: '700', color: 'var(--text-main)' }}>
              Verifiable Cryptographic Evidence Provenance
            </div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Every OSINT finding is cryptographically stamped with SHA-256 hashes and ISO-8601 collection timestamps to guarantee evidentiary admissibility.
            </div>
          </div>
        </div>

        <button
          onClick={() => setIsAddOpen(true)}
          className="btn btn-secondary btn-sm"
          style={{ gap: '0.4rem' }}
        >
          <Plus size={14} color="var(--cyber-cyan)" />
          <span>Ingest Evidence Artifact</span>
        </button>
      </div>

      {/* Evidence Ledger Table */}
      <div className="glass-panel" style={{ padding: '1.25rem' }}>
        <div style={{ overflowX: 'auto' }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>Artifact ID</th>
                <th>Collection Tool</th>
                <th>Source URL / Target</th>
                <th>SHA-256 Cryptographic Hash</th>
                <th>Timestamp</th>
                <th style={{ textAlign: 'right' }}>Payload</th>
              </tr>
            </thead>
            <tbody>
              {evidence.length > 0 ? (
                evidence.map((item) => (
                  <tr key={item.id}>
                    <td>
                      <span className="font-mono" style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                        {item.id}
                      </span>
                    </td>
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                        <Wrench size={13} color="var(--cyber-amber)" />
                        <span style={{ fontSize: '0.8rem', fontWeight: '500', color: 'var(--text-main)' }}>
                          {item.tool_name || 'System Log'}
                        </span>
                      </div>
                    </td>
                    <td>
                      <span style={{ fontSize: '0.78rem', color: 'var(--cyber-cyan)' }} className="font-mono">
                        {item.source_url || 'N/A'}
                      </span>
                    </td>
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                        <span 
                          className="font-mono" 
                          style={{
                            fontSize: '0.72rem',
                            color: 'var(--cyber-violet)',
                            background: 'rgba(139, 92, 246, 0.08)',
                            padding: '0.15rem 0.45rem',
                            borderRadius: '4px',
                            maxWidth: '180px',
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            whiteSpace: 'nowrap',
                          }}
                          title={item.sha256_hash || ''}
                        >
                          {item.sha256_hash ? `${item.sha256_hash.substring(0, 16)}...` : 'Generating hash'}
                        </span>
                        {item.sha256_hash && (
                          <button
                            onClick={() => copyHash(item.sha256_hash!, item.id)}
                            className="btn btn-secondary btn-sm"
                            style={{ padding: '0.2rem' }}
                            title="Copy full SHA-256 hash"
                          >
                            {copiedId === item.id ? <Check size={12} color="var(--cyber-emerald)" /> : <Copy size={12} />}
                          </button>
                        )}
                      </div>
                    </td>
                    <td style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>
                      {new Date(item.collected_at).toLocaleDateString('en-US', {
                        month: 'short',
                        day: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit',
                        second: '2-digit',
                      })}
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      <button
                        onClick={() => setSelectedArtifact(item)}
                        className="btn btn-secondary btn-sm"
                        style={{ fontSize: '0.72rem', padding: '0.25rem 0.55rem', gap: '0.35rem' }}
                      >
                        <Eye size={12} color="var(--cyber-cyan)" />
                        <span>Inspect</span>
                      </button>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={6} style={{ textAlign: 'center', padding: '2.5rem', color: 'var(--text-dim)' }}>
                    No cryptographic evidence artifacts recorded yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Raw Payload Inspector Modal */}
      {selectedArtifact && (
        <div className="modal-overlay" onClick={() => setSelectedArtifact(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '720px' }}>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '1.25rem 1.5rem',
              borderBottom: '1px solid var(--border-subtle)',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
                <ShieldCheck size={20} color="var(--cyber-violet)" />
                <div>
                  <h3 style={{ fontSize: '1rem', fontWeight: '700', color: 'var(--text-main)' }}>
                    Evidence Artifact Details
                  </h3>
                  <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)' }} className="font-mono">
                    ID: {selectedArtifact.id}
                  </div>
                </div>
              </div>
              <button 
                onClick={() => setSelectedArtifact(null)} 
                className="btn btn-secondary btn-sm"
                style={{ padding: '0.35rem' }}
              >
                <X size={16} />
              </button>
            </div>

            <div style={{ padding: '1.5rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div style={{
                background: 'rgba(0, 0, 0, 0.4)',
                borderRadius: '8px',
                padding: '0.85rem',
                border: '1px solid var(--border-subtle)',
                fontSize: '0.78rem',
              }}>
                <div style={{ marginBottom: '0.4rem', color: 'var(--text-muted)' }}>
                  <strong>Source Target:</strong> <span className="font-mono" style={{ color: 'var(--cyber-cyan)' }}>{selectedArtifact.source_url || 'Internal'}</span>
                </div>
                <div style={{ marginBottom: '0.4rem', color: 'var(--text-muted)' }}>
                  <strong>Tool / Ingestion:</strong> {selectedArtifact.tool_name} ({selectedArtifact.collection_method})
                </div>
                <div style={{ color: 'var(--text-muted)', wordBreak: 'break-all' }}>
                  <strong>SHA-256 Digest:</strong> <span className="font-mono" style={{ color: 'var(--cyber-violet)' }}>{selectedArtifact.sha256_hash}</span>
                </div>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.78rem', fontWeight: '600', color: 'var(--text-muted)', marginBottom: '0.4rem' }}>
                  Raw Artifact Content (Immutable)
                </label>
                <pre style={{
                  background: '#04070e',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: '8px',
                  padding: '1rem',
                  fontSize: '0.75rem',
                  color: 'var(--text-main)',
                  maxHeight: '320px',
                  overflowY: 'auto',
                  lineHeight: '1.5',
                }}>
                  {selectedArtifact.raw_content ? (
                    (() => {
                      try {
                        return JSON.stringify(JSON.parse(selectedArtifact.raw_content), null, 2);
                      } catch {
                        return selectedArtifact.raw_content;
                      }
                    })()
                  ) : (
                    'No raw payload stored for this record.'
                  )}
                </pre>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                <button
                  onClick={() => setSelectedArtifact(null)}
                  className="btn btn-secondary"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Ingest Manual Evidence Modal */}
      {isAddOpen && (
        <div className="modal-overlay" onClick={() => setIsAddOpen(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '1.25rem 1.5rem',
              borderBottom: '1px solid var(--border-subtle)',
            }}>
              <h3 style={{ fontSize: '1rem', fontWeight: '700', color: 'var(--text-main)' }}>
                Ingest Evidence Artifact
              </h3>
              <button onClick={() => setIsAddOpen(false)} className="btn btn-secondary btn-sm">
                <X size={16} />
              </button>
            </div>

            <form onSubmit={handleAddEvidence} style={{ padding: '1.5rem' }}>
              <div style={{ marginBottom: '1rem' }}>
                <label style={{ display: 'block', fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '0.35rem' }}>
                  Source Target / URL
                </label>
                <input
                  type="text"
                  className="input-field"
                  placeholder="e.g. https://target-host.org/advisory"
                  value={sourceUrl}
                  onChange={(e) => setSourceUrl(e.target.value)}
                  disabled={isSubmitting}
                />
              </div>

              <div style={{ marginBottom: '1rem' }}>
                <label style={{ display: 'block', fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '0.35rem' }}>
                  Tool or Ingestion Tag
                </label>
                <input
                  type="text"
                  className="input-field"
                  value={toolName}
                  onChange={(e) => setToolName(e.target.value)}
                  disabled={isSubmitting}
                />
              </div>

              <div style={{ marginBottom: '1.25rem' }}>
                <label style={{ display: 'block', fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '0.35rem' }}>
                  Raw Content (JSON or Text payload to be SHA-256 hashed) *
                </label>
                <textarea
                  className="input-field font-mono"
                  rows={6}
                  placeholder='{"dns_query": "target.org", "results": ["1.2.3.4"]}'
                  value={rawContent}
                  onChange={(e) => setRawContent(e.target.value)}
                  disabled={isSubmitting}
                  required
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem' }}>
                <button
                  type="button"
                  onClick={() => setIsAddOpen(false)}
                  className="btn btn-secondary"
                  disabled={isSubmitting}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={isSubmitting || !rawContent.trim()}
                >
                  {isSubmitting ? (
                    <>
                      <Loader2 size={16} className="animate-spin" />
                      <span>Hashing & Stamping...</span>
                    </>
                  ) : (
                    <span>Anchor Evidence</span>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
