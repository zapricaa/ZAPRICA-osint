'use client';

import React, { useState } from 'react';
import { useAppStore } from '@/lib/store';
import { SeedEntityType } from '@/types';
import { X, ShieldAlert, Check, Loader2, Sparkles } from 'lucide-react';

export const CaseCreationModal: React.FC = () => {
  const { isCreateModalOpen, closeCreateModal, createInvestigation, isSaving } = useAppStore();

  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [seedEntity, setSeedEntity] = useState('');
  const [seedEntityType, setSeedEntityType] = useState<SeedEntityType>('domain');
  const [authorizedUse, setAuthorizedUse] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  if (!isCreateModalOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);

    if (!name.trim()) {
      setFormError('Investigation name is required.');
      return;
    }
    if (!seedEntity.trim()) {
      setFormError('Seed entity is required (e.g., target domain or IP).');
      return;
    }
    if (!authorizedUse) {
      setFormError('You must confirm authorized use and compliance with public-source regulations.');
      return;
    }

    const created = await createInvestigation({
      name: name.trim(),
      description: description.trim() || undefined,
      seed_entity: seedEntity.trim(),
      seed_entity_type: seedEntityType,
      authorized_use_confirmed: authorizedUse,
    });

    if (created) {
      // Reset form
      setName('');
      setDescription('');
      setSeedEntity('');
      setAuthorizedUse(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={closeCreateModal}>
      <div 
        className="modal-content" 
        onClick={(e) => e.stopPropagation()} 
        role="dialog" 
        aria-modal="true"
        aria-labelledby="modal-title"
      >
        {/* Modal Header */}
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
              <ShieldAlert size={18} color="var(--cyber-cyan)" />
            </div>
            <div>
              <h2 id="modal-title" style={{ fontSize: '1.1rem', fontWeight: '700', color: 'var(--text-main)' }}>
                Initiate New Investigation
              </h2>
              <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                Seed an autonomous OSINT graph with verifiable provenance
              </p>
            </div>
          </div>
          <button 
            onClick={closeCreateModal} 
            className="btn btn-secondary btn-sm"
            style={{ padding: '0.35rem', borderRadius: '6px' }}
            aria-label="Close dialog"
          >
            <X size={16} />
          </button>
        </div>

        {/* Modal Body */}
        <form onSubmit={handleSubmit} style={{ padding: '1.5rem' }}>
          {formError && (
            <div style={{
              background: 'rgba(244, 63, 94, 0.12)',
              border: '1px solid rgba(244, 63, 94, 0.35)',
              borderRadius: '8px',
              padding: '0.75rem 1rem',
              color: 'var(--cyber-rose)',
              fontSize: '0.8rem',
              marginBottom: '1.25rem',
            }}>
              {formError}
            </div>
          )}

          {/* Investigation Name */}
          <div style={{ marginBottom: '1.25rem' }}>
            <label 
              htmlFor="investigation-name" 
              style={{ display: 'block', fontSize: '0.8rem', fontWeight: '600', color: 'var(--text-muted)', marginBottom: '0.4rem' }}
            >
              Investigation Name *
            </label>
            <input
              id="investigation-name"
              type="text"
              className="input-field"
              placeholder="e.g. Operation Stormbreaker C2 Recon"
              value={name}
              onChange={(e) => setName(e.target.value)}
              disabled={isSaving}
              autoFocus
            />
          </div>

          {/* Seed Target Entity & Type */}
          <div style={{ display: 'grid', gridTemplateColumns: '2fr 1.2fr', gap: '0.85rem', marginBottom: '1.25rem' }}>
            <div>
              <label 
                htmlFor="seed-target-value" 
                style={{ display: 'block', fontSize: '0.8rem', fontWeight: '600', color: 'var(--text-muted)', marginBottom: '0.4rem' }}
              >
                Seed Target Value *
              </label>
              <input
                id="seed-target-value"
                type="text"
                className="input-field font-mono"
                placeholder="e.g. threat-actor-domain.com"
                value={seedEntity}
                onChange={(e) => setSeedEntity(e.target.value)}
                disabled={isSaving}
              />
            </div>
            <div>
              <label 
                htmlFor="seed-entity-type" 
                style={{ display: 'block', fontSize: '0.8rem', fontWeight: '600', color: 'var(--text-muted)', marginBottom: '0.4rem' }}
              >
                Entity Type
              </label>
              <select
                id="seed-entity-type"
                className="input-field"
                value={seedEntityType}
                onChange={(e) => setSeedEntityType(e.target.value as SeedEntityType)}
                disabled={isSaving}
                style={{ cursor: 'pointer' }}
              >
                <option value="domain">Domain</option>
                <option value="ip_address">IP Address</option>
                <option value="url">URL</option>
                <option value="email">Email</option>
                <option value="person">Person</option>
                <option value="organization">Organization</option>
                <option value="file_hash">File Hash</option>
                <option value="phone">Phone</option>
                <option value="asn">ASN</option>
                <option value="certificate">Certificate</option>
              </select>
            </div>
          </div>

          {/* Description */}
          <div style={{ marginBottom: '1.25rem' }}>
            <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: '600', color: 'var(--text-muted)', marginBottom: '0.4rem' }}>
              Description & Scope (Optional)
            </label>
            <textarea
              className="input-field"
              rows={3}
              placeholder="Investigation objectives, targeted APT clusters, or operational constraints..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              disabled={isSaving}
              style={{ resize: 'vertical' }}
            />
          </div>

          {/* Legal / DPDP Act Compliance Attestation */}
          <div style={{
            background: 'rgba(0, 240, 255, 0.04)',
            border: '1px solid rgba(0, 240, 255, 0.15)',
            borderRadius: '8px',
            padding: '0.85rem 1rem',
            marginBottom: '1.5rem',
          }}>
            <label style={{ display: 'flex', alignItems: 'flex-start', gap: '0.65rem', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={authorizedUse}
                onChange={(e) => setAuthorizedUse(e.target.checked)}
                disabled={isSaving}
                style={{ marginTop: '0.2rem', accentColor: 'var(--cyber-cyan)' }}
              />
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', lineHeight: '1.45' }}>
                <strong style={{ color: 'var(--text-main)' }}>Authorized-Use Policy Confirmation:</strong> I attest that this investigation targets lawful, public-source information in compliance with Section 3(c)(ii) of the Digital Personal Data Protection (DPDP) Act, 2023. All findings will be cryptographically anchored with SHA-256 evidence hashes.
              </span>
            </label>
          </div>

          {/* Form Actions */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: '0.75rem' }}>
            <button
              type="button"
              onClick={closeCreateModal}
              className="btn btn-secondary"
              disabled={isSaving}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={isSaving}
            >
              {isSaving ? (
                <>
                  <Loader2 size={16} className="animate-spin" />
                  <span>Provisioning...</span>
                </>
              ) : (
                <>
                  <Sparkles size={16} />
                  <span>Create & Launch Workspace</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
