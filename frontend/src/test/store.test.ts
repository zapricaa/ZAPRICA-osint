import { describe, it, expect, beforeEach } from 'vitest';
import { useAppStore } from '@/lib/store';

describe('ZAPRICA Zustand State Store', () => {
  beforeEach(() => {
    useAppStore.setState({
      investigations: [],
      activeInvestigation: null,
      entities: [],
      evidence: [],
      activityLogs: [],
      searchQuery: '',
      statusFilter: null,
      activeTab: 'graph',
      isCreateModalOpen: false,
      isToolModalOpen: false,
    });
  });

  it('initializes with default values', () => {
    const state = useAppStore.getState();
    expect(state.investigations).toEqual([]);
    expect(state.activeInvestigation).toBeNull();
    expect(state.activeTab).toBe('graph');
  });

  it('updates search query and status filter correctly', () => {
    useAppStore.getState().setSearchQuery('DarkOnyx');
    expect(useAppStore.getState().searchQuery).toBe('DarkOnyx');

    useAppStore.getState().setStatusFilter('active');
    expect(useAppStore.getState().statusFilter).toBe('active');
  });

  it('opens and closes modal states', () => {
    useAppStore.getState().openCreateModal();
    expect(useAppStore.getState().isCreateModalOpen).toBe(true);

    useAppStore.getState().closeCreateModal();
    expect(useAppStore.getState().isCreateModalOpen).toBe(false);

    useAppStore.getState().openToolModal();
    expect(useAppStore.getState().isToolModalOpen).toBe(true);

    useAppStore.getState().closeToolModal();
    expect(useAppStore.getState().isToolModalOpen).toBe(false);
  });

  it('fetches investigations and populates store with fixtures when backend is offline', async () => {
    await useAppStore.getState().fetchInvestigations();
    const state = useAppStore.getState();
    expect(state.investigations.length).toBeGreaterThan(0);
    expect(state.isLoading).toBe(false);
  });

  it('switches workspace tabs smoothly', () => {
    useAppStore.getState().setActiveTab('entities');
    expect(useAppStore.getState().activeTab).toBe('entities');

    useAppStore.getState().setActiveTab('evidence');
    expect(useAppStore.getState().activeTab).toBe('evidence');
  });
});
