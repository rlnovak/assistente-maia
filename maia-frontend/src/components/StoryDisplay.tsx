import { useState } from 'react';
import { api } from '../lib/api';
import type { Story, StoryAudio } from '../lib/api';
import VoiceSelector from './VoiceSelector';

interface Props {
  story: Story;
  onRated?: (updated: Story) => void;
  onBack?: () => void;
}

function StarRating({ value, onChange }: { value: number | null; onChange: (n: number) => void }) {
  const [hovered, setHovered] = useState<number | null>(null);
  return (
    <div className="flex gap-1" aria-label="Avaliação">
      {[1, 2, 3, 4, 5].map((star) => (
        <button
          key={star}
          type="button"
          onClick={() => onChange(star)}
          onMouseEnter={() => setHovered(star)}
          onMouseLeave={() => setHovered(null)}
          aria-label={`${star} estrela${star > 1 ? 's' : ''}`}
          className="text-2xl transition focus:outline-none"
        >
          <span className={(hovered ?? value ?? 0) >= star ? 'text-maia-dourado' : 'text-maia-cinza-claro'}>
            ★
          </span>
        </button>
      ))}
    </div>
  );
}

export default function StoryDisplay({ story: initialStory, onRated, onBack }: Props) {
  const [story, setStory] = useState(initialStory);
  const [rating, setRating] = useState<number>(story.rating ?? 0);
  const [ratingNotes, setRatingNotes] = useState(story.rating_notes ?? '');
  const [ratingSubmitted, setRatingSubmitted] = useState(!!story.rating);
  const [ratingLoading, setRatingLoading] = useState(false);

  const [selectedVoice, setSelectedVoice] = useState('');
  const [audioLoading, setAudioLoading] = useState(false);
  const [audio, setAudio] = useState<StoryAudio | null>(null);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [audioError, setAudioError] = useState<string | null>(null);
  const [showVoicePanel, setShowVoicePanel] = useState(false);

  async function handleRatingSubmit() {
    if (!rating) return;
    setRatingLoading(true);
    try {
      const updated = await api.stories.rate(story.id, rating, ratingNotes || undefined);
      setStory(updated);
      setRatingSubmitted(true);
      onRated?.(updated);
    } catch {
      // silent
    } finally {
      setRatingLoading(false);
    }
  }

  async function handleGenerateAudio() {
    if (!selectedVoice) return;
    setAudioLoading(true);
    setAudioError(null);
    try {
      const result = await api.stories.generateAudio(story.id, selectedVoice);
      setAudio(result);
      const urlResult = await api.stories.getAudioUrl(story.id);
      setAudioUrl(urlResult.url);
      setShowVoicePanel(false);
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Erro ao gerar áudio.';
      setAudioError(msg);
    } finally {
      setAudioLoading(false);
    }
  }

  const expiresIn = audio
    ? Math.ceil((new Date(audio.expires_at).getTime() - Date.now()) / (1000 * 60 * 60 * 24))
    : null;

  return (
    <div className="space-y-6">
      {/* Botão voltar */}
      {onBack && (
        <button
          onClick={onBack}
          className="flex items-center gap-1 text-sm text-maia-cinza hover:text-maia-escuro transition"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          Voltar
        </button>
      )}

      {/* Cabeçalho */}
      <div className="text-center pt-2">
        <h2 className="font-serif text-2xl text-maia-escuro">{story.titulo}</h2>
        {story.tags.length > 0 && (
          <div className="flex flex-wrap justify-center gap-1 mt-2">
            {story.tags.map((tag) => (
              <span key={tag} className="text-xs px-2 py-0.5 rounded-full bg-maia-dourado/10 text-maia-dourado-dark">
                {tag}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Texto da história */}
      <div className="bg-white rounded-xl p-6 shadow-sm border border-maia-offwhite2">
        {story.historia?.split('\n\n').map((paragraph, i) => (
          <p key={i} className="text-maia-escuro leading-relaxed mb-4 last:mb-0 font-serif text-lg">
            {paragraph}
          </p>
        ))}
      </div>

      {/* Moral */}
      {story.moral && (
        <div className="bg-maia-dourado/5 border border-maia-dourado/20 rounded-lg px-5 py-4">
          <p className="text-sm font-medium text-maia-dourado-dark mb-1">Moral da história</p>
          <p className="text-maia-cinza italic">"{story.moral}"</p>
        </div>
      )}

      {/* Áudio */}
      <div className="bg-white rounded-xl p-5 border border-maia-offwhite2 shadow-sm space-y-3">
        <p className="text-sm font-medium text-maia-cinza">Ouvir a história</p>

        {audioUrl ? (
          <div className="space-y-3">
            <audio controls className="w-full" src={audioUrl}>
              Seu navegador não suporta o player de áudio.
            </audio>
            {expiresIn !== null && (
              <p className="text-xs text-maia-cinza-medio">
                Áudio disponível por mais {expiresIn} dia{expiresIn !== 1 ? 's' : ''}.
              </p>
            )}
            <a
              href={audioUrl}
              download={`${story.titulo ?? 'historia'}.mp3`}
              className="inline-flex items-center gap-2 text-sm text-maia-dourado hover:text-maia-dourado-dark transition"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
              </svg>
              Baixar áudio
            </a>
          </div>
        ) : (
          <div className="space-y-3">
            {!showVoicePanel ? (
              <button
                onClick={() => setShowVoicePanel(true)}
                className="flex items-center gap-2 px-4 py-2 rounded-md bg-maia-dourado text-white text-sm font-medium hover:bg-maia-dourado-dark transition"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.536 8.464a5 5 0 010 7.072M12 9v6m-3.536-4.536a5 5 0 000 7.072" />
                </svg>
                Gerar áudio
              </button>
            ) : (
              <div className="space-y-4">
                <VoiceSelector value={selectedVoice} onChange={setSelectedVoice} />
                {audioError && (
                  <p className="text-sm text-red-600 bg-red-50 rounded px-3 py-2">{audioError}</p>
                )}
                <div className="flex gap-2">
                  <button
                    onClick={handleGenerateAudio}
                    disabled={!selectedVoice || audioLoading}
                    className="px-4 py-2 rounded-md bg-maia-dourado text-white text-sm font-medium hover:bg-maia-dourado-dark disabled:opacity-50 transition"
                  >
                    {audioLoading ? 'Gerando...' : 'Gerar com essa voz'}
                  </button>
                  <button
                    onClick={() => setShowVoicePanel(false)}
                    className="px-4 py-2 rounded-md border border-maia-cinza-claro text-maia-cinza text-sm hover:border-maia-cinza transition"
                  >
                    Cancelar
                  </button>
                </div>
              </div>
            )}
            <p className="text-xs text-maia-cinza-medio">O áudio ficará disponível por 7 dias.</p>
          </div>
        )}
      </div>

      {/* Rating */}
      <div className="bg-white rounded-xl p-5 border border-maia-offwhite2 shadow-sm space-y-3">
        <p className="text-sm font-medium text-maia-cinza">
          {ratingSubmitted ? 'Sua avaliação' : 'O que você achou da história?'}
        </p>
        <StarRating value={rating || null} onChange={setRating} />
        {!ratingSubmitted && (
          <>
            <textarea
              value={ratingNotes}
              onChange={(e) => setRatingNotes(e.target.value)}
              placeholder="Algum comentário? (opcional)"
              rows={2}
              className="w-full px-3 py-2 rounded-md border border-maia-cinza-claro bg-maia-offwhite text-sm text-maia-escuro placeholder-maia-cinza-medio focus:outline-none focus:ring-2 focus:ring-maia-dourado transition resize-none"
            />
            <button
              onClick={handleRatingSubmit}
              disabled={!rating || ratingLoading}
              className="px-4 py-2 rounded-md bg-maia-dourado text-white text-sm font-medium hover:bg-maia-dourado-dark disabled:opacity-50 transition"
            >
              {ratingLoading ? 'Salvando...' : 'Salvar avaliação'}
            </button>
          </>
        )}
        {ratingSubmitted && (
          <p className="text-xs text-maia-cinza-medio">Obrigada pela avaliação!</p>
        )}
      </div>
    </div>
  );
}
