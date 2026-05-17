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

// ── tipos: chat ──────────────────────────────────────────────

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

// ── tipos: histórias ─────────────────────────────────────────

export interface StoryGenerateRequest {
  child_name: string;
  characters: string[];
  theme: string;
  lesson: string;
  size: 'curta' | 'media' | 'longa';
  reference?: string;
  child_age?: number;
}

export interface Story {
  id: string;
  user_id: string;
  child_name: string;
  characters: string[];
  theme: string;
  lesson: string;
  size: string;
  reference: string | null;
  child_age: number | null;
  titulo: string | null;
  historia: string | null;
  moral: string | null;
  personagens: string[];
  tags: string[];
  model_used: string | null;
  rating: number | null;
  rating_notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface StoryAudio {
  id: string;
  story_id: string;
  voice_id: string;
  voice_name: string | null;
  expires_at: string;
  created_at: string;
}

export interface AudioUrl {
  url: string;
  expires_at: string;
}

export interface Voice {
  id: string;
  name: string;
  description: string;
  preview_text: string;
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

  stories: {
    generate: (req: StoryGenerateRequest) =>
      apiFetch<{ story: Story }>('/v1/stories/generate', {
        method: 'POST',
        body: JSON.stringify(req),
      }).then((r) => r.story),

    list: (params?: { child_name?: string; tag?: string; limit?: number; offset?: number }) => {
      const qs = new URLSearchParams();
      if (params?.child_name) qs.set('child_name', params.child_name);
      if (params?.tag) qs.set('tag', params.tag);
      if (params?.limit != null) qs.set('limit', String(params.limit));
      if (params?.offset != null) qs.set('offset', String(params.offset));
      return apiFetch<Story[]>(`/v1/stories${qs.size ? `?${qs}` : ''}`);
    },

    get: (storyId: string) =>
      apiFetch<Story>(`/v1/stories/${storyId}`),

    rate: (storyId: string, rating: number, notes?: string) =>
      apiFetch<Story>(`/v1/stories/${storyId}/rating`, {
        method: 'POST',
        body: JSON.stringify({ rating, notes: notes ?? null }),
      }),

    generateAudio: (storyId: string, voiceId: string) =>
      apiFetch<StoryAudio>(`/v1/stories/${storyId}/audio`, {
        method: 'POST',
        body: JSON.stringify({ voice_id: voiceId }),
      }),

    getAudioUrl: (storyId: string) =>
      apiFetch<AudioUrl>(`/v1/stories/${storyId}/audio`),

    voices: () =>
      apiFetch<Voice[]>('/v1/stories/voices'),
  },
};
