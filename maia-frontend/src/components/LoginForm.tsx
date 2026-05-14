import { useState } from 'react';
import { supabase } from '../lib/supabase';

export default function LoginForm() {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);

    const { error } = await supabase.auth.signInWithOtp({
      email,
      options: {
        emailRedirectTo: `${window.location.origin}/auth/callback`,
      },
    });

    setLoading(false);
    if (error) {
      setError('Não foi possível enviar o link. Tente novamente.');
    } else {
      setSent(true);
    }
  }

  if (sent) {
    return (
      <div className="text-center py-4">
        <div className="w-12 h-12 rounded-full bg-maia-verde-light flex items-center justify-center mx-auto mb-4">
          <svg className="w-6 h-6 text-maia-verde" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        </div>
        <h2 className="font-serif text-xl text-maia-escuro mb-2">Link enviado!</h2>
        <p className="text-sm text-maia-cinza">
          Verifique o e-mail <strong>{email}</strong> e clique no link para entrar.
        </p>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      <div>
        <label htmlFor="email" className="block text-sm font-medium text-maia-cinza mb-2">
          E-mail
        </label>
        <input
          id="email"
          type="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="seu@email.com"
          className="w-full px-4 py-3 rounded-md border border-maia-cinza-claro bg-maia-offwhite text-maia-escuro placeholder-maia-cinza-medio focus:outline-none focus:ring-2 focus:ring-maia-dourado focus:border-transparent transition"
          aria-label="Endereço de e-mail"
        />
      </div>

      {error && (
        <p role="alert" className="text-sm text-red-600 bg-red-50 rounded-md px-3 py-2">
          {error}
        </p>
      )}

      <button
        type="submit"
        disabled={loading || !email}
        className="w-full py-3 px-6 rounded-md bg-maia-dourado text-white font-medium text-sm tracking-wide transition hover:bg-maia-dourado-dark disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-maia-dourado focus:ring-offset-2"
      >
        {loading ? 'Enviando...' : 'Enviar link de acesso'}
      </button>
    </form>
  );
}
