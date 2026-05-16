import type { Conversation } from '../lib/api';

interface Props {
  conversations: Conversation[];
  activeId: string | null;
  loading: boolean;
  onSelect: (id: string) => void;
  onNew: () => void;
  onSignOut: () => void;
  onClose?: () => void;
}

export default function ConversationSidebar({
  conversations,
  activeId,
  loading,
  onSelect,
  onNew,
  onSignOut,
  onClose,
}: Props) {
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
          <button
            key={c.id}
            onClick={() => onSelect(c.id)}
            className={`w-full text-left px-4 py-3 text-sm truncate transition ${
              c.id === activeId
                ? 'bg-white/15 text-white'
                : 'text-white/60 hover:bg-white/10 hover:text-white'
            }`}
            aria-current={c.id === activeId ? 'page' : undefined}
          >
            {c.title ?? 'Conversa'}
          </button>
        ))}
      </nav>

      {/* Footer */}
      <div className="border-t border-white/10 px-4 py-3">
        <button
          onClick={onSignOut}
          className="text-xs text-white/40 hover:text-white/70 transition"
          aria-label="Sair da conta"
        >
          Sair
        </button>
      </div>
    </aside>
  );
}
