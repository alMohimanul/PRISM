'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Plus, Loader2, FolderOpen, Trash2, Calendar, FileText, MessageSquare } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { sessionsApi } from '@/lib/api';
import { useAppStore } from '@/lib/store';
import { formatDate } from '@/lib/utils';
import type { Session } from '@/types';

export default function SessionsPage() {
  const [isCreating, setIsCreating] = useState(false);
  const [newSessionName, setNewSessionName] = useState('');
  const [newSessionTopic, setNewSessionTopic] = useState('');
  const queryClient = useQueryClient();
  const { currentSession, setCurrentSession, clearSessionMessages } = useAppStore();

  const { data: sessions, isLoading } = useQuery({
    queryKey: ['sessions'],
    queryFn: sessionsApi.list,
  });

  const createMutation = useMutation({
    mutationFn: () => sessionsApi.create(newSessionName, newSessionTopic),
    onSuccess: (session) => {
      queryClient.invalidateQueries({ queryKey: ['sessions'] });
      setCurrentSession(session);
      setIsCreating(false);
      setNewSessionName('');
      setNewSessionTopic('');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (sessionId: string) => sessionsApi.delete(sessionId),
    onSuccess: (_, sessionId) => {
      queryClient.invalidateQueries({ queryKey: ['sessions'] });
      // Clear messages for deleted session
      clearSessionMessages(sessionId);
      // If current session was deleted, clear it
      if (currentSession?.session_id === sessionId) {
        setCurrentSession(null);
      }
    },
  });

  const handleCreate = () => {
    if (newSessionName.trim()) {
      createMutation.mutate();
    }
  };

  const handleSelect = (session: Session) => {
    setCurrentSession(session);
  };

  const handleDelete = (sessionId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (confirm('Are you sure you want to delete this session?')) {
      deleteMutation.mutate(sessionId);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-glow">Sessions</h1>
          <p className="text-muted-foreground mt-1">
            Manage your research sessions
          </p>
        </div>
        <Button onClick={() => setIsCreating(true)}>
          <Plus className="h-4 w-4 mr-2" />
          New Session
        </Button>
      </div>

      {/* Create session form */}
      {isCreating && (
        <Card className="border-primary/50">
          <CardHeader>
            <CardTitle className="text-lg">Create New Session</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="text-sm font-medium mb-2 block">
                Session Name *
              </label>
              <Input
                value={newSessionName}
                onChange={(e) => setNewSessionName(e.target.value)}
                placeholder="e.g., Deep Learning Research"
              />
            </div>
            <div>
              <label className="text-sm font-medium mb-2 block">
                Topic (optional)
              </label>
              <Input
                value={newSessionTopic}
                onChange={(e) => setNewSessionTopic(e.target.value)}
                placeholder="e.g., Transformer architectures"
              />
            </div>
            <div className="flex gap-2">
              <Button
                onClick={handleCreate}
                disabled={!newSessionName.trim() || createMutation.isPending}
              >
                {createMutation.isPending ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Creating...
                  </>
                ) : (
                  'Create'
                )}
              </Button>
              <Button
                variant="outline"
                onClick={() => {
                  setIsCreating(false);
                  setNewSessionName('');
                  setNewSessionTopic('');
                }}
              >
                Cancel
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Sessions list */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      ) : sessions && sessions.length > 0 ? (
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {sessions.map((session) => (
            <Card
              key={session.session_id}
              className={`hover-glow cursor-pointer transition-all ${
                currentSession?.session_id === session.session_id
                  ? 'border-primary bg-primary/5'
                  : ''
              }`}
              onClick={() => handleSelect(session)}
            >
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <FolderOpen className="h-5 w-5 text-primary" />
                    {currentSession?.session_id === session.session_id && (
                      <div className="h-2 w-2 rounded-full bg-primary animate-pulse-glow" />
                    )}
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8"
                    onClick={(e) => handleDelete(session.session_id, e)}
                    disabled={deleteMutation.isPending}
                  >
                    <Trash2 className="h-4 w-4 text-destructive" />
                  </Button>
                </div>
                <CardTitle className="text-lg line-clamp-1">
                  {session.name}
                </CardTitle>
                {session.topic && (
                  <p className="text-sm text-muted-foreground line-clamp-2">
                    {session.topic}
                  </p>
                )}
              </CardHeader>
              <CardContent className="space-y-2 text-xs text-muted-foreground">
                <div className="flex items-center gap-2">
                  <FileText className="h-4 w-4" />
                  <span>{session.document_count} documents</span>
                </div>
                <div className="flex items-center gap-2">
                  <MessageSquare className="h-4 w-4" />
                  <span>{session.message_count} messages</span>
                </div>
                <div className="flex items-center gap-2">
                  <Calendar className="h-4 w-4" />
                  <span>{formatDate(session.updated_at)}</span>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center py-12 text-center">
          <div className="rounded-full glass p-4 mb-4">
            <FolderOpen className="h-8 w-8 text-muted-foreground" />
          </div>
          <h3 className="text-lg font-semibold">No sessions yet</h3>
          <p className="text-sm text-muted-foreground mt-2">
            Create your first session to start organizing your research
          </p>
        </div>
      )}
    </div>
  );
}
