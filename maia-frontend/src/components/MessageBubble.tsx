import ReactMarkdown from 'react-markdown';
import type { Message } from '../lib/api';

interface Props {
  message: Message;
}

export default function MessageBubble({ message }: Props) {
  const isAssistant = message.role === 'assistant';

  return (
    <div className={`flex gap-3 ${isAssistant ? 'items-start' : 'items-end flex-row-reverse'}`}>
      {isAssistant && (
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-maia-dourado flex items-center justify-center shadow-sm" aria-hidden="true">
          <span className="font-serif text-white text-xs font-semibold">M</span>
        </div>
      )}

      <div
        className={`max-w-[75%] rounded-lg px-4 py-3 text-sm leading-relaxed ${
          isAssistant
            ? 'bg-white shadow-sm border border-maia-offwhite2 text-maia-escuro'
            : 'bg-maia-dourado text-white'
        }`}
      >
        {isAssistant ? (
          <div className="prose prose-sm max-w-none prose-p:my-1 prose-headings:font-serif">
            <ReactMarkdown>{message.content}</ReactMarkdown>
          </div>
        ) : (
          <p>{message.content}</p>
        )}
      </div>
    </div>
  );
}
