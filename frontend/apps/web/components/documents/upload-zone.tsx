'use client';

import { useCallback, useState } from 'react';
import { Upload, Loader2, CheckCircle, XCircle } from 'lucide-react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { documentsApi } from '@/lib/api';
import { cn } from '@/lib/utils';

export function UploadZone() {
  const [isDragging, setIsDragging] = useState(false);
  const [uploadStatus, setUploadStatus] = useState<'idle' | 'uploading' | 'success' | 'error'>('idle');
  const queryClient = useQueryClient();

  const uploadMutation = useMutation({
    mutationFn: (file: File) => documentsApi.upload(file),
    onSuccess: () => {
      setUploadStatus('success');
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      setTimeout(() => setUploadStatus('idle'), 3000);
    },
    onError: () => {
      setUploadStatus('error');
      setTimeout(() => setUploadStatus('idle'), 3000);
    },
  });

  const handleDrop = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);

    const files = Array.from(e.dataTransfer.files);
    const pdfFile = files.find(file => file.type === 'application/pdf');

    if (pdfFile) {
      setUploadStatus('uploading');
      uploadMutation.mutate(pdfFile);
    }
  }, [uploadMutation]);

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file && file.type === 'application/pdf') {
      setUploadStatus('uploading');
      uploadMutation.mutate(file);
    }
  };

  return (
    <div
      className={cn(
        'relative rounded-lg terminal-border p-8 transition-all',
        isDragging && 'border-primary bg-primary/5 scale-[1.02]',
        uploadStatus === 'success' && 'border-primary bg-primary/5',
        uploadStatus === 'error' && 'border-destructive bg-destructive/5'
      )}
      onDragOver={(e) => {
        e.preventDefault();
        setIsDragging(true);
      }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={handleDrop}
    >
      <input
        type="file"
        id="file-upload"
        className="hidden"
        accept=".pdf"
        onChange={handleFileInput}
        disabled={uploadStatus === 'uploading'}
      />

      <label
        htmlFor="file-upload"
        className={cn(
          'flex flex-col items-center justify-center gap-4 cursor-pointer',
          uploadStatus === 'uploading' && 'cursor-not-allowed'
        )}
      >
        {uploadStatus === 'idle' && (
          <>
            <div className="rounded-full glass p-4">
              <Upload className="h-8 w-8 text-primary" />
            </div>
            <div className="text-center">
              <p className="text-sm font-medium">
                {isDragging ? 'Drop PDF here' : 'Upload research paper'}
              </p>
              <p className="text-xs text-muted-foreground mt-1">
                Drag and drop or click to browse (PDF only)
              </p>
            </div>
          </>
        )}

        {uploadStatus === 'uploading' && (
          <>
            <Loader2 className="h-8 w-8 text-primary animate-spin" />
            <div className="text-center">
              <p className="text-sm font-medium">Processing document...</p>
              <p className="text-xs text-muted-foreground mt-1">
                Extracting text and generating embeddings
              </p>
            </div>
          </>
        )}

        {uploadStatus === 'success' && (
          <>
            <CheckCircle className="h-8 w-8 text-primary" />
            <div className="text-center">
              <p className="text-sm font-medium text-primary">Upload successful!</p>
              <p className="text-xs text-muted-foreground mt-1">
                Document ready for analysis
              </p>
            </div>
          </>
        )}

        {uploadStatus === 'error' && (
          <>
            <XCircle className="h-8 w-8 text-destructive" />
            <div className="text-center">
              <p className="text-sm font-medium text-destructive">Upload failed</p>
              <p className="text-xs text-muted-foreground mt-1">
                Please try again
              </p>
            </div>
          </>
        )}
      </label>
    </div>
  );
}
