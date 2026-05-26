"use client";

import { useState } from "react";
import Link from "next/link";
import { toast } from "sonner";
import {
  ArrowRightIcon,
  CheckIcon,
  CopyIcon,
  ExternalLinkIcon,
  KeyIcon,
  RocketIcon,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001";

// shadcn's Button here is a base-ui primitive — no `asChild`. We mirror
// the outline + sm variant on raw anchor/Link elements instead.
const LINK_BUTTON_CLS =
  "inline-flex h-7 items-center gap-1.5 rounded-[12px] border border-border bg-background px-2.5 text-[0.8rem] font-medium text-foreground transition-colors hover:bg-muted dark:border-input dark:bg-input/30 dark:hover:bg-input/50";

const SAMPLE_CURL = `curl -X POST ${API_URL}/v1/score \\
  -H "Authorization: Bearer pk_live_YOUR_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{
    "customer_id": "cust_001",
    "collection_id": "inst_001",
    "collection_amount": 1500.00,
    "collection_currency": "ZAR",
    "collection_due_date": "2026-06-15",
    "collection_method": "CARD",
    "customer_data": {
      "total_payments": 10,
      "successful_payments": 8,
      "card_type": "debit",
      "known_salary_day": 25
    }
  }'`;

export function CollectionsOnboarding() {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(SAMPLE_CURL);
      setCopied(true);
      toast.success("curl command copied");
      setTimeout(() => setCopied(false), 2000);
    } catch {
      toast.error("Could not copy — try selecting the text manually");
    }
  };

  return (
    <div className="space-y-6 px-4 py-8">
      <div className="space-y-2 text-center">
        <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-muted/60 text-muted-foreground ring-1 ring-border/60">
          <RocketIcon className="h-6 w-6" />
        </div>
        <h2 className="text-lg font-semibold text-foreground">
          Score your first collection
        </h2>
        <p className="mx-auto max-w-xl text-sm text-muted-foreground">
          Once your backend sends scoring requests to PayPredict, they&apos;ll
          appear here ranked by risk. Two steps to get there.
        </p>
      </div>

      <div className="mx-auto grid max-w-3xl gap-4 sm:grid-cols-2">
        <Card>
          <CardContent className="space-y-3 p-5">
            <div className="flex items-center gap-2">
              <span className="flex h-6 w-6 items-center justify-center rounded-full bg-primary/10 text-xs font-bold text-primary">
                1
              </span>
              <h3 className="text-sm font-semibold text-foreground">
                Create an API key
              </h3>
            </div>
            <p className="text-sm text-muted-foreground">
              You&apos;ll need a <code className="rounded bg-muted px-1 text-xs">pk_live_…</code> key
              to authenticate requests. Created keys are shown once and
              hashed at rest.
            </p>
            <Link
              href="/dashboard/settings?tab=api-keys"
              className={LINK_BUTTON_CLS}
            >
              <KeyIcon className="h-3.5 w-3.5" />
              Go to API Keys
              <ArrowRightIcon className="h-3.5 w-3.5" />
            </Link>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="space-y-3 p-5">
            <div className="flex items-center gap-2">
              <span className="flex h-6 w-6 items-center justify-center rounded-full bg-primary/10 text-xs font-bold text-primary">
                2
              </span>
              <h3 className="text-sm font-semibold text-foreground">
                Make your first scoring call
              </h3>
            </div>
            <p className="text-sm text-muted-foreground">
              Send a collection to <code className="rounded bg-muted px-1 text-xs">POST /v1/score</code>.
              You&apos;ll get a risk score, factor breakdown, and a
              recommended action back in under 30ms.
            </p>
            <div className="flex flex-wrap gap-2">
              <a
                href={`${API_URL}/docs`}
                target="_blank"
                rel="noopener noreferrer"
                className={LINK_BUTTON_CLS}
              >
                Open Swagger
                <ExternalLinkIcon className="h-3.5 w-3.5" />
              </a>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="mx-auto max-w-3xl space-y-2">
        <div className="flex items-center justify-between">
          <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Sample request
          </p>
          <Button
            variant="ghost"
            size="xs"
            onClick={handleCopy}
            className="gap-1.5"
          >
            {copied ? (
              <>
                <CheckIcon className="h-3 w-3 text-emerald-500" />
                Copied
              </>
            ) : (
              <>
                <CopyIcon className="h-3 w-3" />
                Copy
              </>
            )}
          </Button>
        </div>
        <pre className="max-h-72 overflow-auto rounded-md border border-border bg-muted/40 p-4 font-mono text-xs leading-relaxed text-foreground">
          {SAMPLE_CURL}
        </pre>
        <p className="text-xs text-muted-foreground">
          Need a hand mapping the response to your queue? The Swagger
          quick-start at{" "}
          <a
            href={`${API_URL}/docs`}
            target="_blank"
            rel="noopener noreferrer"
            className="text-foreground underline decoration-muted-foreground/40 underline-offset-2 hover:decoration-foreground"
          >
            {API_URL}/docs
          </a>{" "}
          covers what each <code className="rounded bg-muted px-1 text-[10px]">recommended_action</code>{" "}
          value means and which <code className="rounded bg-muted px-1 text-[10px]">customer_data</code>{" "}
          fields move the score the most.
        </p>
      </div>
    </div>
  );
}
