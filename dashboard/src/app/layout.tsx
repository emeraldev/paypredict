import type { Metadata } from "next";
import { Geist_Mono, Inter } from "next/font/google";
import { Toaster } from "@/components/ui/sonner";
import { AuthProvider } from "@/hooks/use-auth";
import { ThemeProvider, themeNoFlashScript } from "@/hooks/use-theme";
import "./globals.css";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "PayPredict",
  description: "Pre-collection risk scoring dashboard",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${inter.variable} ${geistMono.variable} h-full antialiased`}
      suppressHydrationWarning
    >
      <body className="min-h-full flex flex-col">
        {/*
          Theme no-flash script. Must be the first child of <body> so it runs
          synchronously before any DOM paints. suppressHydrationWarning prevents
          React 19 from warning about script tags inside the component tree.
          This script only needs to run once during initial HTML parse, not on
          subsequent client-side renders.
        */}
        <script
          suppressHydrationWarning
          dangerouslySetInnerHTML={{ __html: themeNoFlashScript }}
        />
        <ThemeProvider>
          <AuthProvider>
            {children}
            <Toaster richColors position="top-right" />
          </AuthProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
