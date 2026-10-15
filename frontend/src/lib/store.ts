import { create } from 'zustand';
import {
  Investigation,
  InvestigationCreate,
  InvestigationUpdate,
  Entity,
  Evidence,
  ActivityLog,
  GraphResponse,
  GraphNode,
  GraphEdge,
  Tool,
  ToolExecuteRequest,
  ToolExecuteResponse,
  HealthResponse,
} from '@/types';
import { api } from './api';

export type WorkspaceTab = 'graph' | 'entities' | 'evidence' | 'activity' | 'tools';

interface AppState {
  // Data
  investigations: Investigation[];
  activeInvestigation: Investigation | null;
  entities: Entity[];
  evidence: Evidence[];
  activityLogs: ActivityLog[];
  graph: GraphResponse;
  tools: Tool[];

  // Graph interaction
  selectedNode: GraphNode | null;
  selectedEdge: GraphEdge | null;
  graphFilterType: string | null;

  // Search & Filter
  searchQuery: string;
  statusFilter: string | null;
  activeTab: WorkspaceTab;

  // System & Environment Status
  isLiveBackend: boolean;
  health: HealthResponse | null;
  isLoading: boolean;
  isSaving: boolean;
  errorMessage: string | null;

  // Modals
  isCreateModalOpen: boolean;
  isToolModalOpen: boolean;
  activeTool: Tool | null;

  // Actions
  checkSystemHealth: () => Promise<void>;
  fetchInvestigations: () => Promise<void>;
  fetchInvestigationDetails: (id: string) => Promise<void>;
  createInvestigation: (data: InvestigationCreate) => Promise<Investigation | null>;
  updateInvestigation: (id: string, data: InvestigationUpdate) => Promise<void>;
  deleteInvestigation: (id: string) => Promise<void>;
  fetchTools: () => Promise<void>;
  executeTool: (payload: ToolExecuteRequest) => Promise<ToolExecuteResponse | null>;

  // UI state actions
  setSearchQuery: (query: string) => void;
  setStatusFilter: (status: string | null) => void;
  setActiveTab: (tab: WorkspaceTab) => void;
  setSelectedNode: (node: GraphNode | null) => void;
  setSelectedEdge: (edge: GraphEdge | null) => void;
  setGraphFilterType: (type: string | null) => void;
  openCreateModal: () => void;
  closeCreateModal: () => void;
  openToolModal: (tool?: Tool) => void;
  closeToolModal: () => void;
  clearError: () => void;
}

