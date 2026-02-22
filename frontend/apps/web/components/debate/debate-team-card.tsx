'use client';

import { Card } from '@/components/ui/card';
import { DebateTeam } from '@/types';
import { FileText } from 'lucide-react';

interface DebateTeamCardProps {
  team: DebateTeam;
  color: 'red' | 'blue';
  documents: Map<string, any>;
}

export function DebateTeamCard({ team, color, documents }: DebateTeamCardProps) {
  const bgColor = color === 'red' ? 'bg-red-500/10' : 'bg-blue-500/10';
  const borderColor = color === 'red' ? 'border-red-500/50' : 'border-blue-500/50';
  const textColor = color === 'red' ? 'text-red-500' : 'text-blue-500';

  return (
    <Card className={`p-4 terminal-border ${bgColor} ${borderColor}`}>
      <div className="space-y-3">
        {/* Team name */}
        <div className="flex items-center justify-between">
          <h3 className={`font-bold text-lg ${textColor}`}>
            {color === 'red' ? '🔴' : '🔵'} {team.name}
          </h3>
          <div className="text-2xl font-bold">{team.score}</div>
        </div>

        {/* Documents */}
        <div className="space-y-2">
          {team.documents.map((docId) => {
            const doc = documents.get(docId);
            return (
              <div
                key={docId}
                className="flex items-center gap-2 text-xs p-2 rounded bg-matrix-bg/30"
              >
                <FileText className="h-3 w-3 flex-shrink-0" />
                <span className="truncate">
                  {doc?.filename || doc?.title || `Paper ${docId.slice(0, 8)}`}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </Card>
  );
}
