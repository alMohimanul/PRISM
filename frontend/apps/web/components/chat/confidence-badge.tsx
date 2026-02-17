'use client';

import { Shield, AlertTriangle, AlertCircle } from 'lucide-react';

interface ConfidenceBadgeProps {
  confidence: number;
  unsupported_spans?: { text: string; reason: string }[];
}

export function ConfidenceBadge({ confidence, unsupported_spans = [] }: ConfidenceBadgeProps) {
  // Determine badge level based on confidence
  const getLevel = () => {
    if (confidence >= 0.75) return 'high';
    if (confidence >= 0.4) return 'medium';
    return 'low';
  };

  const level = getLevel();

  const levelConfig = {
    high: {
      icon: Shield,
      label: 'Well supported',
      color: 'text-green-500',
      bgColor: 'bg-green-500/10',
      borderColor: 'border-green-500/30',
    },
    medium: {
      icon: AlertTriangle,
      label: 'Partial',
      color: 'text-yellow-500',
      bgColor: 'bg-yellow-500/10',
      borderColor: 'border-yellow-500/30',
    },
    low: {
      icon: AlertCircle,
      label: 'Weak evidence',
      color: 'text-red-500',
      bgColor: 'bg-red-500/10',
      borderColor: 'border-red-500/30',
    },
  };

  const config = levelConfig[level];
  const Icon = config.icon;

  return (
    <div className="space-y-2">
      {/* Confidence Badge */}
      <div
        className={`inline-flex items-center gap-2 rounded px-3 py-1.5 text-xs font-medium border ${config.bgColor} ${config.borderColor} ${config.color}`}
        title={`Confidence: ${(confidence * 100).toFixed(0)}%`}
      >
        <Icon className="h-3.5 w-3.5" />
        <span>{config.label}</span>
        <span className="opacity-70">({(confidence * 100).toFixed(0)}%)</span>
      </div>

      {/* Unsupported Spans Warning */}
      {unsupported_spans.length > 0 && (
        <div className="mt-2 space-y-1">
          <p className="text-xs text-yellow-500/80 flex items-center gap-1">
            <AlertTriangle className="h-3 w-3" />
            Potentially unsupported claims:
          </p>
          <div className="space-y-1">
            {unsupported_spans.map((span, idx) => (
              <div
                key={idx}
                className="text-xs rounded border border-yellow-500/20 bg-yellow-500/5 px-2 py-1"
              >
                <p className="text-yellow-200/90">&quot;{span.text}&quot;</p>
                <p className="text-yellow-500/60 text-[10px] mt-0.5">{span.reason}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
