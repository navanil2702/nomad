"use client";

import Link from "next/link";
import { Compass, LogOut } from "lucide-react";

import { Button } from "@/components/ui/button";
import { ProviderBadge } from "@/components/provider-badge";
import { ThemeToggle } from "@/components/theme-toggle";
import { useAuth } from "@/lib/auth";
import { cn } from "@/lib/utils";

export function Logo({ className }: { className?: string }) {
  return (
    <Link href="/" className={cn("flex items-center gap-2.5", className)}>
      <span className="grid size-9 place-items-center rounded-xl bg-gradient-to-br from-primary to-accent text-primary-foreground shadow-sm">
        <Compass className="size-5" strokeWidth={2.2} />
      </span>
      <span className="text-lg font-semibold tracking-tight">Nomad</span>
    </Link>
  );
}

export function SiteHeader({ sticky = true }: { sticky?: boolean }) {
  const { user, signIn, signOut, ready } = useAuth();

  return (
    <header
      className={cn(
        "z-40 w-full border-b border-border/60 bg-background/80 backdrop-blur-xl",
        sticky && "sticky top-0",
      )}
    >
      <div className="container flex h-16 items-center justify-between gap-4">
        <Logo />

        <div className="flex items-center gap-1.5">
          <Button variant="ghost" size="sm" asChild className="hidden sm:inline-flex">
            <Link href="/trips">My trips</Link>
          </Button>
          <ProviderBadge />
          <ThemeToggle />
          {ready &&
            (user ? (
              <div className="flex items-center gap-2 pl-1">
                <span className="hidden text-sm text-muted-foreground sm:inline">
                  {user.name.split(" ")[0]}
                </span>
                <Button
                  variant="ghost"
                  size="icon-sm"
                  onClick={signOut}
                  aria-label="Sign out"
                >
                  <LogOut />
                </Button>
              </div>
            ) : (
              <Button size="sm" variant="outline" onClick={() => void signIn()}>
                <GoogleMark />
                <span className="hidden sm:inline">Sign in</span>
              </Button>
            ))}
        </div>
      </div>
    </header>
  );
}

export function GoogleMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={cn("size-4", className)} aria-hidden>
      <path
        fill="#4285F4"
        d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.76h3.57c2.08-1.92 3.28-4.74 3.28-8.09Z"
      />
      <path
        fill="#34A853"
        d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.76c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84A11 11 0 0 0 12 23Z"
      />
      <path
        fill="#FBBC05"
        d="M5.84 14.11a6.6 6.6 0 0 1 0-4.22V7.05H2.18a11 11 0 0 0 0 9.9l3.66-2.84Z"
      />
      <path
        fill="#EA4335"
        d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1a11 11 0 0 0-9.82 6.05l3.66 2.84c.87-2.6 3.3-4.51 6.16-4.51Z"
      />
    </svg>
  );
}
