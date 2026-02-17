'use client';

import { ChatContainer } from '@/components/chat/chat-container';
import { DocumentSelector } from '@/components/chat/document-selector';
import { PDFViewer } from '@/components/pdf/pdf-viewer';
import { Card } from '@/components/ui/card';
import { useAppStore } from '@/lib/store';

export default function HomePage() {
  const pdfViewerOpen = useAppStore((state) => state.pdfViewerOpen);
  const pdfViewerDocumentId = useAppStore((state) => state.pdfViewerDocumentId);
  const pdfViewerPage = useAppStore((state) => state.pdfViewerPage);
  const pdfViewerHighlightText = useAppStore((state) => state.pdfViewerHighlightText);
  const closePdfViewer = useAppStore((state) => state.closePdfViewer);

  if (pdfViewerOpen && pdfViewerDocumentId) {
    // Full-width layout when PDF viewer is open
    return (
      <div className="grid h-[calc(100vh-8rem)] gap-4 grid-cols-2">
        {/* Chat - Left Half */}
        <Card className="p-6 flex flex-col min-h-0">
          <div className="flex items-center gap-3 mb-4 border-b border-matrix-border/50 pb-4 flex-shrink-0">
            <div className="h-2 w-2 rounded-full bg-primary animate-pulse-glow" />
            <h1 className="text-lg font-bold text-glow">Research Assistant</h1>
          </div>
          <div className="flex-1 min-h-0">
            <ChatContainer />
          </div>
        </Card>

        {/* PDF Viewer - Right Half */}
        <Card className="p-0 overflow-hidden">
          <PDFViewer
            documentId={pdfViewerDocumentId}
            initialPage={pdfViewerPage}
            highlightText={pdfViewerHighlightText || undefined}
            onClose={closePdfViewer}
          />
        </Card>
      </div>
    );
  }

  // Default layout without PDF viewer
  return (
    <div className="grid h-[calc(100vh-8rem)] gap-6 lg:grid-cols-3">
      {/* Main chat area */}
      <Card className="lg:col-span-2 p-6 flex flex-col min-h-0">
        <div className="flex items-center gap-3 mb-4 border-b border-matrix-border/50 pb-4 flex-shrink-0">
          <div className="h-2 w-2 rounded-full bg-primary animate-pulse-glow" />
          <h1 className="text-xl font-bold text-glow">Research Assistant</h1>
        </div>
        <div className="flex-1 min-h-0">
          <ChatContainer />
        </div>
      </Card>

      {/* Sidebar info */}
      <div className="space-y-6">
        {/* Document Selector for Multi-Doc Queries */}
        <Card className="p-6">
          <DocumentSelector />
        </Card>

        {/* Quick stats */}
        <Card className="p-6">
          <h2 className="text-sm font-semibold text-muted-foreground mb-4">
            QUICK STATS
          </h2>
          <div className="space-y-4">
            <div>
              <div className="text-2xl font-bold text-primary">0</div>
              <div className="text-sm text-muted-foreground">Documents</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-secondary">0</div>
              <div className="text-sm text-muted-foreground">Sessions</div>
            </div>
          </div>
        </Card>

        {/* Recent activity */}
        <Card className="p-6">
          <h2 className="text-sm font-semibold text-muted-foreground mb-4">
            RECENT ACTIVITY
          </h2>
          <div className="text-sm text-muted-foreground">
            No recent activity
          </div>
        </Card>
      </div>
    </div>
  );
}
