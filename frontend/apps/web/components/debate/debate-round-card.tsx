'use client';

import { Card } from '@/components/ui/card';
import { DebateRound, DebateArgument } from '@/types';
import { CheckCircle2, ThumbsUp, Zap } from 'lucide-react';

interface DebateRoundCardProps {
  round: DebateRound;
  teamAName: string;
  teamBName: string;
  isLatest?: boolean;
}

function ArgumentDisplay({
  argument,
  teamColor,
  teamName,
}: {
  argument: DebateArgument;
  teamColor: 'red' | 'blue';
  teamName: string;
}) {
  const bgColor = teamColor === 'red' ? 'bg-red-500/5' : 'bg-blue-500/5';
  const borderColor = teamColor === 'red' ? 'border-red-500/30' : 'border-blue-500/30';
  const textColor = teamColor === 'red' ? 'text-red-500' : 'text-blue-500';
  const emoji = teamColor === 'red' ? '🔴' : '🔵';

  // Detect special tones for visual flair
  const getToneIndicator = () => {
    if (argument.tone === 'confident') return '💪';
    if (argument.tone === 'defensive') return '🛡️';
    if (argument.tone === 'conceding') return '🤝';
    return '';
  };

  return (
    <div className={`p-4 rounded terminal-border ${bgColor} ${borderColor} space-y-3`}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className={`font-semibold ${textColor} flex items-center gap-2`}>
          <span>{emoji}</span>
          <span>{teamName}</span>
          <span className="text-lg">{getToneIndicator()}</span>
        </div>
        {argument.verified && (
          <div className="flex items-center gap-1 text-xs text-green-500">
            <CheckCircle2 className="h-3 w-3" />
            <span>Verified</span>
          </div>
        )}
      </div>

      {/* Argument text */}
      <div className="text-sm leading-relaxed">
        {argument.argument}
      </div>

      {/* Citations */}
      {argument.citations.length > 0 && (
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <span className="font-semibold">📊 Cites:</span>
          {argument.citations.map((citation, idx) => (
            <span key={idx} className="px-2 py-1 rounded bg-matrix-bg/50">
              {citation.page ? `p.${citation.page}` : citation.chunk_id}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

export function DebateRoundCard({
  round,
  teamAName,
  teamBName,
  isLatest,
}: DebateRoundCardProps) {
  // Determine winner styling
  const getWinnerBadge = () => {
    if (round.winner === 'team_a') return { text: `🔴 ${teamAName} wins!`, color: 'text-red-500' };
    if (round.winner === 'team_b') return { text: `🔵 ${teamBName} wins!`, color: 'text-blue-500' };
    return { text: '🤝 Tied round', color: 'text-muted-foreground' };
  };

  const winnerBadge = getWinnerBadge();

  return (
    <Card className={`p-6 space-y-4 ${isLatest ? 'ring-2 ring-primary animate-pulse-slow' : ''}`}>
      {/* Round Header */}
      <div className="flex items-center justify-between border-b border-matrix-border/50 pb-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-2xl">🎙️</span>
            <h3 className="font-bold text-lg text-glow">Round {round.round}</h3>
          </div>
          <div className="text-sm text-muted-foreground mt-1">{round.topic}</div>
        </div>
        <div className={`font-semibold ${winnerBadge.color}`}>
          {winnerBadge.text}
        </div>
      </div>

      {/* Arguments - Side by Side */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <ArgumentDisplay
          argument={round.team_a}
          teamColor="red"
          teamName={teamAName}
        />
        <ArgumentDisplay
          argument={round.team_b}
          teamColor="blue"
          teamBName={teamBName}
        />
      </div>

      {/* Moderator Comment */}
      <div className="flex items-start gap-3 p-3 rounded bg-primary/5 terminal-border border-primary/30">
        <Zap className="h-5 w-5 text-primary flex-shrink-0 mt-0.5" />
        <div className="flex-1">
          <div className="text-xs font-semibold text-primary mb-1">MODERATOR</div>
          <div className="text-sm">{round.moderator_comment}</div>
        </div>
      </div>

      {/* Current Scores */}
      <div className="flex items-center justify-center gap-8 text-sm pt-2">
        <div className="flex items-center gap-2">
          <span className="text-muted-foreground">Score:</span>
          <span className="font-bold text-red-500">{round.scores.team_a}</span>
          <span className="text-muted-foreground">-</span>
          <span className="font-bold text-blue-500">{round.scores.team_b}</span>
        </div>
      </div>
    </Card>
  );
}
