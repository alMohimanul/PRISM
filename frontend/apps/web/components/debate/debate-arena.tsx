'use client';

import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { debateApi } from '@/lib/api';
import { DebateResponse } from '@/types';
import { DebateHeader } from './debate-header';
import { DebateTeamCard } from './debate-team-card';
import { DebateRoundCard } from './debate-round-card';
import { DebateScoreboard } from './debate-scoreboard';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Swords, Sparkles } from 'lucide-react';

interface DebateArenaProps {
  documentIds: string[];
  documents: Map<string, any>; // Document ID to Document mapping
}

export function DebateArena({ documentIds, documents }: DebateArenaProps) {
  const [debateResult, setDebateResult] = useState<DebateResponse | null>(null);
  const [currentRound, setCurrentRound] = useState(0);

  const startDebateMutation = useMutation({
    mutationFn: async () => {
      return await debateApi.startDebate(
        documentIds,
        undefined, // Auto-detect topic
        3, // 3 rounds (reduced for rate limiting)
        'high' // Maximum humor! 🔥
      );
    },
    onSuccess: (data) => {
      setDebateResult(data);
      setCurrentRound(0);
    },
    onError: (error) => {
      console.error('Debate failed:', error);
    },
  });

  const handleStartDebate = () => {
    startDebateMutation.mutate();
  };

  const showNextRound = () => {
    if (debateResult && currentRound < debateResult.rounds.length - 1) {
      setCurrentRound(currentRound + 1);
    }
  };

  const showPreviousRound = () => {
    if (currentRound > 0) {
      setCurrentRound(currentRound - 1);
    }
  };

  // Show start screen
  if (!debateResult) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-6 p-8">
        <div className="flex items-center gap-3">
          <Swords className="h-12 w-12 text-primary animate-pulse" />
          <h2 className="text-3xl font-bold text-glow">DEBATE ARENA</h2>
          <Swords className="h-12 w-12 text-primary animate-pulse" />
        </div>

        <Card className="p-6 max-w-2xl">
          <div className="text-center space-y-4">
            <div className="flex items-center justify-center gap-2 text-primary">
              <Sparkles className="h-5 w-5" />
              <span className="font-semibold">
                {documentIds.length} Papers Selected
              </span>
              <Sparkles className="h-5 w-5" />
            </div>

            <p className="text-muted-foreground">
              Watch research papers debate each other in an epic battle of facts and citations!
            </p>

            <div className="grid grid-cols-2 gap-4 text-sm">
              <div className="p-3 rounded terminal-border bg-matrix-bg/20">
                <div className="font-semibold text-primary">3 Rounds</div>
                <div className="text-muted-foreground text-xs">Different topics</div>
              </div>
              <div className="p-3 rounded terminal-border bg-matrix-bg/20">
                <div className="font-semibold text-primary">Auto-Teams</div>
                <div className="text-muted-foreground text-xs">Smart grouping</div>
              </div>
              <div className="p-3 rounded terminal-border bg-matrix-bg/20">
                <div className="font-semibold text-primary">Live Scoring</div>
                <div className="text-muted-foreground text-xs">Points per round</div>
              </div>
              <div className="p-3 rounded terminal-border bg-matrix-bg/20">
                <div className="font-semibold text-primary">Max Humor 🔥</div>
                <div className="text-muted-foreground text-xs">Roast mode enabled</div>
              </div>
            </div>

            <Button
              onClick={handleStartDebate}
              disabled={startDebateMutation.isPending}
              size="lg"
              className="w-full mt-4"
            >
              {startDebateMutation.isPending ? (
                <div className="flex items-center gap-2">
                  <span>Setting up the arena</span>
                  <div className="loading-dots">
                    <span></span>
                    <span></span>
                    <span></span>
                  </div>
                </div>
              ) : (
                <div className="flex items-center gap-2">
                  <Swords className="h-5 w-5" />
                  <span>START DEBATE</span>
                  <Swords className="h-5 w-5" />
                </div>
              )}
            </Button>
          </div>
        </Card>
      </div>
    );
  }

  // Show debate
  return (
    <div className="flex h-full flex-col gap-4 p-4 overflow-y-auto">
      {/* Header */}
      <DebateHeader />

      {/* Teams and Scoreboard */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <DebateTeamCard
          team={debateResult.team_a}
          color="red"
          documents={documents}
        />

        <DebateScoreboard
          teamAScore={debateResult.team_a.score}
          teamBScore={debateResult.team_b.score}
          teamAName={debateResult.team_a.name}
          teamBName={debateResult.team_b.name}
        />

        <DebateTeamCard
          team={debateResult.team_b}
          color="blue"
          documents={documents}
        />
      </div>

      {/* Rounds */}
      <div className="space-y-4">
        {debateResult.rounds.slice(0, currentRound + 1).map((round) => (
          <DebateRoundCard
            key={round.round}
            round={round}
            teamAName={debateResult.team_a.name}
            teamBName={debateResult.team_b.name}
            isLatest={round.round === currentRound + 1}
          />
        ))}
      </div>

      {/* Navigation */}
      <div className="flex items-center justify-between gap-4 sticky bottom-0 bg-background/95 backdrop-blur py-4 border-t border-matrix-border/50">
        <Button
          onClick={showPreviousRound}
          disabled={currentRound === 0}
          variant="outline"
        >
          ← Previous Round
        </Button>

        <div className="text-sm text-muted-foreground">
          Round {currentRound + 1} of {debateResult.rounds.length}
        </div>

        {currentRound < debateResult.rounds.length - 1 ? (
          <Button onClick={showNextRound}>
            Next Round →
          </Button>
        ) : (
          <Card className="p-4 terminal-border bg-primary/10">
            <div className="text-center font-bold text-primary">
              {debateResult.final_verdict}
            </div>
          </Card>
        )}
      </div>
    </div>
  );
}
