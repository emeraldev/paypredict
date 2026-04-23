"use client";

import { DownloadIcon, UploadIcon } from "lucide-react";
import { useCallback, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { backtestApi } from "@/lib/api/backtest";

interface CsvUploadZoneProps {
  onResult: (result: unknown) => void;
  onError: (error: string) => void;
}

export function CsvUploadZone({ onResult, onError }: CsvUploadZoneProps) {
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [fileName, setFileName] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFile = useCallback(
    async (file: File) => {
      if (!file.name.toLowerCase().endsWith(".csv")) {
        onError("Please upload a .csv file");
        return;
      }
      setFileName(file.name);
      setUploading(true);
      try {
        const result = await backtestApi.uploadCsv(file);
        onResult(result);
      } catch (err) {
        onError(err instanceof Error ? err.message : "Upload failed");
      } finally {
        setUploading(false);
      }
    },
    [onResult, onError],
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragging(false);
      const file = e.dataTransfer.files[0];
      if (file) handleFile(file);
    },
    [handleFile],
  );

  return (
    <Card>
      <CardContent className="p-6">
        <div
          onDragOver={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={handleDrop}
          className={cn(
            "flex flex-col items-center justify-center gap-4 rounded-lg border-2 border-dashed p-10 transition-colors",
            dragging
              ? "border-primary bg-primary/5"
              : "border-border hover:border-primary/40",
          )}
        >
          <UploadIcon className="h-10 w-10 text-muted-foreground" />
          <div className="text-center">
            <p className="text-sm font-medium text-foreground">
              {uploading
                ? `Uploading ${fileName}...`
                : "Drag & drop a CSV file here"}
            </p>
            <p className="mt-1 text-xs text-muted-foreground">
              or click to browse. Max 500 rows, 10MB.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <Button
              size="sm"
              variant="outline"
              disabled={uploading}
              onClick={() => inputRef.current?.click()}
            >
              {uploading ? "Uploading..." : "Choose file"}
            </Button>
            <a
              href={backtestApi.templateUrl()}
              download
              className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground"
            >
              <DownloadIcon className="h-3.5 w-3.5" />
              Download template
            </a>
          </div>
          <input
            ref={inputRef}
            type="file"
            accept=".csv"
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) handleFile(file);
            }}
          />
        </div>
      </CardContent>
    </Card>
  );
}
