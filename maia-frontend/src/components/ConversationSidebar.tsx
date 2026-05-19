import { useState, useRef, useEffect, useCallback } from 'react';
import type { Conversation } from '../lib/api';

interface ContextMenuState {
  convId: string;
  x: number;
  y: number;
}

interface Props {
  conversations: Conversation[];
  activeId: string | null;
  loading: boolean;
  onSelect: (id: string) => void;
  onNew: () => void;
  onSignOut: () => void;
  onClose?: () => void;
  onRename: (id: string, title: string) => void;
  onDelete: (id: string) => void;
  onExport: (id: string) => void;
}

export default function ConversationSidebar({
  conversations,
  activeId,
  loading,
  onSelect,
  onNew,
  onSignOut,
  onClose,
  onRename,
  onDelete,
  onExport,
}: Props) {
  const [contextMenu, setContextMenu] = useState<ContextMenuState | null>(null);
  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState('');
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const renameInputRef = useRef<HTMLInputElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);

  // close context menu on outside click
  useEffect(() => {
    if (!contextMenu) return;
    function handleClick(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setContextMenu(null);
      }
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, [contextMenu]);

  // focus rename input
  useEffect(() => {
    if (renamingId) renameInputRef.current?.focus();
  }, [renamingId]);

  // auto-hide toast
  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast(null), 2000);
    return () => clearTimeout(t);
  }, [toast]);

  function handleContextMenu(e: React.MouseEvent, conv: Conversation) {
    e.preventDefault();
    e.stopPropagation();
    setContextMenu({ convId: conv.id, x: e.clientX, y: e.clientY });
    setRenamingId(null);
    setDeleteConfirmId(null);
  }

  function startRename(conv: Conversation) {
    setContextMenu(null);
    setRenameValue(conv.title ?? '');
    setRenamingId(conv.id);
  }

  function commitRename(id: string) {
    const trimmed = renameValue.trim();
    if (trimmed) onRename(id, trimmed);
    setRenamingId(null);
  }

  function handleRenameKeyDown(e: React.KeyboardEvent, id: string) {
    if (e.key === 'Enter') commitRename(id);
    if (e.key === 'Escape') setRenamingId(null);
  }

  async function handleExport(id: string) {
    setContextMenu(null);
    await onExport(id);
    setToast('Copiado!');
  }

  function requestDelete(id: string) {
    setContextMenu(null);
    setDeleteConfirmId(id);
  }

  function confirmDelete(id: string) {
    setDeleteConfirmId(null);
    onDelete(id);
  }

  return (
    <aside className="flex flex-col w-64 bg-maia-escuro text-maia-offwhite h-full" aria-label="Conversas">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-4 border-b border-white/10">
        <span className="font-serif text-xl font-light tracking-wide">
          Ma<em className="italic text-maia-dourado">IA</em>
        </span>
        <div className="flex items-center gap-2">
          <button
            onClick={onNew}
            className="w-7 h-7 rounded-md bg-white/10 hover:bg-white/20 flex items-center justify-center transition"
            aria-label="Nova conversa"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
          </button>
          {onClose && (
            <button
              onClick={onClose}
              className="md:hidden w-7 h-7 rounded-md bg-white/10 hover:bg-white/20 flex items-center justify-center transition"
              aria-label="Fechar menu"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          )}
        </div>
      </div>

      {/* Lista de conversas */}
      <nav className="flex-1 overflow-y-auto py-2" aria-label="Histórico de conversas">
        {loading && (
          <p className="px-4 py-3 text-xs text-white/40">Carregando...</p>
        )}
        {!loading && conversations.length === 0 && (
          <p className="px-4 py-3 text-xs text-white/40 italic">Nenhuma conversa ainda.</p>
        )}
        {conversations.map((c) => (
          <div key={c.id} className="relative group">
            {renamingId === c.id ? (
              <div className="px-3 py-2">
                <input
                  ref={renameInputRef}
                  value={renameValue}
                  onChange={(e) => setRenameValue(e.target.value)}
                  onBlur={() => commitRename(c.id)}
                  onKeyDown={(e) => handleRenameKeyDown(e, c.id)}
                  className="w-full bg-white/10 text-white text-sm rounded px-2 py-1 outline-none focus:ring-1 focus:ring-maia-dourado"
                />
              </div>
            ) : (
              <button
                onClick={() => onSelect(c.id)}
                onContextMenu={(e) => handleContextMenu(e, c)}
                className={`w-full text-left px-4 py-3 text-sm truncate transition ${
                  c.id === activeId
                    ? 'bg-white/15 text-white'
                    : 'text-white/60 hover:bg-white/10 hover:text-white'
                }`}
                aria-current={c.id === activeId ? 'page' : undefined}
              >
                {c.title ?? 'Conversa'}
              </button>
            )}

            {/* Delete confirm inline */}
            {deleteConfirmId === c.id && (
              <div className="mx-3 mb-2 bg-white/5 rounded p-2 text-xs text-white/80">
                <p className="mb-2">Apagar esta conversa?</p>
                <div className="flex gap-2">
                  <button
                    onClick={() => confirmDelete(c.id)}
                    className="flex-1 bg-red-600 hover:bg-red-700 text-white rounded px-2 py-1 transition"
                  >
                    Apagar
                  </button>
                  <button
                    onClick={() => setDeleteConfirmId(null)}
                    className="flex-1 bg-white/10 hover:bg-white/20 text-white rounded px-2 py-1 transition"
                  >
                    Cancelar
                  </button>
                </div>
              </div>
            )}
          </div>
        ))}
      </nav>

      {/* Footer */}
      <div className="border-t border-white/10 px-4 py-3 space-y-2">
        <a
          href="/stories"
          className="flex items-center gap-2 text-xs text-white/50 hover:text-white/80 transition"
        >
          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
          </svg>
          Histórias infantis
        </a>
        <button
          onClick={onSignOut}
          className="text-xs text-white/40 hover:text-white/70 transition"
          aria-label="Sair da conta"
        >
          Sair
        </button>
      </div>

      {/* Context menu — fixed, outside sidebar flow */}
      {contextMenu && (
        <div
          ref={menuRef}
          style={{ position: 'fixed', top: contextMenu.y, left: contextMenu.x, zIndex: 9999 }}
          className="bg-maia-escuro border border-white/20 rounded-md shadow-xl py-1 min-w-[160px]"
        >
          {(() => {
            const conv = conversations.find((c) => c.id === contextMenu.convId);
            if (!conv) return null;
            return (
              <>
                <button
                  onClick={() => startRename(conv)}
                  className="w-full text-left px-4 py-2 text-sm text-white/80 hover:bg-white/10 transition"
                >
                  Renomear
                </button>
                <button
                  onClick={() => handleExport(conv.id)}
                  className="w-full text-left px-4 py-2 text-sm text-white/80 hover:bg-white/10 transition"
                >
                  Copiar transcrição
                </button>
                <button
                  onClick={() => requestDelete(conv.id)}
                  className="w-full text-left px-4 py-2 text-sm text-red-400 hover:bg-white/10 transition"
                >
                  Apagar
                </button>
              </>
            );
          })()}
        </div>
      )}

      {/* Toast */}
      {toast && (
        <div
          style={{ position: 'fixed', bottom: 24, left: '50%', transform: 'translateX(-50%)', zIndex: 9999 }}
          className="bg-maia-escuro border border-white/20 rounded-full px-4 py-2 text-sm text-white shadow-lg"
        >
          {toast}
        </div>
      )}
    </aside>
  );
}
