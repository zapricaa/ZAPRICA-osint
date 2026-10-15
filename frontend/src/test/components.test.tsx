import React from 'react';
import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { Header } from '@/components/Header';
import { StatsCards } from '@/components/StatsCards';
import { InvestigationCard } from '@/components/InvestigationCard';
import { CaseCreationModal } from '@/components/CaseCreationModal';
import { useAppStore } from '@/lib/store';
import { Investigation } from '@/types';

const mockInvestigation: Investigation = {
  id: 'inv-test-01',
  name: 'Project Threat Hunter',
  description: 'Tracking malicious command and control infrastructure',
  seed_entity: 'malicious-domain.com',
  seed_entity_type: 'domain',
  status: 'active',
  authorized_use_confirmed: true,
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
  entity_count: 7,
  evidence_count: 3,
};

describe('ZAPRICA UI Component Suite', () => {
  beforeEach(() => {
    useAppStore.setState({
      investigations: [mockInvestigation],
      activeInvestigation: null,
      isLiveBackend: false,
      isCreateModalOpen: false,
      searchQuery: '',
    });
  });

  it('renders Header with brand and new investigation button', () => {
    render(<Header />);
    expect(screen.getByText('ZAPRICA')).toBeInTheDocument();
    expect(screen.getByText('New Investigation')).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/search cases/i)).toBeInTheDocument();
  });

  it('renders StatsCards with metrics and fixture indicator when offline', () => {
    render(<StatsCards />);
    expect(screen.getByText('INVESTIGATIONS')).toBeInTheDocument();
    expect(screen.getByText('CORRELATED ENTITIES')).toBeInTheDocument();
    expect(screen.getByText('EVIDENCE PROVENANCE')).toBeInTheDocument();
    expect(screen.getByText('AUTONOMOUS TOOLS')).toBeInTheDocument();
    expect(screen.getByText('FIXTURE FALLBACK')).toBeInTheDocument();
  });

  it('renders InvestigationCard with title, seed target, and entity counters', () => {
    render(<InvestigationCard investigation={mockInvestigation} />);
    expect(screen.getByText('Project Threat Hunter')).toBeInTheDocument();
    expect(screen.getByText('malicious-domain.com')).toBeInTheDocument();
    expect(screen.getByText('7')).toBeInTheDocument();
    expect(screen.getByText('3')).toBeInTheDocument();
    expect(screen.getByText('Workspace')).toBeInTheDocument();
  });

  it('renders CaseCreationModal when opened and handles validation', () => {
    useAppStore.setState({ isCreateModalOpen: true });
    render(<CaseCreationModal />);

    expect(screen.getByText('Initiate New Investigation')).toBeInTheDocument();
    expect(screen.getByLabelText(/investigation name/i)).toBeInTheDocument();

    // Clicking submit without filling name shows error
    const submitBtn = screen.getByRole('button', { name: /create & launch workspace/i });
    fireEvent.click(submitBtn);

    expect(screen.getByText(/investigation name is required/i)).toBeInTheDocument();
  });
});
