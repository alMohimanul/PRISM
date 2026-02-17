"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Document, Page, pdfjs } from "react-pdf";
import "react-pdf/dist/esm/Page/AnnotationLayer.css";
import "react-pdf/dist/esm/Page/TextLayer.css";
import { ChevronLeft, ChevronRight, ZoomIn, ZoomOut, X } from "lucide-react";

// Configure PDF.js worker
pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.js`;

interface PDFViewerProps {
  documentId: string;
  initialPage?: number;
  highlightText?: string;
  onClose?: () => void;
}

export function PDFViewer({
  documentId,
  initialPage = 1,
  highlightText,
  onClose,
}: PDFViewerProps) {
  const [numPages, setNumPages] = useState<number>(0);
  const [pageNumber, setPageNumber] = useState<number>(initialPage);
  const [scale, setScale] = useState<number>(1.0);
  const [pdfUrl, setPdfUrl] = useState<string>("");
  const pageRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Set PDF URL from API
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    setPdfUrl(`${apiUrl}/api/documents/${documentId}/pdf`);
  }, [documentId]);

  useEffect(() => {
    // Jump to initial page when it changes
    if (initialPage !== pageNumber) {
      setPageNumber(initialPage);
    }
  }, [initialPage, pageNumber]);

  useEffect(() => {
    // Highlight text when it changes or page changes
    if (highlightText && pageRef.current) {
      // Delay to ensure text layer is rendered
      const timer = setTimeout(() => {
        highlightTextInPage(highlightText);
      }, 500);
      return () => clearTimeout(timer);
    }
  }, [highlightText, pageNumber, highlightTextInPage]);

  function onDocumentLoadSuccess({ numPages }: { numPages: number }) {
    setNumPages(numPages);
  }

  const highlightTextInPage = useCallback((text: string) => {
    if (!pageRef.current) {
      console.log('❌ No pageRef');
      return;
    }

    const textLayer = pageRef.current.querySelector(".react-pdf__Page__textContent");
    if (!textLayer) {
      console.log('❌ No text layer found, retrying...');
      // Retry after a delay
      setTimeout(() => highlightTextInPage(text), 300);
      return;
    }

    console.log('🔍 Attempting to highlight:', text.substring(0, 100) + '...');

    // Remove existing highlights
    const existingHighlights = textLayer.querySelectorAll(".pdf-highlight");
    existingHighlights.forEach((el) => el.classList.remove("pdf-highlight"));

    // Get all text spans
    const spans = Array.from(textLayer.querySelectorAll("span"));
    const searchWords = text
      .toLowerCase()
      .replace(/[^\w\s]/g, ' ')
      .split(/\s+/)
      .filter(word => word.length > 3); // Only significant words

    console.log('🔎 Searching for words:', searchWords.slice(0, 5));

    let highlighted = false;
    let consecutiveMatches = 0;
    const minConsecutiveMatches = 3;

    // Look for consecutive spans that match our search words
    for (let i = 0; i < spans.length; i++) {
      const span = spans[i];
      const spanText = (span.textContent || "").toLowerCase().replace(/[^\w\s]/g, ' ');

      // Check if this span contains any of our search words
      const hasMatch = searchWords.some(word => spanText.includes(word));

      if (hasMatch) {
        consecutiveMatches++;
        span.classList.add("pdf-highlight");
        highlighted = true;

        // If we found enough consecutive matches, we're done
        if (consecutiveMatches >= minConsecutiveMatches) {
          console.log('✅ Found matching text, highlighted', consecutiveMatches, 'spans');
          break;
        }
      } else if (consecutiveMatches > 0) {
        // Reset if we break the sequence
        consecutiveMatches = 0;
      }
    }

    if (highlighted) {
      // Scroll to first highlight
      const firstHighlight = textLayer.querySelector(".pdf-highlight");
      if (firstHighlight) {
        setTimeout(() => {
          firstHighlight.scrollIntoView({ behavior: "smooth", block: "center" });
          console.log('📜 Scrolled to highlight');
        }, 100);
      }
    } else {
      console.log('⚠️ Text not found on this page');
      console.log('💡 Try navigating to a different page');
    }
  }, []);

  function changePage(offset: number) {
    setPageNumber((prevPageNumber) => {
      const newPage = prevPageNumber + offset;
      return Math.min(Math.max(1, newPage), numPages);
    });
  }

  function zoomIn() {
    setScale((prevScale) => Math.min(prevScale + 0.25, 2.0));
  }

  function zoomOut() {
    setScale((prevScale) => Math.max(prevScale - 0.25, 0.6));
  }

  function resetZoom() {
    setScale(1.0);
  }

  if (!pdfUrl) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-muted-foreground">Loading PDF...</div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-matrix-dark">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-primary/20 bg-matrix-darker/50">
        <div className="flex items-center gap-4">
          {/* Page Navigation */}
          <div className="flex items-center gap-2">
            <button
              onClick={() => changePage(-1)}
              disabled={pageNumber <= 1}
              className="p-1.5 rounded-md hover:bg-primary/10 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            >
              <ChevronLeft className="w-5 h-5 text-primary" />
            </button>
            <span className="text-sm font-mono text-foreground min-w-[100px] text-center">
              Page {pageNumber} of {numPages || "?"}
            </span>
            <button
              onClick={() => changePage(1)}
              disabled={pageNumber >= numPages}
              className="p-1.5 rounded-md hover:bg-primary/10 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            >
              <ChevronRight className="w-5 h-5 text-primary" />
            </button>
          </div>

          {/* Zoom Controls */}
          <div className="flex items-center gap-2 ml-4 border-l border-primary/20 pl-4">
            <button
              onClick={zoomOut}
              className="p-1.5 rounded-md hover:bg-primary/10 transition-colors"
              title="Zoom out"
            >
              <ZoomOut className="w-5 h-5 text-primary" />
            </button>
            <button
              onClick={resetZoom}
              className="text-sm font-mono text-primary hover:text-primary/80 min-w-[60px] text-center cursor-pointer transition-colors"
              title="Reset zoom (100%)"
            >
              {Math.round(scale * 100)}%
            </button>
            <button
              onClick={zoomIn}
              className="p-1.5 rounded-md hover:bg-primary/10 transition-colors"
              title="Zoom in"
            >
              <ZoomIn className="w-5 h-5 text-primary" />
            </button>
          </div>
        </div>

        {/* Close Button */}
        {onClose && (
          <button
            onClick={onClose}
            className="p-1.5 rounded-md hover:bg-primary/10 transition-colors"
          >
            <X className="w-5 h-5 text-primary" />
          </button>
        )}
      </div>

      {/* PDF Content */}
      <div className="flex-1 overflow-auto bg-neutral-900/50 p-4">
        <div className="flex justify-center min-h-full">
          <div ref={pageRef} className="shadow-2xl bg-white">
            <Document
              file={pdfUrl}
              onLoadSuccess={onDocumentLoadSuccess}
              loading={
                <div className="flex items-center justify-center p-20 bg-matrix-dark">
                  <div className="flex flex-col items-center gap-3">
                    <div className="animate-spin h-8 w-8 border-4 border-primary border-t-transparent rounded-full"></div>
                    <div className="text-muted-foreground">Loading document...</div>
                  </div>
                </div>
              }
              error={
                <div className="flex items-center justify-center p-20 bg-matrix-dark">
                  <div className="text-red-500">Error loading PDF</div>
                </div>
              }
            >
              <Page
                pageNumber={pageNumber}
                scale={scale}
                renderTextLayer={true}
                renderAnnotationLayer={true}
                className="max-w-full"
                loading={
                  <div className="flex items-center justify-center p-20 bg-white">
                    <div className="text-gray-600">Rendering page...</div>
                  </div>
                }
              />
            </Document>
          </div>
        </div>
      </div>

      {/* Custom CSS for highlighting */}
      <style jsx global>{`
        .pdf-highlight {
          background-color: rgba(255, 255, 0, 0.5) !important;
          box-shadow: 0 0 0 2px rgba(255, 255, 0, 0.3);
          border-radius: 2px;
          animation: pulse-highlight 1.5s ease-in-out 3;
          padding: 2px 0;
        }

        @keyframes pulse-highlight {
          0%, 100% {
            background-color: rgba(255, 255, 0, 0.5);
            box-shadow: 0 0 0 2px rgba(255, 255, 0, 0.3);
          }
          50% {
            background-color: rgba(255, 255, 0, 0.8);
            box-shadow: 0 0 0 3px rgba(255, 255, 0, 0.5);
          }
        }

        /* Improve PDF text layer readability */
        .react-pdf__Page__textContent {
          opacity: 1 !important;
        }

        .react-pdf__Page__textContent span {
          color: transparent !important;
        }
      `}</style>
    </div>
  );
}
