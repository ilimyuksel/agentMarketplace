"use client";

import { useEffect } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { X } from "lucide-react";

interface Props {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  subtitle?: string;
  children: React.ReactNode;
}

export function Modal({ isOpen, onClose, title, subtitle, children }: Props) {
  // ESC key + body scroll lock while open.
  useEffect(() => {
    if (!isOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    window.addEventListener("keydown", onKey);
    return () => {
      document.body.style.overflow = prevOverflow;
      window.removeEventListener("keydown", onKey);
    };
  }, [isOpen, onClose]);

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.18 }}
          // Hardcoded dark backdrop so it dims correctly regardless of whether
          // the modal opened from light-content or dark-chrome.
          style={{ backgroundColor: "rgba(15, 21, 37, 0.7)" }}
          className="fixed inset-0 z-[100] flex items-center justify-center backdrop-blur-sm px-4"
          onClick={onClose}
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.96, y: 4 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.96, y: 4 }}
            transition={{ duration: 0.18, ease: [0.22, 1, 0.36, 1] }}
            onClick={(e) => e.stopPropagation()}
            className="content-light rounded-lg border border-line bg-elevated shadow-2xl w-full max-w-md max-h-[80vh] overflow-y-auto"
            role="dialog"
            aria-modal="true"
            aria-label={title}
          >
            <header className="flex items-start justify-between gap-3 px-5 py-4 border-b border-line">
              <div className="min-w-0">
                <h2
                  className="text-base font-semibold text-text-primary"
                  style={{ fontFamily: "var(--font-space-grotesk)" }}
                >
                  {title}
                </h2>
                {subtitle && (
                  <p className="text-[11px] text-text-muted mt-0.5">{subtitle}</p>
                )}
              </div>
              <button
                type="button"
                onClick={onClose}
                aria-label="Close"
                className="flex-shrink-0 text-text-faint hover:text-text-primary transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </header>
            <div className="p-6">{children}</div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
