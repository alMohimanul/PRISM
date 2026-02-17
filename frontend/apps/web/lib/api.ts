import axios from 'axios';
import type {
  Document,
  Session,
  ChatResponse,
  UploadResponse,
} from '@/types';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Documents
export const documentsApi = {
  upload: async (file: File): Promise<UploadResponse> => {
    const formData = new FormData();
    formData.append('file', file);
    const { data } = await api.post('/api/documents/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return data;
  },

  list: async (): Promise<Document[]> => {
    const { data } = await api.get('/api/documents');
    return data;
  },

  get: async (documentId: string): Promise<Document> => {
    const { data } = await api.get(`/api/documents/${documentId}`);
    return data;
  },

  delete: async (documentId: string): Promise<void> => {
    await api.delete(`/api/documents/${documentId}`);
  },
};

// Sessions
export const sessionsApi = {
  create: async (
    name: string,
    topic?: string,
    description?: string
  ): Promise<Session> => {
    const { data } = await api.post('/api/sessions', {
      name,
      topic,
      description,
    });
    return data;
  },

  list: async (): Promise<Session[]> => {
    const { data } = await api.get('/api/sessions');
    return data;
  },

  get: async (sessionId: string): Promise<Session> => {
    const { data } = await api.get(`/api/sessions/${sessionId}`);
    return data;
  },

  delete: async (sessionId: string): Promise<void> => {
    await api.delete(`/api/sessions/${sessionId}`);
  },

  addDocument: async (
    sessionId: string,
    documentId: string
  ): Promise<void> => {
    await api.post(`/api/sessions/${sessionId}/documents/${documentId}`);
  },
};

// Chat
export const chatApi = {
  sendMessage: async (
    sessionId: string,
    message: string,
    agentType?: string,
    documentIds?: string[]
  ): Promise<ChatResponse> => {
    const { data } = await api.post('/api/chat', {
      session_id: sessionId,
      message,
      agent_type: agentType,
      document_ids: documentIds,
    });
    return data;
  },
};

// Health check
export const healthCheck = async (): Promise<{ status: string }> => {
  const { data } = await api.get('/health');
  return data;
};
