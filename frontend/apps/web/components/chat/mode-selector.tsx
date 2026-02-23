'use client';

import { Card } from '@/components/ui/card';
import { MessageCircle, GitCompare } from 'lucide-react';

export type ChatMode = 'ask' | 'compare';

interface ModeSelectorProps {
  selectedMode: ChatMode;
  onSelectMode: (mode: ChatMode) => void;
  documentCount: number;
}

export function ModeSelector({ selectedMode, onSelectMode, documentCount }: ModeSelectorProps) {
  const modes = [
    {
      id: 'ask' as ChatMode,
      icon: MessageCircle,
      label: 'Ask',
      description: 'Chat with your papers',
      color: 'text-green-500',
      bgColor: 'bg-green-500/10',
      borderColor: 'border-green-500/50',
      minDocs: 0,
    },
    {
      id: 'compare' as ChatMode,
      icon: GitCompare,
      label: 'Paper Comparison',
      description: 'Side-by-side analysis for 2-4 papers',
      color: 'text-purple-500',
      bgColor: 'bg-purple-500/10',
      borderColor: 'border-purple-500/50',
      minDocs: 2,
      maxDocs: 4,
    },
  ];

  return (
    <div className="border-b border-matrix-border/50 pb-4 mb-4">
      <div className="flex items-center justify-center gap-3">
        {modes.map((mode) => {
          const Icon = mode.icon;
          const isSelected = selectedMode === mode.id;
          const isTooFewDocs = documentCount < mode.minDocs;
          const isTooManyDocs = mode.maxDocs && documentCount > mode.maxDocs;
          const isDisabled = isTooFewDocs || isTooManyDocs;

          return (
            <Card
              key={mode.id}
              className={`
                relative cursor-pointer transition-all duration-200
                ${isSelected
                  ? `${mode.bgColor} ${mode.borderColor} border-2 scale-105`
                  : 'bg-matrix-bg/20 border-matrix-border hover:scale-102'
                }
                ${isDisabled ? 'opacity-40 cursor-not-allowed' : ''}
              `}
              onClick={() => !isDisabled && onSelectMode(mode.id)}
            >
              <div className="p-4 text-center min-w-[140px]">
                <div className="flex flex-col items-center gap-2">
                  <Icon className={`h-8 w-8 ${isSelected ? mode.color : 'text-muted-foreground'}`} />
                  <div>
                    <div className={`font-bold ${isSelected ? mode.color : 'text-foreground'}`}>
                      {mode.label}
                    </div>
                    <div className="text-xs text-muted-foreground mt-1">
                      {mode.description}
                    </div>
                    {isTooFewDocs && (
                      <div className="text-xs text-red-400 mt-1">
                        Need {mode.minDocs}+ docs
                      </div>
                    )}
                    {isTooManyDocs && (
                      <div className="text-xs text-red-400 mt-1">
                        Max {mode.maxDocs} docs
                      </div>
                    )}
                  </div>
                </div>
                {isSelected && (
                  <div className="absolute -top-1 -right-1">
                    <div className={`w-3 h-3 rounded-full ${mode.color.replace('text-', 'bg-')} animate-pulse`} />
                  </div>
                )}
              </div>
            </Card>
          );
        })}
      </div>

      {/* Mode description */}
      <div className="text-center mt-4 text-sm text-muted-foreground">
        {selectedMode === 'ask' && (
          <span>💬 Ask questions and get answers with citations</span>
        )}
        {selectedMode === 'compare' && (
          <span>📊 Compare papers across methodology, datasets, results, and limitations</span>
        )}
      </div>
    </div>
  );
}
