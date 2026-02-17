'use client';

import { useQuery } from '@tanstack/react-query';
import { Grid, List, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { UploadZone } from '@/components/documents/upload-zone';
import { DocumentCard } from '@/components/documents/document-card';
import { documentsApi } from '@/lib/api';
import { useAppStore } from '@/lib/store';

export default function DocumentsPage() {
  const { documentViewMode, setDocumentViewMode } = useAppStore();

  const { data: documents, isLoading } = useQuery({
    queryKey: ['documents'],
    queryFn: documentsApi.list,
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-glow">Documents</h1>
          <p className="text-muted-foreground mt-1">
            Upload and manage your research papers
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant={documentViewMode === 'grid' ? 'default' : 'outline'}
            size="icon"
            onClick={() => setDocumentViewMode('grid')}
          >
            <Grid className="h-4 w-4" />
          </Button>
          <Button
            variant={documentViewMode === 'list' ? 'default' : 'outline'}
            size="icon"
            onClick={() => setDocumentViewMode('list')}
          >
            <List className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Upload zone */}
      <UploadZone />

      {/* Documents grid/list */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      ) : documents && documents.length > 0 ? (
        <div
          className={
            documentViewMode === 'grid'
              ? 'grid gap-6 sm:grid-cols-2 lg:grid-cols-3'
              : 'space-y-4'
          }
        >
          {documents.map((doc) => (
            <DocumentCard
              key={doc.document_id}
              document={doc}
              viewMode={documentViewMode}
            />
          ))}
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center py-12 text-center">
          <div className="rounded-full glass p-4 mb-4">
            <List className="h-8 w-8 text-muted-foreground" />
          </div>
          <h3 className="text-lg font-semibold">No documents yet</h3>
          <p className="text-sm text-muted-foreground mt-2">
            Upload your first research paper to get started
          </p>
        </div>
      )}
    </div>
  );
}
