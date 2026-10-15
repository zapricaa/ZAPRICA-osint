'use client';

import React, { useState, useRef, useEffect } from 'react';
import dynamic from 'next/dynamic';
import { useAppStore } from '@/lib/store';
import { 
  Maximize2, 
  ZoomIn, 
  ZoomOut, 
  Filter, 
  Layers, 
  X, 
  ExternalLink, 
  Terminal, 
  ShieldCheck, 
  ChevronRight,
  Info,
  Loader2
} from 'lucide-react';
import { SeedEntityType } from '@/types';

// Dynamically import inner canvas graph with SSR disabled
const ForceGraphInner = dynamic(
  () => import('./ForceGraphInner').then((mod) => mod.ForceGraphInner),
  {
    ssr: false,
    loading: () => (
      <div style={{
        height: '100%',
        width: '100%',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        background: '#070b14',
        color: 'var(--text-muted)',
        gap: '0.75rem',
      }}>
        <Loader2 size={28} className="animate-spin" color="var(--cyber-cyan)" />
        <span style={{ fontSize: '0.85rem' }}>Initializing WebGL Intelligence Graph...</span>
      </div>
    ),
  }
);

export const IntelligenceGraph: React.FC = () => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });
  const { 
    graph, 
    selectedNode, 
    setSelectedNode, 
    selectedEdge, 
    setSelectedEdge,
    graphFilterType,
    setGraphFilterType,
    openToolModal,
    activeInvestigation
  } = useAppStore();

  // Measure container dimensions reactively
  useEffect(() => {
    const updateSize = () => {
      if (containerRef.current) {
        setDimensions({
          width: containerRef.current.clientWidth || 800,
          height: containerRef.current.clientHeight || 600,
        });
      }
    };

    updateSize();
    window.addEventListener('resize', updateSize);
    return () => window.removeEventListener('resize', updateSize);
  }, []);

  const entityTypes: { label: string; value: SeedEntityType | null }[] = [
    { label: 'All Entities', value: null },
    { label: 'Domains', value: 'domain' },
    { label: 'IPs', value: 'ip_address' },
    { label: 'Emails', value: 'email' },
    { label: 'Organizations', value: 'organization' },
    { label: 'Persons', value: 'person' },
    { label: 'Hashes', value: 'file_hash' },
  ];

  const handlePivotWithTool = (toolName: string, paramKey: string, paramValue: string) => {
    openToolModal();
  };

  return (
    <div 
      ref={containerRef}
      style={{
        position: 'relative',
        width: '100%',
        height: '620px',
        background: '#070b14',
        borderRadius: '12px',
        overflow: 'hidden',
        border: '1px solid var(--border-subtle)',
      }}
    >
      {/* Canvas Layer */}
      <ForceGraphInner
        nodes={graph.nodes || []}
        edges={graph.edges || []}
        width={dimensions.width}
        height={dimensions.height}
      />

      {/* Top Floating Controls: Entity Type Filter */}
      <div style={{
        position: 'absolute',
        top: '1rem',
        left: '1rem',
        zIndex: 10,
        display: 'flex',
        alignItems: 'center',
        gap: '0.4rem',
        background: 'rgba(6, 9, 17, 0.82)',
        backdropFilter: 'blur(12px)',
        padding: '0.35rem',
        borderRadius: '8px',
        border: '1px solid var(--border-subtle)',
      }}>
        <div style={{ padding: '0 0.4rem', display: 'flex', alignItems: 'center', gap: '0.3rem', color: 'var(--text-dim)', fontSize: '0.72rem', fontWeight: '600' }}>
          <Filter size={12} />
          <span>FILTER:</span>
        </div>
        {entityTypes.map((t) => (
          <button
            key={t.label}
            onClick={() => setGraphFilterType(t.value)}
            className="btn btn-sm"
            style={{
              padding: '0.2rem 0.55rem',
              fontSize: '0.72rem',
              borderRadius: '5px',
              background: graphFilterType === t.value ? 'rgba(0, 240, 255, 0.18)' : 'transparent',
              color: graphFilterType === t.value ? 'var(--cyber-cyan)' : 'var(--text-muted)',
              border: `1px solid ${graphFilterType === t.value ? 'rgba(0, 240, 255, 0.4)' : 'transparent'}`,
            }}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Graph Stats Overlay Pill */}
      <div style={{
        position: 'absolute',
        top: '1rem',
        right: '1rem',
        zIndex: 10,
        display: 'flex',
        alignItems: 'center',
        gap: '0.75rem',
        background: 'rgba(6, 9, 17, 0.82)',
        backdropFilter: 'blur(12px)',
        padding: '0.4rem 0.85rem',
        borderRadius: '8px',
        border: '1px solid var(--border-subtle)',
        fontSize: '0.75rem',
        color: 'var(--text-muted)',
      }}>
        <span><strong style={{ color: 'var(--cyber-cyan)' }}>{graph.nodes?.length || 0}</strong> Nodes</span>
        <span style={{ color: 'var(--border-subtle)' }}>|</span>
        <span><strong style={{ color: 'var(--cyber-sky)' }}>{graph.edges?.length || 0}</strong> Edges</span>
      </div>

      {/* Selected Node Details Drawer */}
      {selectedNode && (
        <div 
          className="glass-panel"
          style={{
            position: 'absolute',
            bottom: '1rem',
            right: '1rem',
            width: '360px',
            maxHeight: '480px',
            overflowY: 'auto',
            zIndex: 20,
            padding: '1.25rem',
            animation: 'slideUp 200ms ease-out',
            border: '1px solid var(--border-glow)',
            boxShadow: '0 12px 30px rgba(0, 0, 0, 0.6), 0 0 15px rgba(0, 240, 255, 0.2)',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.75rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <span className="badge badge-active" style={{ fontSize: '0.68rem' }}>
                {selectedNode.entity_type}
              </span>
              <span style={{ fontSize: '0.72rem', color: 'var(--text-dim)' }}>
                Confidence: <strong style={{ color: 'var(--cyber-emerald)' }}>{selectedNode.confidence}</strong>
              </span>
            </div>
            <button 
              onClick={() => setSelectedNode(null)}
              className="btn btn-secondary btn-sm"
              style={{ padding: '0.2rem', borderRadius: '4px' }}
            >
              <X size={14} />
            </button>
          </div>

          <h4 style={{
            fontSize: '0.95rem',
            fontWeight: '600',
            color: 'var(--text-main)',
            wordBreak: 'break-all',
            marginBottom: '0.75rem',
          }} className="font-mono">
            {selectedNode.label || selectedNode.value}
          </h4>

          {selectedNode.metadata && Object.keys(selectedNode.metadata).length > 0 && (
            <div style={{
              background: 'rgba(0, 0, 0, 0.35)',
              padding: '0.65rem',
              borderRadius: '6px',
              fontSize: '0.75rem',
              marginBottom: '1rem',
              border: '1px solid var(--border-subtle)',
            }}>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)', textTransform: 'uppercase', marginBottom: '0.3rem' }}>
                Metadata Attributes
              </div>
              {Object.entries(selectedNode.metadata).map(([k, v]) => (
                <div key={k} style={{ display: 'flex', justifyContent: 'space-between', gap: '0.5rem', marginBottom: '0.2rem' }}>
                  <span style={{ color: 'var(--text-muted)' }}>{k}:</span>
                  <span style={{ color: 'var(--text-main)', fontWeight: '500' }}>{String(v)}</span>
                </div>
              ))}
            </div>
          )}

          {/* Pivot Action Trigger */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            <button
              onClick={() => openToolModal()}
              className="btn btn-outline-cyan btn-sm"
              style={{ width: '100%', justifyContent: 'center' }}
            >
              <Terminal size={14} />
              <span>Pivot & Execute OSINT Tool</span>
            </button>
          </div>
        </div>
      )}

      {/* Selected Edge Details Drawer */}
      {selectedEdge && (
        <div 
          className="glass-panel"
          style={{
            position: 'absolute',
            bottom: '1rem',
            right: '1rem',
            width: '340px',
            zIndex: 20,
            padding: '1.25rem',
            animation: 'slideUp 200ms ease-out',
            border: '1px solid rgba(56, 189, 248, 0.4)',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.5rem' }}>
            <span style={{ fontSize: '0.75rem', fontWeight: '700', color: 'var(--cyber-sky)', textTransform: 'uppercase' }}>
              Relationship
            </span>
            <button 
              onClick={() => setSelectedEdge(null)}
              className="btn btn-secondary btn-sm"
              style={{ padding: '0.2rem' }}
            >
              <X size={14} />
            </button>
          </div>

          <div style={{ fontSize: '0.9rem', fontWeight: '600', color: 'var(--text-main)', marginBottom: '0.5rem' }}>
            {selectedEdge.relationship_type}
          </div>

          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.75rem' }}>
            Confidence Assessment: <strong style={{ color: 'var(--cyber-emerald)' }}>{selectedEdge.confidence}</strong>
          </div>

          {selectedEdge.evidence_id && (
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.4rem',
              fontSize: '0.75rem',
              color: 'var(--cyber-violet)',
              background: 'rgba(139, 92, 246, 0.08)',
              padding: '0.4rem 0.6rem',
              borderRadius: '6px',
              border: '1px solid rgba(139, 92, 246, 0.25)',
            }}>
              <ShieldCheck size={14} />
              <span>Evidence Pointer: {selectedEdge.evidence_id}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
