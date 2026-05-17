import { useState, useEffect } from 'react';
import { supabase } from '../lib/supabase';
import type { Story } from '../lib/api';
import StoryForm from './StoryForm';
import StoryDisplay from './StoryDisplay';
import StoryLibrary from './StoryLibrary';

type Tab = 'nova' | 'biblioteca';
type View = 'form' | 'story';

export default function StoriesApp() {
  const [authChecked, setAuthChecked] = useState(false);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [tab, setTab] = useState<Tab>('nova');
  const [view, setView] = useState<View>('form');
  const [currentStory, setCurrentStory] = useState<Story | null>(null);
  const [libraryRefresh, setLibraryRefresh] = useState(0);

  useEffect(() => {
    const { data: { subscription } } = supabase.auth.onAuthStateChange((event, session) => {
      if (event === 'SIGNED_OUT') {
        window.location.href = '/login';
        return;
      }
      if (session) {
        setIsAuthenticated(true);
        setAuthChecked(true);
      } else if (event === 'INITIAL_SESSION') {
        window.location.href = '/login';
      }
    });
    return () => subscription.unsubscribe();
  }, []);

  function handleStoryGenerated(story: Story) {
    setCurrentStory(story);
    setView('story');
    setLibraryRefresh((n) => n + 1);
  }

  function handleSelectFromLibrary(story: Story) {
    setCurrentStory(story);
    setView('story');
    setTab('nova');
  }

  function handleBack() {
    setView('form');
    setCurrentStory(null);
  }

  async function handleSignOut() {
    await supabase.auth.signOut();
  }

  if (!authChecked) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-maia-offwhite">
        <p className="font-serif italic text-maia-cinza text-lg">Verificando sessão...</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-maia-offwhite flex flex-col">
      {/* Header */}
      <header className="bg-white border-b border-maia-offwhite2 px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <a
            href="/chat"
            className="flex items-center gap-1.5 text-sm text-maia-cinza hover:text-maia-escuro transition"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            Chat
          </a>
          <span className="font-serif text-lg text-maia-escuro">
            Ma<em className="italic text-maia-dourado">IA</em>
            <span className="text-maia-cinza-medio font-sans text-sm font-normal ml-2">· Histórias</span>
          </span>
        </div>
        <button
          onClick={handleSignOut}
          className="text-xs text-maia-cinza-medio hover:text-maia-cinza transition"
        >
          Sair
        </button>
      </header>

      {/* Tabs */}
      <div className="bg-white border-b border-maia-offwhite2 px-4">
        <div className="flex gap-0 max-w-2xl mx-auto">
          {(['nova', 'biblioteca'] as Tab[]).map((t) => (
            <button
              key={t}
              onClick={() => { setTab(t); if (t === 'nova' && view === 'story') setView('form'); }}
              className={`px-4 py-3 text-sm font-medium border-b-2 transition ${
                tab === t
                  ? 'border-maia-dourado text-maia-escuro'
                  : 'border-transparent text-maia-cinza-medio hover:text-maia-cinza'
              }`}
            >
              {t === 'nova' ? 'Nova história' : 'Minhas histórias'}
            </button>
          ))}
        </div>
      </div>

      {/* Conteúdo */}
      <main className="flex-1 overflow-y-auto px-4 py-6">
        <div className="max-w-2xl mx-auto">
          {tab === 'nova' && (
            <>
              {view === 'form' && (
                <div className="space-y-4">
                  <div>
                    <h1 className="font-serif text-2xl text-maia-escuro">Criar uma história</h1>
                    <p className="text-sm text-maia-cinza-medio mt-1">
                      Preencha os campos abaixo e a MaIA vai criar uma história personalizada.
                    </p>
                  </div>
                  <StoryForm onStoryGenerated={handleStoryGenerated} />
                </div>
              )}
              {view === 'story' && currentStory && (
                <StoryDisplay
                  story={currentStory}
                  onBack={handleBack}
                  onRated={(updated) => setCurrentStory(updated)}
                />
              )}
            </>
          )}

          {tab === 'biblioteca' && (
            <div className="space-y-4">
              <h1 className="font-serif text-2xl text-maia-escuro">Minhas histórias</h1>
              <StoryLibrary
                onSelectStory={handleSelectFromLibrary}
                refreshTrigger={libraryRefresh}
              />
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
