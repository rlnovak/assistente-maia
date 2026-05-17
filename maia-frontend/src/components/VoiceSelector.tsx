import { useState, useEffect } from 'react';
import { api } from '../lib/api';
import type { Voice } from '../lib/api';

const STORAGE_KEY = 'maia_selected_voice';

interface Props {
  value: string;
  onChange: (voiceId: string) => void;
}

export default function VoiceSelector({ value, onChange }: Props) {
  const [voices, setVoices] = useState<Voice[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.stories.voices().then((v) => {
      setVoices(v);
      setLoading(false);
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved && v.some((voice) => voice.id === saved)) {
        onChange(saved);
      } else if (v.length > 0 && !value) {
        onChange(v[0].id);
      }
    }).catch(() => setLoading(false));
  }, []);

  function handleChange(voiceId: string) {
    localStorage.setItem(STORAGE_KEY, voiceId);
    onChange(voiceId);
  }

  if (loading) {
    return <p className="text-sm text-maia-cinza-medio italic">Carregando vozes...</p>;
  }

  return (
    <div className="space-y-2">
      <label className="block text-sm font-medium text-maia-cinza">Voz da história</label>
      <div className="grid gap-2">
        {voices.map((voice) => (
          <button
            key={voice.id}
            type="button"
            onClick={() => handleChange(voice.id)}
            className={`w-full text-left px-4 py-3 rounded-md border transition ${
              value === voice.id
                ? 'border-maia-dourado bg-maia-dourado/5 text-maia-escuro'
                : 'border-maia-cinza-claro bg-maia-offwhite text-maia-cinza hover:border-maia-dourado/50'
            }`}
          >
            <span className="font-medium text-sm">{voice.name}</span>
            <span className="block text-xs text-maia-cinza-medio mt-0.5">{voice.description}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
