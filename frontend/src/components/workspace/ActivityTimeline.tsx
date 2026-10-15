'use client';

import React from 'react';
import { ActivityLog } from '@/types';
import { 
  Activity, 
  Terminal, 
  FileCheck, 
  User, 
  Bot, 
  Clock, 
  CheckCircle2, 
  Layers
} from 'lucide-react';

interface Props {
  activityLogs: ActivityLog[];
}

export const ActivityTimeline: React.FC<Props> = ({ activityLogs }) => {
  const getActionBadge = (action: string) => {
    switch (action) {
      case 'investigation_created':
        return { label: 'Case Initialized', color: 'var(--cyber-cyan)', icon: <Layers size={13} /> };
      case 'tool_executed':
        return { label: 'Tool Invocation', color: 'var(--cyber-amber)', icon: <Terminal size={13} /> };
      case 'evidence_collected':
        return { label: 'Evidence Anchored', color: 'var(--cyber-violet)', icon: <FileCheck size={13} /> };
      case 'investigation_updated':
        return { label: 'Case Updated', color: 'var(--cyber-sky)', icon: <CheckCircle2 size={13} /> };
      default:
        return { label: action, color: 'var(--text-muted)', icon: <Activity size={13} /> };
    }
  };

  return (
    <div className="glass-panel" style={{ padding: '1.5rem' }}>
      <h3 style={{ fontSize: '1rem', fontWeight: '700', color: 'var(--text-main)', marginBottom: '1.25rem' }}>
        Autonomous Agent Audit Timeline
      </h3>

      {activityLogs.length > 0 ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', position: 'relative' }}>
          {/* Timeline connecting line */}
          <div style={{
            position: 'absolute',
            left: '16px',
            top: '12px',
            bottom: '12px',
            width: '2px',
            background: 'rgba(255, 255, 255, 0.08)',
            zIndex: 1,
          }} />

          {activityLogs.map((log) => {
            const badge = getActionBadge(log.action);
            return (
              <div 
                key={log.id} 
                style={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: '1rem',
                  position: 'relative',
                  zIndex: 2,
                }}
              >
                {/* Timeline node icon */}
                <div style={{
                  width: '32px',
                  height: '32px',
                  borderRadius: '50%',
                  background: 'var(--bg-surface)',
                  border: `1px solid ${badge.color}`,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: badge.color,
                  flexShrink: 0,
                  boxShadow: `0 0 10px ${badge.color}33`,
                }}>
                  {badge.icon}
                </div>

                {/* Content Box */}
                <div style={{
                  flex: 1,
                  background: 'rgba(255, 255, 255, 0.02)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: '8px',
                  padding: '0.85rem 1rem',
                }}>
                  <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    flexWrap: 'wrap',
                    gap: '0.5rem',
                    marginBottom: '0.35rem',
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <span style={{ fontSize: '0.8rem', fontWeight: '600', color: 'var(--text-main)' }}>
                        {badge.label}
                      </span>
                      <span style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '0.25rem',
                        fontSize: '0.68rem',
                        padding: '0.15rem 0.45rem',
                        borderRadius: '4px',
                        background: 'rgba(255, 255, 255, 0.05)',
                        color: log.actor === 'user' ? 'var(--cyber-cyan)' : 'var(--text-muted)',
                      }}>
                        {log.actor === 'user' ? <User size={10} /> : <Bot size={10} />}
                        <span>{log.actor}</span>
                      </span>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.3rem', fontSize: '0.72rem', color: 'var(--text-dim)' }}>
                      <Clock size={11} />
                      <span>{new Date(log.timestamp).toLocaleString()}</span>
                    </div>
                  </div>

                  {log.details && (
                    <div style={{
                      marginTop: '0.5rem',
                      background: 'rgba(0, 0, 0, 0.35)',
                      borderRadius: '6px',
                      padding: '0.5rem 0.75rem',
                      fontSize: '0.75rem',
                      fontFamily: 'JetBrains Mono, monospace',
                      color: 'var(--text-muted)',
                      overflowX: 'auto',
                    }}>
                      {JSON.stringify(log.details, null, 2)}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div style={{ textAlign: 'center', padding: '2.5rem', color: 'var(--text-dim)' }}>
          No activity logs recorded yet.
        </div>
      )}
    </div>
  );
};
