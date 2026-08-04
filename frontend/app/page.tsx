import Link from "next/link";
import {
  ArrowRight,
  BookHeart,
  CloudSun,
  Languages,
  Luggage,
  MapPin,
  Radar,
  Route,
  Wallet,
  WifiOff,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { SiteHeader } from "@/components/site-header";
import { CompanionDemo } from "@/components/landing/companion-demo";
import { HeroIllustration } from "@/components/landing/hero-illustration";
import { api } from "@/lib/api";
import type { DestinationOption } from "@/lib/types";

const STEPS = [
  {
    icon: Route,
    title: "Tell it the shape of the trip",
    body: "Where, when, how much, how many of you, and what you actually enjoy. Thirty seconds, one screen.",
  },
  {
    icon: MapPin,
    title: "Get a plan built around real constraints",
    body: "Opening hours, travel time between stops, your budget and the forecast — not a generic top-ten list.",
  },
  {
    icon: Radar,
    title: "Then let it watch the trip for you",
    body: "It re-checks the weather, your spending and the shape of each day, and rewrites the plan before the problem reaches you.",
  },
];

const FEATURES = [
  {
    icon: Radar,
    title: "Proactive, not reactive",
    body: "Rain at 2 PM tomorrow? The beach is already moved to Friday and the museum is in its place before you ask.",
  },
  {
    icon: CloudSun,
    title: "Weather-aware planning",
    body: "Forecast-driven warnings, and indoor alternatives chosen from places that are genuinely open at that hour.",
  },
  {
    icon: Wallet,
    title: "Budget that self-corrects",
    body: "Log spending as you go. Run hot and the companion trims the coming days rather than telling you off.",
  },
  {
    icon: Luggage,
    title: "Packing from the actual plan",
    body: "A list derived from your forecast, your activities and the country's plug type — not a generic checklist.",
  },
  {
    icon: BookHeart,
    title: "A journal that writes itself",
    body: "Each evening it records where you went, what you spent and how the day felt, then binds it into a travel journal.",
  },
  {
    icon: Languages,
    title: "The small stuff, handled",
    body: "Local phrases, emergency numbers with the nearest hospital and police, live currency and time-zone conversion, and a printable PDF of the whole trip.",
  },
];

async function getDestinations(): Promise<DestinationOption[]> {
  try {
    return await api.destinations();
  } catch {
    return [];
  }
}

export default async function LandingPage() {
  const destinations = await getDestinations();

  return (
    <div className="min-h-dvh">
      <SiteHeader />

      {/* ---------------------------------------------------------- hero */}
      <section className="aurora relative overflow-hidden">
        <div className="grid-lines pointer-events-none absolute inset-0 opacity-[0.35] [mask-image:radial-gradient(60%_50%_at_50%_0%,black,transparent)]" />

        <div className="container relative py-16 sm:py-24">
          <div className="grid items-center gap-12 lg:grid-cols-[1.05fr_1fr] lg:gap-16">
            <div>
              <Badge variant="outline" className="mb-5 gap-1.5 bg-background/60 py-1">
                <Radar className="size-3" />
                Real-time travel companion
              </Badge>

              <h1 className="text-balance text-4xl font-semibold leading-[1.05] tracking-tight sm:text-5xl lg:text-6xl">
                Planning is easy.
                <br />
                <span className="font-display text-gradient text-[1.15em] font-normal italic">
                  Travel changes.
                </span>
                <br />
                Your itinerary should adapt.
              </h1>

              <p className="mt-6 max-w-xl text-pretty text-lg leading-relaxed text-muted-foreground">
                Nomad builds a day-by-day plan around your budget, your pace and the
                real forecast — then keeps watching. When the rain arrives or the
                train is late, it has already moved things around and tells you what
                it did.
              </p>

              <div className="mt-8 flex flex-col gap-3 sm:flex-row">
                <Button size="lg" variant="gradient" asChild>
                  <Link href="/plan">
                    Plan My Trip
                    <ArrowRight />
                  </Link>
                </Button>
                <Button size="lg" variant="outline" asChild>
                  <Link href="/trips">See a live trip</Link>
                </Button>
              </div>

              <p className="mt-4 text-sm text-muted-foreground">
                No account needed to try it. A sample trip is already loaded.
              </p>
            </div>

            <div className="relative">
              <HeroIllustration className="w-full" />
              <CompanionDemo className="mx-auto -mt-16 w-[92%] sm:-mt-20 lg:-mt-24" />
            </div>
          </div>
        </div>
      </section>

      {/* -------------------------------------------------- how it works */}
      <section className="border-t border-border/60 py-16 sm:py-24">
        <div className="container">
          <div className="max-w-2xl">
            <p className="text-sm font-medium uppercase tracking-wide text-primary">
              How the companion works
            </p>
            <h2 className="mt-3 text-3xl font-semibold tracking-tight sm:text-4xl">
              It plans once, then keeps working
            </h2>
            <p className="mt-4 text-lg text-muted-foreground">
              Most trip planners hand you a document and stop. This one stays with you
              for the whole trip.
            </p>
          </div>

          <div className="mt-12 grid gap-5 md:grid-cols-3">
            {STEPS.map((step, i) => (
              <Card key={step.title} className="relative overflow-hidden p-6">
                <span className="font-display text-5xl leading-none text-primary/15">
                  0{i + 1}
                </span>
                <step.icon className="mt-4 size-6 text-primary" />
                <h3 className="mt-4 text-lg font-semibold tracking-tight">
                  {step.title}
                </h3>
                <p className="mt-2 leading-relaxed text-muted-foreground">{step.body}</p>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* ------------------------------------------------------- features */}
      <section className="border-t border-border/60 bg-secondary/30 py-16 sm:py-24">
        <div className="container">
          <div className="max-w-2xl">
            <p className="text-sm font-medium uppercase tracking-wide text-primary">
              What you get
            </p>
            <h2 className="mt-3 text-3xl font-semibold tracking-tight sm:text-4xl">
              Everything the trip actually needs
            </h2>
          </div>

          <div className="mt-12 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {FEATURES.map((f) => (
              <Card key={f.title} className="p-6" interactive>
                <span className="grid size-11 place-items-center rounded-xl bg-primary/10 text-primary">
                  <f.icon className="size-5" />
                </span>
                <h3 className="mt-4 font-semibold tracking-tight">{f.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                  {f.body}
                </p>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* --------------------------------------------------- destinations */}
      {destinations.length > 0 && (
        <section className="border-t border-border/60 py-16 sm:py-24">
          <div className="container">
            <div className="flex flex-wrap items-end justify-between gap-4">
              <div className="max-w-2xl">
                <p className="text-sm font-medium uppercase tracking-wide text-primary">
                  Hand-checked destinations
                </p>
                <h2 className="mt-3 text-3xl font-semibold tracking-tight sm:text-4xl">
                  Curated down to the opening hours
                </h2>
                <p className="mt-4 text-muted-foreground">
                  These cities have hand-checked catalogs behind them — real
                  prices, indoor alternatives, walking effort and tips written by
                  someone who went. Everywhere else is planned from live Google
                  Places, with the same attributes derived automatically.
                </p>
              </div>
              <Button variant="outline" asChild>
                <Link href="/plan">
                  Start planning <ArrowRight />
                </Link>
              </Button>
            </div>

            <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {destinations.map((d) => (
                <Link key={d.key} href={`/plan?destination=${encodeURIComponent(d.label)}`}>
                  <Card className="h-full p-5" interactive>
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <h3 className="font-semibold tracking-tight">{d.name}</h3>
                        <p className="text-sm text-muted-foreground">{d.country}</p>
                      </div>
                      <Badge variant="secondary">{d.places} places</Badge>
                    </div>
                    <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
                      {d.blurb}
                    </p>
                  </Card>
                </Link>
              ))}
            </div>
          </div>
        </section>
      )}

      {/* ------------------------------------------------------------ cta */}
      <section className="border-t border-border/60">
        <div className="container py-16 sm:py-24">
          <Card className="aurora relative overflow-hidden border-primary/20 p-8 text-center sm:p-14">
            <div className="grid-lines pointer-events-none absolute inset-0 opacity-25" />
            <div className="relative mx-auto max-w-2xl">
              <h2 className="text-balance text-3xl font-semibold tracking-tight sm:text-4xl">
                The plan you leave with is not the trip you have
              </h2>
              <p className="mt-4 text-lg text-muted-foreground">
                Give Nomad five details and it will handle the rest of the week —
                including the parts that go wrong.
              </p>
              <div className="mt-8 flex flex-col justify-center gap-3 sm:flex-row">
                <Button size="lg" variant="gradient" asChild>
                  <Link href="/plan">
                    Plan My Trip <ArrowRight />
                  </Link>
                </Button>
                <Button size="lg" variant="outline" asChild>
                  <Link href="/trips">Open the sample trip</Link>
                </Button>
              </div>
            </div>
          </Card>
        </div>
      </section>

      <footer className="border-t border-border/60 py-10">
        <div className="container flex flex-col items-center justify-between gap-4 text-sm text-muted-foreground sm:flex-row">
          <p>Nomad — a travel companion, not a chatbot.</p>
          <p className="flex items-center gap-1.5">
            <WifiOff className="size-3.5" />
            Live data when it's there, offline engines when it isn't
          </p>
        </div>
      </footer>
    </div>
  );
}
