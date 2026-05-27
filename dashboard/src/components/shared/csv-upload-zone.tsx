"use client";

import { DownloadIcon, UploadIcon } from "lucide-react";
import { useCallback, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface CsvUploadZoneProps {
  /** Function that POSTs the file to the backend and returns the parsed response. */
  onUpload: (file: File) => Promise<unknown>;
  /** Called with the response from a successful upload. */
  onResult: (result: unknown) => void;
  /** Called with a human-readable error message on failure. */
  onError: (error: string) => void;
  /** URL the "Download template" button links to. */
  templateUrl: string;
  /** Required CSV column names shown to the user. */
  requiredColumns: string[];
  /** Optional columns shown after the required list. */
  optionalColumns?: string[];
  /** Short helper note shown after the file-size hint (e.g. "Max 500 rows, 5MB"). */
  sizeHint?: string;
}

export function CsvUploadZone({
  onUpload,
  onResult,
  onError,
  templateUrl,
  requiredColumns,
  optionalColumns,
  sizeHint = "Max 500 rows, 5MB.",
}: CsvUploadZoneProps) {
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
        const result = await onUpload(file);
        onResult(result);
      } catch (err) {
        onError(err instanceof Error ? err.message : "Upload failed");
      } finally {
        setUploading(false);
      }
    },
    [onUpload, onResult, onError],
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
              or click to browse. {sizeHint}
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
              href={templateUrl}
              download
              className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground"
            >
              <DownloadIcon className="h-3.5 w-3.5" />
              Download template
            </a>
          </div>
          <div className="mt-2 max-w-md text-left text-[11px] text-muted-foreground/70">
            <p className="font-medium text-muted-foreground mb-1">Required columns:</p>
            <p>
              {requiredColumns.map((col, i) => (
                <span key={col}>
                  <span className="font-mono">{col}</span>
                  {i < requiredColumns.length - 1 ? ", " : ""}
                </span>
              ))}
            </p>
            {optionalColumns && optionalColumns.length > 0 && (
              <p className="mt-1">
                Optional:{" "}
                {optionalColumns.map((col, i) => (
                  <span key={col}>
                    <span className="font-mono">{col}</span>
                    {i < optionalColumns.length - 1 ? ", " : ""}
                  </span>
                ))}
              </p>
            )}
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
