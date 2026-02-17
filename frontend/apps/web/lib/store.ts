import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { Session, Document, Message } from '@/types';

interface AppState {
  // Current session
  currentSession: Session | null;
  setCurrentSession: (session: Session | null) => void;

  // Messages per session (sessionId -> messages[])
  sessionMessages: Record<string, Message[]>;
  addMessage: (sessionId: string, message: Message) => void;
  setSessionMessages: (sessionId: string, messages: Message[]) => void;
  clearSessionMessages: (sessionId: string) => void;
  getSessionMessages: (sessionId: string) => Message[];

  // Sidebar state
  sidebarOpen: boolean;
  setSidebarOpen: (open: boolean) => void;
  toggleSidebar: () => void;

  // View mode for documents
  documentViewMode: 'grid' | 'list';
  setDocumentViewMode: (mode: 'grid' | 'list') => void;

  // Selected document for PDF viewer
  selectedDocument: Document | null;
  setSelectedDocument: (document: Document | null) => void;

  // PDF Viewer state
  pdfViewerOpen: boolean;
  pdfViewerDocumentId: string | null;
  pdfViewerPage: number;
  pdfViewerHighlightText: string | null;
  openPdfViewer: (documentId: string, page: number, highlightText?: string) => void;
  closePdfViewer: () => void;

  // Loading states
  isLoading: boolean;
  setIsLoading: (loading: boolean) => void;
}

export const useAppStore = create<AppState>()(
  persist(
    (set, get) => ({
      // Session
      currentSession: null,
      setCurrentSession: (session) => set({ currentSession: session }),

      // Messages per session
      sessionMessages: {},
      addMessage: (sessionId, message) =>
        set((state) => ({
          sessionMessages: {
            ...state.sessionMessages,
            [sessionId]: [...(state.sessionMessages[sessionId] || []), message],
          },
        })),
      setSessionMessages: (sessionId, messages) =>
        set((state) => ({
          sessionMessages: {
            ...state.sessionMessages,
            [sessionId]: messages,
          },
        })),
      clearSessionMessages: (sessionId) =>
        set((state) => {
          const { [sessionId]: _, ...rest } = state.sessionMessages;
          return { sessionMessages: rest };
        }),
      getSessionMessages: (sessionId) => get().sessionMessages[sessionId] || [],

      // Sidebar
      sidebarOpen: true,
      setSidebarOpen: (open) => set({ sidebarOpen: open }),
      toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),

      // Document view
      documentViewMode: 'grid',
      setDocumentViewMode: (mode) => set({ documentViewMode: mode }),

      // Selected document
      selectedDocument: null,
      setSelectedDocument: (document) => set({ selectedDocument: document }),

      // PDF Viewer
      pdfViewerOpen: false,
      pdfViewerDocumentId: null,
      pdfViewerPage: 1,
      pdfViewerHighlightText: null,
      openPdfViewer: (documentId, page, highlightText) =>
        set({
          pdfViewerOpen: true,
          pdfViewerDocumentId: documentId,
          pdfViewerPage: page,
          pdfViewerHighlightText: highlightText || null,
        }),
      closePdfViewer: () =>
        set({
          pdfViewerOpen: false,
          pdfViewerDocumentId: null,
          pdfViewerPage: 1,
          pdfViewerHighlightText: null,
        }),

      // Loading
      isLoading: false,
      setIsLoading: (loading) => set({ isLoading: loading }),
    }),
    {
      name: 'prism-app-storage', // localStorage key
      partialize: (state) => ({
        sessionMessages: state.sessionMessages,
        documentViewMode: state.documentViewMode,
      }),
    }
  )
);
