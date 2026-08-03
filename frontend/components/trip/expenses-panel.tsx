"use client";

import * as React from "react";
import {
  Bed,
  Bus,
  Loader2,
  Plus,
  ShoppingBag,
  Ticket,
  Trash2,
  TrendingUp,
  UtensilsCrossed,
} from "lucide-react";
import {
  Bar,
  BarChart,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input, Label } from "@/components/ui/input";
import {
  Progress,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/controls";
import { useToast } from "@/components/ui/toast";
import { api } from "@/lib/api";
import { EXPENSE_COLORS } from "@/lib/place-visual";
import type { ExpenseCategory, ExpenseStats, Trip } from "@/lib/types";
import { cn, formatDate, money, todayIso } from "@/lib/utils";

const CATEGORIES: { value: ExpenseCategory; label: string; icon: typeof Bed }[] = [
  { value: "food", label: "Food", icon: UtensilsCrossed },
  { value: "transport", label: "Transport", icon: Bus },
  { value: "shopping", label: "Shopping", icon: ShoppingBag },
  { value: "hotels", label: "Hotels", icon: Bed },
  { value: "activities", label: "Activities", icon: Ticket },
];

export function ExpensesPanel({
  trip,
  onTripChange,
}: {
  trip: Trip;
  onTripChange: (t: Trip) => void;
}) {
  const { toast } = useToast();
  const [stats, setStats] = React.useState<ExpenseStats | null>(null);
  const [label, setLabel] = React.useState("");
  const [amount, setAmount] = React.useState("");
  const [category, setCategory] = React.useState<ExpenseCategory>("food");
  const [date, setDate] = React.useState(defaultDate(trip));
  const [saving, setSaving] = React.useState(false);

  const { currency } = trip.preferences;

  React.useEffect(() => {
    api.expenseStats(trip.id).then(setStats).catch(() => setStats(null));
  }, [trip.id, trip.expenses.length, trip.updated_at]);

  async function addExpense(e: React.FormEvent) {
    e.preventDefault();
    const value = Number(amount);
    if (!value || value <= 0) {
      toast({ title: "Enter an amount above zero", tone: "warning" });
      return;
    }
    setSaving(true);
    try {
      const fresh = await api.addExpense(trip.id, {
        label: label.trim() || CATEGORIES.find((c) => c.value === category)!.label,
        amount: value,
        category,
        date,
      });
      onTripChange(fresh);
      setLabel("");
      setAmount("");
      toast({ title: "Expense logged", tone: "success" });
    } catch {
      toast({ title: "Couldn't save that expense", tone: "error" });
    } finally {
      setSaving(false);
    }
  }

  async function remove(id: string) {
    try {
      onTripChange(await api.deleteExpense(trip.id, id));
    } catch {
      toast({ title: "Couldn't delete that expense", tone: "error" });
    }
  }

  const pieData = React.useMemo(
    () =>
      Object.entries(stats?.by_category ?? {})
        .filter(([, v]) => v > 0)
        .map(([name, value]) => ({ name, value })),
    [stats],
  );

  return (
    <div className="space-y-6">
      {/* summary tiles */}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <StatTile
          label="Budget"
          value={money(trip.preferences.budget, currency)}
          hint={`${trip.preferences.travelers} travellers`}
        />
        <StatTile
          label="Spent"
          value={money(stats?.spent ?? 0, currency)}
          hint={`${Math.round(((stats?.spent ?? 0) / Math.max(trip.preferences.budget, 1)) * 100)}% of budget`}
        />
        <StatTile
          label="Remaining"
          value={money(stats?.remaining ?? trip.preferences.budget, currency)}
          hint={stats?.over_budget ? "Over budget" : "On track"}
          tone={stats?.over_budget ? "danger" : "good"}
        />
        <StatTile
          label="Daily average"
          value={money(stats?.daily_average ?? 0, currency)}
          hint={`Projected ${money(stats?.projected_total ?? 0, currency)}`}
        />
      </div>

      {stats && (
        <Card className="p-5">
          <div className="mb-2 flex items-baseline justify-between text-sm">
            <span className="font-medium">Budget used</span>
            <span className="text-muted-foreground tabular-nums">
              {money(stats.spent, currency)} / {money(stats.budget, currency)}
            </span>
          </div>
          <Progress
            value={Math.min((stats.spent / Math.max(stats.budget, 1)) * 100, 100)}
            indicatorClassName={
              stats.over_budget
                ? "bg-gradient-to-r from-orange-500 to-destructive"
                : undefined
            }
          />
          {stats.projected_total > stats.budget && (
            <p className="mt-3 flex items-center gap-1.5 text-xs text-[hsl(var(--warning))]">
              <TrendingUp className="size-3.5" />
              At this rate you'll finish about{" "}
              {money(stats.projected_total - stats.budget, currency)} over. Ask the
              companion to trim the coming days.
            </p>
          )}
        </Card>
      )}

      <div className="grid gap-5 lg:grid-cols-2">
        {/* pie */}
        <Card className="p-5">
          <h3 className="text-sm font-semibold">Where the money went</h3>
          {pieData.length ? (
            <div className="mt-2 h-64">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={pieData}
                    dataKey="value"
                    nameKey="name"
                    innerRadius={58}
                    outerRadius={92}
                    paddingAngle={2}
                    strokeWidth={0}
                  >
                    {pieData.map((entry) => (
                      <Cell key={entry.name} fill={EXPENSE_COLORS[entry.name]} />
                    ))}
                  </Pie>
                  <Tooltip
                    formatter={(value: number) => money(value, currency)}
                    contentStyle={tooltipStyle}
                  />
                  <Legend
                    verticalAlign="bottom"
                    iconType="circle"
                    formatter={(value: string) => (
                      <span className="text-xs capitalize text-muted-foreground">
                        {value}
                      </span>
                    )}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <p className="mt-8 text-center text-sm text-muted-foreground">
              Log an expense to see the split.
            </p>
          )}
        </Card>

        {/* daily bars */}
        <Card className="p-5">
          <h3 className="text-sm font-semibold">Spend by day</h3>
          <div className="mt-2 h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={stats?.by_day ?? []} barGap={2}>
                <XAxis
                  dataKey="label"
                  tick={{ fontSize: 11 }}
                  stroke="hsl(var(--muted-foreground))"
                  tickLine={false}
                  axisLine={false}
                />
                <YAxis
                  tick={{ fontSize: 11 }}
                  stroke="hsl(var(--muted-foreground))"
                  tickLine={false}
                  axisLine={false}
                  width={38}
                />
                <Tooltip
                  formatter={(value: number, name) => [
                    money(value, currency),
                    name === "amount" ? "Actual" : "Planned",
                  ]}
                  contentStyle={tooltipStyle}
                  cursor={{ fill: "hsl(var(--secondary))" }}
                />
                <Bar
                  dataKey="planned"
                  fill="hsl(var(--muted-foreground))"
                  fillOpacity={0.25}
                  radius={[4, 4, 0, 0]}
                />
                <Bar dataKey="amount" fill="hsl(var(--primary))" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <p className="mt-1 text-xs text-muted-foreground">
            Solid bars are what you actually spent; faded bars are the plan's estimate.
          </p>
        </Card>
      </div>

      {/* add form */}
      <Card className="p-5">
        <h3 className="text-sm font-semibold">Add an expense</h3>
        <form onSubmit={addExpense} className="mt-4 grid gap-3 sm:grid-cols-12">
          <div className="space-y-1.5 sm:col-span-4">
            <Label htmlFor="exp-label">What was it</Label>
            <Input
              id="exp-label"
              value={label}
              onChange={(e) => setLabel(e.target.value)}
              placeholder="Dinner at Ramiro"
            />
          </div>
          <div className="space-y-1.5 sm:col-span-2">
            <Label htmlFor="exp-amount">Amount</Label>
            <Input
              id="exp-amount"
              type="number"
              min="0.01"
              step="0.01"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              placeholder="0.00"
              required
            />
          </div>
          <div className="space-y-1.5 sm:col-span-3">
            <Label>Category</Label>
            <Select
              value={category}
              onValueChange={(v) => setCategory(v as ExpenseCategory)}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {CATEGORIES.map((c) => (
                  <SelectItem key={c.value} value={c.value}>
                    {c.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5 sm:col-span-2">
            <Label htmlFor="exp-date">Date</Label>
            <Input
              id="exp-date"
              type="date"
              value={date}
              min={trip.preferences.start_date}
              max={trip.preferences.end_date}
              onChange={(e) => setDate(e.target.value)}
            />
          </div>
          <div className="flex items-end sm:col-span-1">
            <Button type="submit" variant="gradient" size="icon" disabled={saving}>
              {saving ? <Loader2 className="animate-spin" /> : <Plus />}
            </Button>
          </div>
        </form>
      </Card>

      {/* list */}
      <Card className="overflow-hidden">
        <div className="flex items-center justify-between p-5 pb-3">
          <h3 className="text-sm font-semibold">Logged expenses</h3>
          <Badge variant="secondary">{trip.expenses.length}</Badge>
        </div>
        {trip.expenses.length === 0 ? (
          <p className="px-5 pb-5 text-sm text-muted-foreground">
            Nothing logged yet.
          </p>
        ) : (
          <ul className="divide-y divide-border">
            {[...trip.expenses].reverse().map((e) => {
              const meta = CATEGORIES.find((c) => c.value === e.category)!;
              return (
                <li
                  key={e.id}
                  className="flex items-center gap-3 px-5 py-3 transition-colors hover:bg-secondary/40"
                >
                  <span
                    className="grid size-9 shrink-0 place-items-center rounded-lg text-white"
                    style={{ background: EXPENSE_COLORS[e.category] }}
                  >
                    <meta.icon className="size-4" />
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium">{e.label}</p>
                    <p className="text-xs capitalize text-muted-foreground">
                      {e.category} · {formatDate(e.date)}
                    </p>
                  </div>
                  <span className="shrink-0 text-sm font-medium tabular-nums">
                    {money(e.amount, currency)}
                  </span>
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    onClick={() => remove(e.id)}
                    aria-label={`Delete ${e.label}`}
                    className="text-muted-foreground hover:text-destructive"
                  >
                    <Trash2 />
                  </Button>
                </li>
              );
            })}
          </ul>
        )}
      </Card>
    </div>
  );
}

const tooltipStyle = {
  background: "hsl(var(--popover))",
  border: "1px solid hsl(var(--border))",
  borderRadius: "0.75rem",
  fontSize: "0.8125rem",
  color: "hsl(var(--popover-foreground))",
} as const;

function StatTile({
  label,
  value,
  hint,
  tone,
}: {
  label: string;
  value: string;
  hint?: string;
  tone?: "good" | "danger";
}) {
  return (
    <Card className="p-4">
      <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
        {label}
      </p>
      <p className="mt-1.5 text-2xl font-semibold tabular-nums">{value}</p>
      {hint && (
        <p
          className={cn(
            "mt-0.5 text-xs",
            tone === "danger" && "text-destructive",
            tone === "good" && "text-[hsl(var(--success))]",
            !tone && "text-muted-foreground",
          )}
        >
          {hint}
        </p>
      )}
    </Card>
  );
}

function defaultDate(trip: Trip) {
  const today = todayIso();
  if (today >= trip.preferences.start_date && today <= trip.preferences.end_date) {
    return today;
  }
  return trip.preferences.start_date;
}
