import { useState } from 'react';
import { api } from '../lib/api';
import type { Story, StoryGenerateRequest } from '../lib/api';

interface Props {
  onStoryGenerated: (story: Story) => void;
}

const SIZE_OPTIONS = [
  { value: 'curta', label: 'Curta', desc: '~300 palavras' },
  { value: 'media', label: 'Média', desc: '~600 palavras' },
  { value: 'longa', label: 'Longa', desc: '~1000 palavras' },
  { value: 'nao_sei', label: 'Não sei', desc: 'Estimamos pela idade' },
] as const;

export default function StoryForm({ onStoryGenerated }: Props) {
  const [childName, setChildName] = useState('');
  const [characters, setCharacters] = useState('');
  const [theme, setTheme] = useState('');
  const [lesson, setLesson] = useState('');
  const [size, setSize] = useState<'curta' | 'media' | 'longa' | 'nao_sei'>('curta');
  const [childAge, setChildAge] = useState('');
  const [reference, setReference] = useState('');
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);

    const req: StoryGenerateRequest = {
      child_name: childName.trim(),
      characters: characters.split(',').map((c) => c.trim()).filter(Boolean),
      theme: theme.trim(),
      lesson: lesson.trim(),
      size: size === 'nao_sei' ? 'curta' : size,
      reference: reference.trim() || undefined,
      child_age: size === 'nao_sei' && childAge ? parseInt(childAge) : undefined,
    };

    try {
      const story = await api.stories.generate(req);
      onStoryGenerated(story);
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Erro ao gerar história.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  }

  const isValid = childName.trim() && characters.trim() && theme.trim() && lesson.trim();

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      {/* Nome da criança */}
      <div>
        <label htmlFor="child-name" className="block text-sm font-medium text-maia-cinza mb-1">
          Nome da criança <span className="text-maia-dourado">*</span>
        </label>
        <input
          id="child-name"
          type="text"
          required
          value={childName}
          onChange={(e) => setChildName(e.target.value)}
          placeholder="Ex: Sofia"
          className="w-full px-4 py-3 rounded-md border border-maia-cinza-claro bg-maia-offwhite text-maia-escuro placeholder-maia-cinza-medio focus:outline-none focus:ring-2 focus:ring-maia-dourado focus:border-transparent transition"
        />
      </div>

      {/* Personagens */}
      <div>
        <label htmlFor="characters" className="block text-sm font-medium text-maia-cinza mb-1">
          Personagens <span className="text-maia-dourado">*</span>
        </label>
        <input
          id="characters"
          type="text"
          required
          value={characters}
          onChange={(e) => setCharacters(e.target.value)}
          placeholder="Ex: gatinho laranja, fada do bosque"
          className="w-full px-4 py-3 rounded-md border border-maia-cinza-claro bg-maia-offwhite text-maia-escuro placeholder-maia-cinza-medio focus:outline-none focus:ring-2 focus:ring-maia-dourado focus:border-transparent transition"
        />
        <p className="text-xs text-maia-cinza-medio mt-1">Separe com vírgula</p>
      </div>

      {/* Tema */}
      <div>
        <label htmlFor="theme" className="block text-sm font-medium text-maia-cinza mb-1">
          Tema da história <span className="text-maia-dourado">*</span>
        </label>
        <input
          id="theme"
          type="text"
          required
          value={theme}
          onChange={(e) => setTheme(e.target.value)}
          placeholder="Ex: o gatinho aprende a compartilhar seus brinquedos"
          className="w-full px-4 py-3 rounded-md border border-maia-cinza-claro bg-maia-offwhite text-maia-escuro placeholder-maia-cinza-medio focus:outline-none focus:ring-2 focus:ring-maia-dourado focus:border-transparent transition"
        />
      </div>

      {/* Lição */}
      <div>
        <label htmlFor="lesson" className="block text-sm font-medium text-maia-cinza mb-1">
          Lição ou valor <span className="text-maia-dourado">*</span>
        </label>
        <input
          id="lesson"
          type="text"
          required
          value={lesson}
          onChange={(e) => setLesson(e.target.value)}
          placeholder="Ex: compartilhar traz amizades e alegria"
          className="w-full px-4 py-3 rounded-md border border-maia-cinza-claro bg-maia-offwhite text-maia-escuro placeholder-maia-cinza-medio focus:outline-none focus:ring-2 focus:ring-maia-dourado focus:border-transparent transition"
        />
      </div>

      {/* Tamanho */}
      <div>
        <label className="block text-sm font-medium text-maia-cinza mb-2">
          Tamanho <span className="text-maia-dourado">*</span>
        </label>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          {SIZE_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              type="button"
              onClick={() => setSize(opt.value)}
              className={`px-3 py-2 rounded-md border text-sm transition ${
                size === opt.value
                  ? 'border-maia-dourado bg-maia-dourado/10 text-maia-escuro font-medium'
                  : 'border-maia-cinza-claro bg-maia-offwhite text-maia-cinza hover:border-maia-dourado/50'
              }`}
            >
              <span className="block font-medium">{opt.label}</span>
              <span className="block text-xs text-maia-cinza-medio">{opt.desc}</span>
            </button>
          ))}
        </div>

        {size === 'nao_sei' && (
          <div className="mt-3">
            <label htmlFor="child-age" className="block text-sm text-maia-cinza mb-1">
              Idade da criança (para estimar o tamanho)
            </label>
            <input
              id="child-age"
              type="number"
              min={1}
              max={10}
              value={childAge}
              onChange={(e) => setChildAge(e.target.value)}
              placeholder="Ex: 3"
              className="w-32 px-4 py-2 rounded-md border border-maia-cinza-claro bg-maia-offwhite text-maia-escuro focus:outline-none focus:ring-2 focus:ring-maia-dourado transition"
            />
          </div>
        )}
      </div>

      {/* Referência criativa (opcional) */}
      <div>
        <button
          type="button"
          onClick={() => setShowAdvanced(!showAdvanced)}
          className="text-sm text-maia-dourado hover:text-maia-dourado-dark transition flex items-center gap-1"
        >
          <svg className={`w-4 h-4 transition-transform ${showAdvanced ? 'rotate-90' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
          {showAdvanced ? 'Ocultar' : 'Inspiração criativa'} (opcional)
        </button>

        {showAdvanced && (
          <div className="mt-3">
            <textarea
              value={reference}
              onChange={(e) => setReference(e.target.value)}
              placeholder='Ex: "Como Chapeuzinho Vermelho, mas a protagonista é uma gatinha chamada Mimi que visita a vovó no bosque encantado."'
              rows={3}
              className="w-full px-4 py-3 rounded-md border border-maia-cinza-claro bg-maia-offwhite text-maia-escuro placeholder-maia-cinza-medio focus:outline-none focus:ring-2 focus:ring-maia-dourado focus:border-transparent transition resize-none text-sm"
            />
          </div>
        )}
      </div>

      {error && (
        <p role="alert" className="text-sm text-red-600 bg-red-50 rounded-md px-3 py-2">
          {error}
        </p>
      )}

      <button
        type="submit"
        disabled={!isValid || loading}
        className="w-full py-3 px-6 rounded-md bg-maia-dourado text-white font-medium text-sm tracking-wide transition hover:bg-maia-dourado-dark disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-maia-dourado focus:ring-offset-2"
      >
        {loading ? (
          <span className="flex items-center justify-center gap-2">
            <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
            </svg>
            Criando história...
          </span>
        ) : (
          'Criar história'
        )}
      </button>
    </form>
  );
}
