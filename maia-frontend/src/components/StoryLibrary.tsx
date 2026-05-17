import { useState, useEffect, useCallback } from 'react';
import { api } from '../lib/api';
import type { Story } from '../lib/api';

interface Props {
  onSelectStory: (story: Story) => void;
  refreshTrigger?: number;
}

function StoryCard({ story, onClick }: { story: Story; onClick: () => void }) {
  const hasAudio = false; // será verificado via estado futuro
  const stars = story.rating ?? 0;

  return (
    <button
      onClick={onClick}
      className="w-full text-left bg-white rounded-xl p-4 border border-maia-offwhite2 shadow-sm hover:border-maia-dourado/40 hover:shadow-md transition group"
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <h3 className="font-serif text-base text-maia-escuro truncate group-hover:text-maia-dourado-dark transition">
            {story.titulo ?? 'História sem título'}
          </h3>
          <p className="text-xs text-maia-cinza-medio mt-0.5">
            {story.child_name} · {new Date(story.created_at).toLocaleDateString('pt-BR')}
          </p>
        </div>
        {stars > 0 && (
          <span className="flex-shrink-0 text-maia-dourado text-sm">
            {'★'.repeat(stars)}{'☆'.repeat(5 - stars)}
          </span>
        )}
      </div>

      {story.tags.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-2">
          {story.tags.slice(0, 3).map((tag) => (
            <span key={tag} className="text-xs px-2 py-0.5 rounded-full bg-maia-offwhite2 text-maia-cinza">
              {tag}
            </span>
          ))}
        </div>
      )}

      <p className="text-xs text-maia-cinza-claro mt-2 capitalize">{story.size}</p>
    </button>
  );
}

export default function StoryLibrary({ onSelectStory, refreshTrigger }: Props) {
  const [stories, setStories] = useState<Story[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterName, setFilterName] = useState('');
  const [filterTag, setFilterTag] = useState('');
  const [allTags, setAllTags] = useState<string[]>([]);

  const loadStories = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.stories.list({
        child_name: filterName || undefined,
        tag: filterTag || undefined,
      });
      setStories(data);

      // Coleta todas as tags únicas para o filtro
      const tags = Array.from(new Set(data.flatMap((s) => s.tags))).sort();
      setAllTags(tags);
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  }, [filterName, filterTag]);

  useEffect(() => {
    loadStories();
  }, [loadStories, refreshTrigger]);

  if (loading) {
    return (
      <div className="flex justify-center py-12">
        <p className="text-sm text-maia-cinza-medio italic">Carregando histórias...</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Filtros */}
      <div className="flex flex-col sm:flex-row gap-2">
        <input
          type="text"
          value={filterName}
          onChange={(e) => setFilterName(e.target.value)}
          placeholder="Filtrar por nome da criança"
          className="flex-1 px-3 py-2 rounded-md border border-maia-cinza-claro bg-maia-offwhite text-sm text-maia-escuro placeholder-maia-cinza-medio focus:outline-none focus:ring-2 focus:ring-maia-dourado transition"
        />
        {allTags.length > 0 && (
          <select
            value={filterTag}
            onChange={(e) => setFilterTag(e.target.value)}
            className="px-3 py-2 rounded-md border border-maia-cinza-claro bg-maia-offwhite text-sm text-maia-escuro focus:outline-none focus:ring-2 focus:ring-maia-dourado transition"
          >
            <option value="">Todos os temas</option>
            {allTags.map((tag) => (
              <option key={tag} value={tag}>{tag}</option>
            ))}
          </select>
        )}
      </div>

      {/* Lista */}
      {stories.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-maia-cinza-medio text-sm">
            {filterName || filterTag ? 'Nenhuma história encontrada com esses filtros.' : 'Nenhuma história criada ainda.'}
          </p>
        </div>
      ) : (
        <div className="grid gap-3">
          {stories.map((story) => (
            <StoryCard key={story.id} story={story} onClick={() => onSelectStory(story)} />
          ))}
        </div>
      )}
    </div>
  );
}
