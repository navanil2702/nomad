"use client";

import * as React from "react";
import { AnimatePresence, motion } from "framer-motion";
import { AlertTriangle, CheckCircle2, Info, X, XCircle } from "lucide-react";

import { cn } from "@/lib/utils";

type ToastTone = "info" | "success" | "warning" | "error";

interface Toast {
  id: string;
  title: string;
  description?: string;
  tone: ToastTone;
}

interface ToastContextValue {
  toast: (t: Omit<Toast, "id" | "tone"> & { tone?: ToastTone }) => void;
}

const ToastContext = React.createContext<ToastContextValue | null>(null);

const TONE_ICON = {
  info: Info,
  success: CheckCircle2,
  warning: AlertTriangle,
  error: XCircle,
} as const;

const TONE_CLASS: Record<ToastTone, string> = {
  info: "text-primary",
  success: "text-[hsl(var(--success))]",
  warning: "text-[hsl(var(--warning))]",
  error: "text-destructive",
};

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = React.useState<Toast[]>([]);

  const dismiss = React.useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const toast = React.useCallback<ToastContextValue["toast"]>(
    ({ title, description, tone = "info" }) => {
      const id = Math.random().toString(36).slice(2);
      setToasts((prev) => [...prev.slice(-2), { id, title, description, tone }]);
      setTimeout(() => dismiss(id), 5200);
    },
    [dismiss],
  );

  return (
    <ToastContext.Provider value={{ toast }}>
      {children}
      <div className="pointer-events-none fixed inset-x-0 bottom-0 z-[70] flex flex-col items-center gap-2 p-4 sm:items-end sm:p-6">
        <AnimatePresence initial={false}>
          {toasts.map((t) => {
            const Icon = TONE_ICON[t.tone];
            return (
              <motion.div
                key={t.id}
                layout
                initial={{ opacity: 0, y: 16, scale: 0.96 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: 8, scale: 0.96 }}
                transition={{ type: "spring", stiffness: 380, damping: 30 }}
                className="pointer-events-auto flex w-full max-w-sm items-start gap-3 rounded-2xl border border-border bg-card p-4 shadow-xl"
              >
                <Icon className={cn("mt-0.5 size-5 shrink-0", TONE_CLASS[t.tone])} />
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium leading-snug">{t.title}</p>
                  {t.description && (
                    <p className="mt-0.5 text-sm leading-snug text-muted-foreground">
                      {t.description}
                    </p>
                  )}
                </div>
                <button
                  onClick={() => dismiss(t.id)}
                  className="rounded-full p-1 text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
                  aria-label="Dismiss"
                >
                  <X className="size-3.5" />
                </button>
              </motion.div>
            );
          })}
        </AnimatePresence>
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const ctx = React.useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used inside ToastProvider");
  return ctx;
}
