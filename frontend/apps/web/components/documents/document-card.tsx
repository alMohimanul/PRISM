'use client';

import { FileText, Trash2, Eye } from 'lucide-react';
import { Card, CardContent, CardFooter, CardHeader } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { formatDate, formatFileSize } from '@/lib/utils';
import type { Document } from '@/types';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { documentsApi } from '@/lib/api';
import { useAppStore } from '@/lib/store';

interface DocumentCardProps {
  document: Document;
  viewMode?: 'grid' | 'list';
}

export function DocumentCard({ document, viewMode = 'grid' }: DocumentCardProps) {
  const queryClient = useQueryClient();
  const { setSelectedDocument } = useAppStore();

  const deleteMutation = useMutation({
    mutationFn: () => documentsApi.delete(document.document_id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
    },
  });

  const handleView = () => {
    setSelectedDocument(document);
  };

  const handleDelete = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (confirm('Are you sure you want to delete this document?')) {
      deleteMutation.mutate();
    }
  };

  if (viewMode === 'list') {
    return (
      <Card className="hover-glow cursor-pointer transition-all" onClick={handleView}>
        <CardContent className="flex items-center gap-4 p-4">
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded terminal-border bg-primary/10">
            <FileText className="h-6 w-6 text-primary" />
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="font-semibold truncate">{document.title || document.filename}</h3>
            <p className="text-sm text-muted-foreground">
              {document.page_count} pages · {formatFileSize(document.size_bytes)}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="icon" onClick={handleView}>
              <Eye className="h-4 w-4" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              onClick={handleDelete}
              disabled={deleteMutation.isPending}
            >
              <Trash2 className="h-4 w-4 text-destructive" />
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="hover-glow cursor-pointer transition-all" onClick={handleView}>
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-2">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded terminal-border bg-primary/10">
            <FileText className="h-5 w-5 text-primary" />
          </div>
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8"
            onClick={handleDelete}
            disabled={deleteMutation.isPending}
          >
            <Trash2 className="h-4 w-4 text-destructive" />
          </Button>
        </div>
      </CardHeader>
      <CardContent className="pb-3">
        <h3 className="font-semibold line-clamp-2 mb-2">
          {document.title || document.filename}
        </h3>
        {document.abstract && (
          <p className="text-xs text-muted-foreground line-clamp-3">
            {document.abstract}
          </p>
        )}
      </CardContent>
      <CardFooter className="flex flex-col items-start gap-2 text-xs text-muted-foreground pt-3 border-t border-matrix-border/50">
        <div className="flex items-center justify-between w-full">
          <span>{document.page_count} pages</span>
          <span>{formatFileSize(document.size_bytes)}</span>
        </div>
        <div className="text-xs text-muted-foreground">
          {formatDate(document.upload_date)}
        </div>
      </CardFooter>
    </Card>
  );
}
