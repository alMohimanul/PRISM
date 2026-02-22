'use client';

import { Card } from '@/components/ui/card';
import { Trophy } from 'lucide-react';

interface DebateScoreboardProps {
  teamAScore: number;
  teamBScore: number;
  teamAName: string;
  teamBName: string;
}

export function DebateScoreboard({
  teamAScore,
  teamBScore,
  teamAName,
  teamBName,
}: DebateScoreboardProps) {
  const totalScore = teamAScore + teamBScore;
  const teamAPercent = totalScore > 0 ? (teamAScore / totalScore) * 100 : 50;
  const teamBPercent = totalScore > 0 ? (teamBScore / totalScore) * 100 : 50;

  return (
    <Card className="p-4 terminal-border bg-primary/5 flex flex-col justify-center">
      <div className="space-y-4">
        {/* Title */}
        <div className="text-center">
          <div className="flex items-center justify-center gap-2 mb-2">
            <Trophy className="h-5 w-5 text-primary" />
            <h3 className="font-bold text-glow">SCOREBOARD</h3>
          </div>
        </div>

        {/* Score Display */}
        <div className="flex items-center justify-center gap-4 text-3xl font-bold">
          <div className="text-red-500">{teamAScore}</div>
          <div className="text-muted-foreground">-</div>
          <div className="text-blue-500">{teamBScore}</div>
        </div>

        {/* Progress bar */}
        <div className="relative h-6 rounded-full overflow-hidden terminal-border bg-matrix-bg">
          <div
            className="absolute left-0 top-0 h-full bg-red-500/50 transition-all duration-500"
            style={{ width: `${teamAPercent}%` }}
          />
          <div
            className="absolute right-0 top-0 h-full bg-blue-500/50 transition-all duration-500"
            style={{ width: `${teamBPercent}%` }}
          />
          <div className="absolute inset-0 flex items-center justify-center text-xs font-semibold">
            {teamAScore > teamBScore ? '🔴 Leading' : teamBScore > teamAScore ? '🔵 Leading' : '🤝 Tied'}
          </div>
        </div>

        {/* Stars */}
        <div className="flex items-center justify-between text-xs">
          <div className="flex gap-0.5">
            {[...Array(5)].map((_, i) => (
              <span key={i} className={i < teamAScore ? 'text-red-500' : 'text-muted-foreground/30'}>
                ⭐
              </span>
            ))}
          </div>
          <div className="flex gap-0.5">
            {[...Array(5)].map((_, i) => (
              <span key={i} className={i < teamBScore ? 'text-blue-500' : 'text-muted-foreground/30'}>
                ⭐
              </span>
            ))}
          </div>
        </div>
      </div>
    </Card>
  );
}
