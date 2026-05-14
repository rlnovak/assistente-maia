import { supabase } from './supabase';

const API_BASE = import.meta.env.PUBLIC_API_URL ?? 'http://localhost:8000';

async function getAuthHeader(): Promise<Record<string, string>> {
  const { data } = await supabase.auth.getSession();
  const token = data.session?.access_token;
  if (!token) return {};
  return { Authorization: `Bearer ${token}` };
}

async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
  retries = 2,
): Promise<T> {
  const authHeaders = await getAuthHeader();
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...authHeaders,
      ...options.headers,
    },
  });

  if (response.status === 401) {
    await supabase.auth.signOut();
    window.location.href = '/login';
    throw new Error('Sessão expirada. Faça login novamente.');
  }

  if (response.status >= 500 && retries > 0) {
    await new Promise((r) => setTimeout(r, 500 * (3 - retries)));
    return apiFetch<T>(path, options, retries - 1);
  }

  if (!response.ok) {
    const body = await response.text();
    throw new Error(`Erro ${response.status}: ${body}`);
  }

  return response.json() as Promise<T>;
}

// ── tipos ────────────────────────────────────────────────────

export interface Conversation {
  id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
}

export interface Message {
  id: string;
  conversation_id: string;
  role: 'user' | 'assistant';
  content: string;
  model_used: string | null;
  created_at: string;
}

export interface ChatResponse {
  conversation_id: string;
  message: Message;
}

// ── endpoints ────────────────────────────────────────────────

export const api = {
  chat: (message: string, conversationId?: string) =>
    apiFetch<ChatResponse>('/v1/chat', {
      method: 'POST',
      body: JSON.stringify({ message, conversation_id: conversationId ?? null }),
    }),

  conversations: () =>
    apiFetch<Conversation[]>('/v1/conversations'),

  messages: (conversationId: string) =>
    apiFetch<Message[]>(`/v1/conversations/${conversationId}/messages`),

  health: () =>
    apiFetch<{ status: string; version: string }>('/v1/health'),
};
