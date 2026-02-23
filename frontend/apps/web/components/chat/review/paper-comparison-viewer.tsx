'use client';

import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { GitCompare, Loader2, RefreshCw } from 'lucide-react';
import { paperComparisonApi } from '@/lib/api';
import type { PaperComparisonResponse, PaperComparisonFocus } from '@/types';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';

interface PaperComparisonViewerProps {
  documentIds: string[];
}

const focusOptions: Array<{ value: PaperComparisonFocus; label: string }> = [
  { value: 'all', label: 'All Dimensions' },
  { value: 'methodology', label: 'Methodology' },
  { value: 'datasets', label: 'Datasets' },
  { value: 'results', label: 'Results' },
];

export function PaperComparisonViewer({ documentIds }: PaperComparisonViewerProps) {
  const [focus, setFocus] = useState<PaperComparisonFocus>('all');
  const [comparison, setComparison] = useState<PaperComparisonResponse | null>(null);

  const compareMutation = useMutation({
    mutationFn: async () => {
      return paperComparisonApi.compare(documentIds, focus);
    },
    onSuccess: (data) => {
      setComparison(data);
    },
  });

  const handleRunComparison = () => {
    compareMutation.reset();
    compareMutation.mutate();
  };

  const handleNewComparison = () => {
    compareMutation.reset();
    setComparison(null);
  };

  const isDocumentCountInvalid = documentIds.length < 2 || documentIds.length > 4;

  // Empty and setup state
  if (!comparison) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-6 p-8">
        <GitCompare className="h-12 w-12 text-purple-500 animate-pulse" />
        <h2 className="text-2xl font-bold">Paper Comparison</h2>

        <Card className="p-6 max-w-3xl w-full space-y-4">
          <p className="text-sm text-muted-foreground text-center">
            Compare {documentIds.length} selected paper{documentIds.length === 1 ? '' : 's'} across key dimensions.
          </p>

          <div className="flex flex-wrap gap-2 justify-center">
            {focusOptions.map((option) => (
              <Button
                key={option.value}
                type="button"
                variant={focus === option.value ? 'default' : 'outline'}
                size="sm"
                onClick={() => setFocus(option.value)}
              >
                {option.label}
              </Button>
            ))}
          </div>

          {isDocumentCountInvalid && (
            <div className="text-sm text-red-400 text-center">
              Select between 2 and 4 documents to run a comparison.
            </div>
          )}

          {compareMutation.isError && (
            <div className="text-sm text-red-400 text-center">
              {compareMutation.error instanceof Error
                ? compareMutation.error.message
                : 'Failed to compare papers. Please try again.'}
            </div>
          )}

          <Button
            onClick={handleRunComparison}
            disabled={compareMutation.isPending || isDocumentCountInvalid}
            size="lg"
            className="w-full"
          >
            {compareMutation.isPending ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Comparing...
              </>
            ) : (
              'Run Comparison'
            )}
          </Button>
        </Card>
      </div>
    );
  }

  // Success state
  return (
    <div className="flex h-full flex-col gap-4 p-6 overflow-y-auto">
      <div className="flex items-center justify-between border-b border-matrix-border/50 pb-4">
        <h2 className="text-xl font-bold">Paper Comparison Results</h2>
        <Button onClick={handleNewComparison} variant="ghost" size="sm">
          <RefreshCw className="h-4 w-4 mr-2" />
          New Comparison
        </Button>
      </div>

      <Card className="p-6 space-y-4">
        <h3 className="font-semibold text-lg">Comparison Table</h3>
        <div className="prose prose-invert prose-sm max-w-none overflow-x-auto">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {comparison.markdown_table}
          </ReactMarkdown>
        </div>
      </Card>

      <Card className="p-6 space-y-4">
        <h3 className="font-semibold text-lg">Insights</h3>
        <div>
          <h4 className="font-medium mb-2">Best Performers</h4>
          <div className="space-y-1 text-sm text-muted-foreground">
            {Object.entries(comparison.insights.best_performers).map(([dimension, paper]) => (
              <p key={dimension}>
                <span className="text-foreground">{dimension}:</span> {paper}
              </p>
            ))}
          </div>
        </div>

        <div>
          <h4 className="font-medium mb-2">Common Patterns</h4>
          <ul className="list-disc list-inside space-y-1 text-sm text-muted-foreground">
            {comparison.insights.common_patterns.map((pattern, idx) => (
              <li key={`${pattern}-${idx}`}>{pattern}</li>
            ))}
          </ul>
        </div>

        <div>
          <h4 className="font-medium mb-2">Key Differences</h4>
          <ul className="list-disc list-inside space-y-1 text-sm text-muted-foreground">
            {comparison.insights.key_differences.map((difference, idx) => (
              <li key={`${difference}-${idx}`}>{difference}</li>
            ))}
          </ul>
        </div>
      </Card>
    </div>
  );
}
