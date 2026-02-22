'use client';

import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { literatureReviewApi } from '@/lib/api';
import { LiteratureReviewResponse } from '@/types';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { BookOpen, Download, Sparkles } from 'lucide-react';

interface LiteratureReviewViewerProps {
  documentIds: string[];
}

export function LiteratureReviewViewer({ documentIds }: LiteratureReviewViewerProps) {
  const [review, setReview] = useState<LiteratureReviewResponse | null>(null);
  const [topic, setTopic] = useState('');

  const generateMutation = useMutation({
    mutationFn: async () => {
      return await literatureReviewApi.generate(
        documentIds,
        topic || 'Research Topic'
      );
    },
    onSuccess: (data) => {
      setReview(data);
    },
  });

  const handleDownload = () => {
    if (!review) return;
    const blob = new Blob([review.full_review], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `literature-review.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (!review) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-6 p-8">
        <BookOpen className="h-12 w-12 text-blue-500 animate-pulse" />
        <h2 className="text-2xl font-bold">Literature Review Generator</h2>

        <Card className="p-6 max-w-xl w-full space-y-4">
          <p className="text-sm text-muted-foreground text-center">
            Generate a comprehensive literature review from {documentIds.length} selected papers
          </p>

          <div className="space-y-2">
            <label className="text-sm font-semibold">Research Topic</label>
            <Input
              placeholder="e.g., Deep Learning for Image Classification"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
            />
          </div>

          <Button
            onClick={() => generateMutation.mutate()}
            disabled={generateMutation.isPending}
            size="lg"
            className="w-full"
          >
            {generateMutation.isPending ? 'Generating...' : 'Generate Review'}
          </Button>
        </Card>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col gap-4 p-6 overflow-y-auto">
      <div className="flex items-center justify-between border-b pb-4">
        <h2 className="text-xl font-bold">Literature Review</h2>
        <div className="flex gap-2">
          <Button onClick={handleDownload} variant="outline" size="sm">
            <Download className="h-4 w-4 mr-2" />
            Download
          </Button>
          <Button onClick={() => setReview(null)} variant="ghost" size="sm">
            New Review
          </Button>
        </div>
      </div>

      <Card className="p-6">
        <pre className="whitespace-pre-wrap font-mono text-sm">
          {review.full_review}
        </pre>
      </Card>
    </div>
  );
}