export const useAppStore = create<AppState>((set, get) => ({
  investigations: [],
  activeInvestigation: null,
  entities: [],
  evidence: [],
  activityLogs: [],
  graph: { nodes: [], edges: [] },
  tools: [],

  selectedNode: null,
  selectedEdge: null,
  graphFilterType: null,

  searchQuery: '',
  statusFilter: null,
  activeTab: 'graph',

  isLiveBackend: false,
  health: null,
  isLoading: false,
  isSaving: false,
  errorMessage: null,

  isCreateModalOpen: false,
  isToolModalOpen: false,
  activeTool: null,

  checkSystemHealth: async () => {
    const health = await api.checkHealth();
    set({
      health,
      isLiveBackend: health !== null && health.status === 'healthy',
    });
  },

  fetchInvestigations: async () => {
    set({ isLoading: true, errorMessage: null });
    try {
      const { statusFilter } = get();
      const res = await api.getInvestigations(statusFilter || undefined);
      set({
        investigations: res.data.investigations,
        isLiveBackend: !res.isFixture,
        isLoading: false,
      });
    } catch (err: unknown) {
      set({
        isLoading: false,
        errorMessage: err instanceof Error ? err.message : 'Failed to fetch investigations',
      });
    }
  },

  fetchInvestigationDetails: async (id: string) => {
    set({ isLoading: true, errorMessage: null, selectedNode: null, selectedEdge: null });
    try {
      const [invRes, entRes, evRes, actRes, graphRes] = await Promise.all([
        api.getInvestigation(id),
        api.getEntities(id),
        api.getEvidence(id),
        api.getActivityLogs(id),
        api.getGraph(id),
      ]);

      set({
        activeInvestigation: invRes.data,
        entities: entRes.data,
        evidence: evRes.data,
        activityLogs: actRes.data,
        graph: graphRes.data,
        isLiveBackend: !invRes.isFixture,
        isLoading: false,
      });
    } catch (err: unknown) {
      set({
        isLoading: false,
        errorMessage: err instanceof Error ? err.message : 'Failed to load investigation details',
      });
    }
  },

  createInvestigation: async (data: InvestigationCreate) => {
    set({ isSaving: true, errorMessage: null });
    try {
      const res = await api.createInvestigation(data);
      set((state) => ({
        investigations: [res.data, ...state.investigations],
        activeInvestigation: res.data,
        isSaving: false,
        isCreateModalOpen: false,
      }));
      // Refresh details for newly created case
      await get().fetchInvestigationDetails(res.data.id);
      return res.data;
    } catch (err: unknown) {
      set({
        isSaving: false,
        errorMessage: err instanceof Error ? err.message : 'Failed to create investigation',
      });
      return null;
    }
  },

  updateInvestigation: async (id: string, data: InvestigationUpdate) => {
    set({ isSaving: true });
    try {
      const res = await api.updateInvestigation(id, data);
      set((state) => ({
        investigations: state.investigations.map((i) => (i.id === id ? res.data : i)),
        activeInvestigation: state.activeInvestigation?.id === id ? res.data : state.activeInvestigation,
        isSaving: false,
      }));
    } catch (err: unknown) {
      set({
        isSaving: false,
        errorMessage: err instanceof Error ? err.message : 'Failed to update investigation',
      });
    }
  },

  deleteInvestigation: async (id: string) => {
    set({ isSaving: true });
    try {
      await api.deleteInvestigation(id);
      set((state) => ({
        investigations: state.investigations.filter((i) => i.id !== id),
        activeInvestigation: state.activeInvestigation?.id === id ? null : state.activeInvestigation,
        isSaving: false,
      }));
    } catch (err: unknown) {
      set({
        isSaving: false,
        errorMessage: err instanceof Error ? err.message : 'Failed to delete investigation',
      });
    }
  },

  fetchTools: async () => {
    try {
      const res = await api.getTools();
      set({ tools: res.data });
    } catch {
      // fallback in api
    }
  },

  executeTool: async (payload: ToolExecuteRequest) => {
    set({ isSaving: true });
    try {
      const res = await api.executeTool(payload);
      if (payload.investigation_id) {
        // Refresh investigation details to load new entities, evidence, graph nodes
        await get().fetchInvestigationDetails(payload.investigation_id);
      }
      set({ isSaving: false });
      return res.data;
    } catch (err: unknown) {
      set({
        isSaving: false,
        errorMessage: err instanceof Error ? err.message : 'Failed to execute tool',
      });
      return null;
    }
  },

  setSearchQuery: (query: string) => set({ searchQuery: query }),
  setStatusFilter: (status: string | null) => {
    set({ statusFilter: status });
    get().fetchInvestigations();
  },
  setActiveTab: (tab: WorkspaceTab) => set({ activeTab: tab }),
  setSelectedNode: (node: GraphNode | null) => set({ selectedNode: node, selectedEdge: null }),
  setSelectedEdge: (edge: GraphEdge | null) => set({ selectedEdge: edge, selectedNode: null }),
  setGraphFilterType: (type: string | null) => set({ graphFilterType: type }),

  openCreateModal: () => set({ isCreateModalOpen: true }),
  closeCreateModal: () => set({ isCreateModalOpen: false }),
  openToolModal: (tool?: Tool) => set({ isToolModalOpen: true, activeTool: tool || null }),
  closeToolModal: () => set({ isToolModalOpen: false, activeTool: null }),
  clearError: () => set({ errorMessage: null }),
}));
