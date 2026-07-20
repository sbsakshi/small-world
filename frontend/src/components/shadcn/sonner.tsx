"use client"

import { Toaster as Sonner, type ToasterProps } from "sonner"
import { CircleCheckIcon, InfoIcon, TriangleAlertIcon, OctagonXIcon, Loader2Icon } from "lucide-react"

// This app doesn't support a dark theme yet (tokens.css is light-only), so
// the toaster is pinned to "light" rather than following next-themes/system.
const Toaster = ({ ...props }: ToasterProps) => {
  return (
    <Sonner
      theme="light"
      position="top-center"
      className="toaster group"
      icons={{
        success: (
          <CircleCheckIcon className="size-4" />
        ),
        info: (
          <InfoIcon className="size-4" />
        ),
        warning: (
          <TriangleAlertIcon className="size-4" />
        ),
        error: (
          <OctagonXIcon className="size-4" />
        ),
        loading: (
          <Loader2Icon className="size-4 animate-spin" />
        ),
      }}
      style={
        {
          "--normal-bg": "var(--surface)",
          "--normal-text": "var(--ink)",
          "--normal-border": "var(--border-strong)",
          "--success-bg": "var(--good-bg)",
          "--success-text": "var(--good-ink)",
          "--success-border": "var(--good-ink)",
          "--warning-bg": "var(--warn-bg)",
          "--warning-text": "var(--warn-ink)",
          "--warning-border": "var(--warn-ink)",
          "--error-bg": "color-mix(in oklch, var(--priority-high) 12%, white)",
          "--error-text": "var(--priority-high)",
          "--error-border": "var(--priority-high)",
          "--border-radius": "var(--r-lg)",
          "--font-sans": "var(--font)",
        } as React.CSSProperties
      }
      toastOptions={{
        classNames: {
          toast: "cn-toast",
        },
      }}
      {...props}
    />
  )
}

export { Toaster }
