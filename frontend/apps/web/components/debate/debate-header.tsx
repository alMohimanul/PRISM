'use client';

import { Swords } from 'lucide-react';

export function DebateHeader() {
  return (
    <div className="text-center py-4 border-b border-matrix-border/50">
      <div className="flex items-center justify-center gap-3 mb-2">
        <div className="text-red-500">🥊</div>
        <h1 className="text-2xl font-bold text-glow flex items-center gap-2">
          <span className="text-red-500">DEBATE</span>
          <Swords className="h-6 w-6 text-primary" />
          <span className="text-blue-500">ARENA</span>
        </h1>
        <div className="text-blue-500">🥊</div>
      </div>
      <p className="text-sm text-muted-foreground">
        Watch research papers battle with facts and citations
      </p>
    </div>
  );
}
