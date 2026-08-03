import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { SiteHeader } from "@/components/site-header";
import { TripWorkspace } from "@/components/trip/trip-workspace";
import { api, ApiError } from "@/lib/api";
import type { Trip } from "@/lib/types";

async function getTrip(id: string): Promise<Trip | null> {
  try {
    return await api.getTrip(id);
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) return null;
    throw err;
  }
}

export async function generateMetadata({
  params,
}: {
  params: { id: string };
}): Promise<Metadata> {
  const trip = await getTrip(params.id).catch(() => null);
  return { title: trip ? trip.title : "Trip" };
}

export default async function TripPage({ params }: { params: { id: string } }) {
  const trip = await getTrip(params.id);
  if (!trip) notFound();

  return (
    <div className="min-h-dvh">
      <SiteHeader />
      <TripWorkspace initialTrip={trip} />
    </div>
  );
}
