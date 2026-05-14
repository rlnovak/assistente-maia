import { useState, useEffect, useRef, useCallback } from 'react';
import { supabase } from '../lib/supabase';
import { api } from '../lib/api';
import type { Conversation, Message } from '../lib/api';
import ConversationSidebar from './ConversationSidebar';
import MessageBubble from './MessageBubble';

export default function ChatApp() {
  const [authChecked, setAuthChecked] = useState(false);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConvId, setActiveConvId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [loadingConvs, setLoadingConvs] = useState(true);
  const [loadingMsgs, setLoadingMsgs] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // ── auth check ────────────────────────────────────────────

  useEffect(() => {
    // onAuthStateChange dispara imediatamente com a sessão atual (incluindo
    // a sessão recém-criada pelo callback PKCE), antes de getSession() resolver.
    // Usar apenas onAuthStateChange evita o race condition que causava loop.
    const { data: { subscription } } = supabase.auth.onAuthStateChange((event, session) => {
      if (event === 'SIGNED_OUT') {
        window.location.href = '/login';
        return;
      }

      if (session) {
        setIsAuthenticated(true);
        setAuthChecked(true);
      } else if (event === 'INITIAL_SESSION') {
        // SDK terminou de verificar — sem sessão = não autenticado
        window.location.href = '/login';
      }
    });

    return () => subscription.unsubscribe();
  }, []);

  // ── carregar conversas ────────────────────────────────────

  const loadConversations = useCallback(async () => {
    setLoadingConvs(true);
    try {
      const data = await api.conversations();
      setConversations(data);
    } catch {
      // silent — mostrará lista vazia
    } finally {
      setLoadingConvs(false);
    }
  }, []);

  useEffect(() => {
    if (isAuthenticated) loadConversations();
  }, [isAuthenticated, loadConversations]);

  // ── carregar mensagens de uma conversa ────────────────────

  async function loadMessages(convId: string) {
    setLoadingMsgs(true);
    setMessages([]);
    try {
      const data = await api.messages(convId);
      setMessages(data);
    } catch {
      setError('Não foi possível carregar as mensagens.');
    } finally {
      setLoadingMsgs(false);
    }
  }

  function handleSelectConversation(id: string) {
    setActiveConvId(id);
    loadMessages(id);
    setError(null);
  }

  function handleNewConversation() {
    setActiveConvId(null);
    setMessages([]);
    setError(null);
    inputRef.current?.focus();
  }

  // ── auto-scroll ───────────────────────────────────────────

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // ── enviar mensagem ───────────────────────────────────────

  async function handleSend() {
    const text = input.trim();
    if (!text || sending) return;

    const optimisticUser: Message = {
      id: `temp-${Date.now()}`,
      conversation_id: activeConvId ?? '',
      role: 'user',
      content: text,
      model_used: null,
      created_at: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, optimisticUser]);
    setInput('');
    setSending(true);
    setError(null);

    try {
      const response = await api.chat(text, activeConvId ?? undefined);

      if (!activeConvId) {
        setActiveConvId(response.conversation_id);
        await loadConversations();
      }

      setMessages((prev) => [
        ...prev.filter((m) => m.id !== optimisticUser.id),
        { ...optimisticUser, id: `user-${Date.now()}`, conversation_id: response.conversation_id },
        response.message,
      ]);
    } catch (err: unknown) {
      setMessages((prev) => prev.filter((m) => m.id !== optimisticUser.id));
      const msg = err instanceof Error ? err.message : 'Erro ao enviar mensagem.';
      setError(msg);
    } finally {
      setSending(false);
      inputRef.current?.focus();
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  async function handleSignOut() {
    await supabase.auth.signOut();
  }

  // ── render ────────────────────────────────────────────────

  if (!authChecked) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-maia-offwhite">
        <p className="font-serif italic text-maia-cinza text-lg">Verificando sessão...</p>
      </div>
    );
  }

  return (
    <div className="flex h-screen overflow-hidden bg-maia-offwhite">
      {/* Sidebar — oculta em mobile quando fechada */}
      <div className={`${sidebarOpen ? 'flex' : 'hidden'} md:flex flex-shrink-0`}>
        <ConversationSidebar
          conversations={conversations}
          activeId={activeConvId}
          loading={loadingConvs}
          onSelect={handleSelectConversation}
          onNew={handleNewConversation}
          onSignOut={handleSignOut}
        />
      </div>

      {/* Área principal */}
      <div className="flex flex-col flex-1 min-w-0">
        {/* Topbar mobile */}
        <header className="md:hidden flex items-center gap-3 px-4 py-3 border-b border-maia-offwhite2 bg-white">
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            aria-label="Abrir menu de conversas"
            className="text-maia-cinza hover:text-maia-escuro transition"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
          <span className="font-serif text-lg text-maia-escuro">
            Ma<em className="italic text-maia-dourado">IA</em>
          </span>
        </header>

        {/* Mensagens */}
        <main className="flex-1 overflow-y-auto px-4 py-6 space-y-4" aria-live="polite" aria-label="Histórico de mensagens">
          {messages.length === 0 && !loadingMsgs && (
            <div className="flex flex-col items-center justify-center h-full text-center py-16 gap-4">
              <div className="w-14 h-14 rounded-full bg-maia-dourado/10 flex items-center justify-center">
                <span className="font-serif text-2xl text-maia-dourado">M</span>
              </div>
              <div>
                <h2 className="font-serif text-2xl text-maia-escuro mb-1">
                  Olá! Sou a MaIA.
                </h2>
                <p className="text-sm text-maia-cinza max-w-xs">
                  Estou aqui para te ajudar com dúvidas sobre crianças de 1 a 5 anos. Como posso te apoiar hoje?
                </p>
              </div>
            </div>
          )}

          {loadingMsgs && (
            <div className="flex justify-center py-8">
              <span className="text-sm text-maia-cinza italic">Carregando mensagens...</span>
            </div>
          )}

          {messages.map((msg) => (
            <MessageBubble key={msg.id} message={msg} />
          ))}

          {sending && (
            <div className="flex items-start gap-3">
              <div className="w-8 h-8 rounded-full bg-maia-dourado flex items-center justify-center">
                <span className="font-serif text-white text-xs font-semibold">M</span>
              </div>
              <div className="bg-white rounded-lg px-4 py-3 shadow-sm border border-maia-offwhite2">
                <span className="text-maia-cinza-medio text-sm italic animate-pulse">
                  MaIA está pensando...
                </span>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </main>

        {/* Error banner */}
        {error && (
          <div role="alert" className="mx-4 mb-2 px-4 py-2 bg-red-50 border border-red-200 rounded-md text-sm text-red-700">
            {error}
          </div>
        )}

        {/* Input */}
        <footer className="border-t border-maia-offwhite2 bg-white px-4 py-3">
          <div className="max-w-3xl mx-auto flex items-end gap-3">
            <label htmlFor="chat-input" className="sr-only">
              Mensagem para a MaIA
            </label>
            <textarea
              id="chat-input"
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Digite sua mensagem… (Enter para enviar, Shift+Enter para nova linha)"
              rows={1}
              className="flex-1 resize-none rounded-md border border-maia-cinza-claro bg-maia-offwhite px-4 py-3 text-sm text-maia-escuro placeholder-maia-cinza-medio focus:outline-none focus:ring-2 focus:ring-maia-dourado focus:border-transparent transition max-h-40 overflow-y-auto"
              style={{ lineHeight: '1.5' }}
            />
            <button
              onClick={handleSend}
              disabled={!input.trim() || sending}
              aria-label="Enviar mensagem"
              className="flex-shrink-0 w-10 h-10 rounded-md bg-maia-dourado hover:bg-maia-dourado-dark disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center transition focus:outline-none focus:ring-2 focus:ring-maia-dourado focus:ring-offset-2"
            >
              <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
              </svg>
            </button>
          </div>
          <p className="text-center text-xs text-maia-cinza-medio mt-2">
            MaIA pode cometer erros. Para emergências, ligue SAMU 192 ou CVV 188.
          </p>
        </footer>
      </div>
    </div>
  );
}
