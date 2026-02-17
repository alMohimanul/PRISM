'use client';

import { useEffect, useRef, useState, useCallback, useMemo } from 'react';
import { useMutation } from '@tanstack/react-query';
import { MessageBubble } from './message';
import { ChatInput } from './chat-input';
import { useAppStore } from '@/lib/store';
import { chatApi } from '@/lib/api';
import type { Message } from '@/types';
import { Bot } from 'lucide-react';

export function ChatContainer() {
  const { currentSession, addMessage, getSessionMessages, selectedDocuments } = useAppStore();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const [shouldAutoScroll, setShouldAutoScroll] = useState(true);

  // Get messages for current session from store
  const messages = useMemo(() => {
    return currentSession ? getSessionMessages(currentSession.session_id) : [];
  }, [currentSession, getSessionMessages]);

  // Auto-scroll to bottom when new messages arrive (only if user is near bottom)
  const scrollToBottom = useCallback(() => {
    if (shouldAutoScroll) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [shouldAutoScroll]);

  // Check if user is near the bottom of the scroll container
  const handleScroll = () => {
    if (!scrollContainerRef.current) return;

    const { scrollTop, scrollHeight, clientHeight } = scrollContainerRef.current;
    const isNearBottom = scrollHeight - scrollTop - clientHeight < 100;

    setShouldAutoScroll(isNearBottom);
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  // Send message mutation
  const sendMessageMutation = useMutation({
    mutationFn: async (message: string) => {
      if (!currentSession) throw new Error('No session selected');

      // Add user message immediately to store
      const userMessage: Message = {
        role: 'user',
        content: message,
        timestamp: new Date().toISOString(),
      };
      addMessage(currentSession.session_id, userMessage);

      // Call API with selected documents if any
      const documentIds = selectedDocuments.size > 0 ? Array.from(selectedDocuments) : undefined;
      const response = await chatApi.sendMessage(currentSession.session_id, message, undefined, documentIds);

      // Add assistant response to store
      const assistantMessage: Message = {
        role: 'assistant',
        content: response.message,
        timestamp: response.timestamp,
        metadata: {
          sources: response.sources,
          confidence: response.confidence,
          unsupported_spans: response.unsupported_spans,
        },
      };
      addMessage(currentSession.session_id, assistantMessage);

      return response;
    },
    onError: (error) => {
      console.error('Error sending message:', error);
      // TODO: Show error toast
    },
  });

  const handleSend = (message: string) => {
    sendMessageMutation.mutate(message);
  };

  // Empty state
  if (!currentSession) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-4 text-center">
        <Bot className="h-16 w-16 text-primary/50" />
        <div>
          <h3 className="text-lg font-semibold text-glow">No Active Session</h3>
          <p className="text-sm text-muted-foreground mt-2">
            Create or select a session to start chatting
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col overflow-hidden">
      {/* Messages - Scrollable Container */}
      <div
        ref={scrollContainerRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto overflow-x-hidden pr-4 scrollbar-thin scrollbar-thumb-primary/30 scrollbar-track-transparent hover:scrollbar-thumb-primary/50"
      >
        <div className="space-y-6 py-4">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center gap-4 py-12 text-center">
              <Bot className="h-12 w-12 text-primary/50" />
              <div>
                <h3 className="text-lg font-semibold">Start a Conversation</h3>
                <p className="text-sm text-muted-foreground mt-2">
                  Ask questions about your uploaded research papers
                </p>
              </div>
            </div>
          ) : (
            messages.map((message, idx: number) => (
              <MessageBubble key={idx} message={message} />
            ))
          )}
          {sendMessageMutation.isPending && (
            <div className="flex gap-4">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded terminal-border bg-primary/20">
                <Bot className="h-4 w-4 text-primary" />
              </div>
              <div className="flex-1">
                <div className="inline-block rounded-lg code-block px-4 py-3">
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <span>Thinking</span>
                    <div className="loading-dots">
                      <span></span>
                      <span></span>
                      <span></span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
          {/* Invisible element at the bottom to scroll to */}
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input - Fixed at Bottom */}
      <div className="flex-shrink-0 border-t border-matrix-border/50 pt-4 mt-4">
        <ChatInput
          onSend={handleSend}
          isLoading={sendMessageMutation.isPending}
          disabled={!currentSession}
        />
      </div>
    </div>
  );
}
