'use client';

import { formatDate } from '@/lib/utils';
import type { Message } from '@/types';
import { User, Bot } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { ConfidenceBadge } from './confidence-badge';
import { useMemo } from 'react';
import { useAppStore } from '@/lib/store';

interface MessageBubbleProps {
  message: Message;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === 'user';
  const openPdfViewer = useAppStore((state) => state.openPdfViewer);

  // Build a map of chunk_id -> source
  const sourcesMap = useMemo(() => {
    if (!message.metadata?.sources) return {};
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const map: Record<string, any> = {};
    message.metadata.sources.forEach((source) => {
      map[source.chunk_id] = source;
    });
    return map;
  }, [message.metadata?.sources]);

  const handleCitationClick = (chunkId: string) => {
    const source = sourcesMap[chunkId];
    if (!source) return;

    console.log('Citation clicked:', {
      chunkId,
      documentId: source.document_id,
      page: source.page,
      textLength: source.text.length,
      textPreview: source.text.substring(0, 200)
    });

    // Open PDF viewer with the chunk's page and text
    // Use first 200 chars for better matching
    const highlightText = source.text
      .substring(0, 200)
      .replace(/\s+/g, ' ') // Normalize whitespace
      .trim();

    openPdfViewer(
      source.document_id,
      source.page || 1,
      highlightText
    );
  };

  // Process content to make citations clickable
  const renderContentWithCitations = (content: string) => {
    // Split by citation pattern [c1], [c2], etc.
    const parts = content.split(/(\[c\d+\])/g);

    return parts.map((part, index) => {
      const citationMatch = part.match(/\[c(\d+)\]/);

      if (citationMatch) {
        const chunkId = part.replace('[', '').replace(']', ''); // c1, c2, etc.
        const citationNumber = citationMatch[1]; // Extract the number
        const source = sourcesMap[chunkId];

        return (
          <button
            key={index}
            onClick={() => handleCitationClick(chunkId)}
            className="inline text-primary hover:text-primary/80 hover:underline cursor-pointer transition-colors"
            title={`View source in PDF (Page ${source?.page || '?'})`}
          >
            [{citationNumber}]
          </button>
        );
      }

      // Regular text - render as markdown
      return <ReactMarkdown key={index} remarkPlugins={[remarkGfm]}>{part}</ReactMarkdown>;
    });
  };

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
              {renderContentWithCitations(message.content)}
            </div>
          )}
        </div>

        {/* Timestamp */}
        <div className="text-xs text-muted-foreground px-1">
          {formatDate(message.timestamp)}
        </div>

        {/* Confidence Badge (for assistant messages) */}
        {!isUser && message.metadata?.confidence !== undefined && (
          <div className="px-1">
            <ConfidenceBadge
              confidence={message.metadata.confidence}
              unsupported_spans={message.metadata.unsupported_spans}
            />
          </div>
        )}

      </div>
    </div>
  );
}
