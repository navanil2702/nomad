import { Suspense } from "react";
import type { Metadata } from "next";

import { SiteHeader } from "@/components/site-header";
import { TripForm } from "@/components/plan/trip-form";
import { Skeleton } from "@/components/ui/controls";
import { api } from "@/lib/api";
import type { DestinationOption } from "@/lib/types";

export const metadata: Metadata = { title: "Plan a trip" };

async function getDestinations(): Promise<DestinationOption[]> {
  try {
    return await api.destinations();
  } catch {
    return [];
  }
}

export default async function PlanPage() {
  const destinations = await getDestinations();

  return (
    <div className="min-h-dvh">
      <SiteHeader />
      <main className="aurora relative">
        <div className="grid-lines pointer-events-none absolute inset-0 opacity-25 [mask-image:radial-gradient(60%_40%_at_50%_0%,black,transparent)]" />
        <div className="container relative py-10 sm:py-16">
          <div className="mx-auto mb-8 max-w-2xl text-center">
            <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">
              Let's shape the trip
            </h1>
            <p className="mt-3 text-muted-foreground">
              Five details. The companion handles opening hours, travel time, the
              forecast and your budget from there.
            </p>
          </div>

          <Suspense fallback={<Skeleton className="mx-auto h-[520px] max-w-2xl" />}>
            <TripForm destinations={destinations} />
          </Suspense>
        </div>
      </main>
    </div>
  );
}
