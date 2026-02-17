'use client';

import { useQuery } from '@tanstack/react-query';
import { documentsApi } from '@/lib/api';
import { useAppStore } from '@/lib/store';
import { FileText, X, CheckCircle2 } from 'lucide-react';
import { cn } from '@/lib/utils';

export function DocumentSelector() {
  const { selectedDocuments, toggleSelectedDocument, clearSelectedDocuments } = useAppStore();

  const { data: documents = [], isLoading } = useQuery({
    queryKey: ['documents'],
    queryFn: documentsApi.list,
  });

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
        Loading documents...
      </div>
    );
  }

  if (documents.length === 0) {
    return (
      <div className="text-sm text-muted-foreground">
        No documents uploaded yet. Upload papers to enable multi-document queries.
      </div>
    );
  }

  const selectedCount = selectedDocuments.size;

  return (
    <div className="flex flex-col gap-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h3 className="text-sm font-medium">
            Query Documents
            {selectedCount > 0 && (
              <span className="ml-2 text-primary">({selectedCount} selected)</span>
            )}
          </h3>
        </div>
        {selectedCount > 0 && (
          <button
            onClick={clearSelectedDocuments}
            className="text-xs text-muted-foreground hover:text-foreground transition-colors flex items-center gap-1"
          >
            <X className="h-3 w-3" />
            Clear
          </button>
        )}
      </div>

      {/* Info */}
      <p className="text-xs text-muted-foreground">
        {selectedCount === 0
          ? 'Query all documents, or select specific papers for focused analysis'
          : selectedCount === 1
          ? 'Querying one document'
          : `Compare and synthesize across ${selectedCount} papers`}
      </p>

      {/* Document List */}
      <div className="grid grid-cols-1 gap-2 max-h-40 overflow-y-auto scrollbar-thin scrollbar-thumb-primary/30 scrollbar-track-transparent">
        {documents.map((doc) => {
          const isSelected = selectedDocuments.has(doc.document_id);
          return (
            <button
              key={doc.document_id}
              onClick={() => toggleSelectedDocument(doc.document_id)}
              className={cn(
                'flex items-center gap-3 p-2 rounded-md border text-left transition-all',
                isSelected
                  ? 'border-primary bg-primary/10 hover:bg-primary/15'
                  : 'border-matrix-border hover:border-primary/50 hover:bg-primary/5'
              )}
            >
              {/* Icon */}
              <div
                className={cn(
                  'flex h-8 w-8 shrink-0 items-center justify-center rounded',
                  isSelected ? 'bg-primary/20' : 'bg-primary/10'
                )}
              >
                {isSelected ? (
                  <CheckCircle2 className="h-4 w-4 text-primary" />
                ) : (
                  <FileText className="h-4 w-4 text-primary/70" />
                )}
              </div>

              {/* Document Info */}
              <div className="flex-1 min-w-0">
                <h4 className={cn(
                  'text-sm font-medium truncate',
                  isSelected && 'text-primary'
                )}>
                  {doc.title || doc.filename}
                </h4>
                <p className="text-xs text-muted-foreground">
                  {doc.page_count} pages
                </p>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
