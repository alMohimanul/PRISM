'use client';

import { formatDate } from '@/lib/utils';
import type { Message } from '@/types';
import { User, Bot } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface MessageBubbleProps {
  message: Message;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === 'user';

  return (
    <div className={`flex gap-4 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
      {/* Avatar */}
      <div
        className={`flex h-8 w-8 shrink-0 items-center justify-center rounded terminal-border ${
          isUser ? 'bg-secondary/20' : 'bg-primary/20'
        }`}
      >
        {isUser ? (
          <User className="h-4 w-4 text-secondary" />
        ) : (
          <Bot className="h-4 w-4 text-primary" />
        )}
      </div>

      {/* Message content */}
      <div className={`flex-1 space-y-2 ${isUser ? 'text-right' : 'text-left'}`}>
        <div
          className={`inline-block max-w-[80%] rounded-lg px-4 py-3 ${
            isUser
              ? 'glass border border-secondary/30'
              : 'code-block'
          }`}
        >
          {isUser ? (
            <p className="text-sm">{message.content}</p>
          ) : (
            <div className="prose prose-invert prose-sm max-w-none">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {message.content}
              </ReactMarkdown>
            </div>
          )}
        </div>

        {/* Timestamp */}
        <div className="text-xs text-muted-foreground px-1">
          {formatDate(message.timestamp)}
        </div>

        {/* Sources */}
        {message.metadata?.sources && message.metadata.sources.length > 0 && (
          <div className="space-y-2 mt-2">
            <p className="text-xs text-muted-foreground px-1">
              Sources ({message.metadata.sources.length}):
            </p>
            <div className="flex flex-wrap gap-2">
              {message.metadata.sources.map((source, idx) => (
                <div
                  key={idx}
                  className="terminal-border rounded px-2 py-1 text-xs bg-matrix-surface/50 hover-glow cursor-pointer"
                >
                  <span className="text-primary">[{idx + 1}]</span>{' '}
                  <span className="text-muted-foreground">
                    {source.document_id.substring(0, 8)}...
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
