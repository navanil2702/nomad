"""The offline itinerary, as a PDF you can print or keep on a phone.

Built with fpdf2 because it is pure Python — no cairo, no pango, nothing that
needs a system library — which is what makes it deployable on serverless.

The one cost of that choice is fonts. fpdf2's built-in fonts are Latin-1, so
anything outside it (the o-macron in "Sensō-ji", any Devanagari or CJK name)
would raise rather than render. `_latin` folds text down to the closest ASCII
instead: "Senso-ji" is imperfect but legible, and it means the document never
fails on a destination. Embedding a Unicode TTF would fix the accents at the
cost of ~700KB in the bundle, and still not cover CJK.
"""

from __future__ import annotations

import unicodedata
from datetime import date

from fpdf import FPDF

from ..models.schemas import LocalInfo, Trip
from . import places as places_svc

# Matches the app's palette so the print-out looks like the product.
INK = (24, 28, 36)
MUTED = (118, 124, 138)
PRIMARY = (26, 122, 100)
ACCENT = (214, 106, 42)
RULE = (222, 218, 212)


def _latin(text: str) -> str:
    """Fold to something the Latin-1 core fonts can actually render."""
    if not text:
        return ""
    swaps = {"—": "-", "–": "-", "’": "'", "‘": "'", "“": '"', "”": '"', "·": "-", "€": "EUR ", "₹": "Rs ", "¥": "JPY ", "£": "GBP "}
    for a, b in swaps.items():
        text = text.replace(a, b)
    # Decompose accents, drop the combining marks, keep the base letters.
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return text.encode("latin-1", "replace").decode("latin-1").replace("?", "")


class ItineraryPDF(FPDF):
    def __init__(self, trip: Trip) -> None:
        super().__init__(orientation="P", unit="mm", format="A4")
        self.trip = trip
        self.set_auto_page_break(auto=True, margin=18)
        self.set_margins(16, 16, 16)

    def footer(self) -> None:
        self.set_y(-14)
        self.set_font("Helvetica", size=8)
        self.set_text_color(*MUTED)
        self.cell(
            self.content_width,
            5,
            _latin(f"{self.trip.title}  ·  page {self.page_no()}"),
            align="C",
            new_x="LMARGIN",
            new_y="NEXT",
        )

    # -- building blocks ---------------------------------------------------
    @property
    def content_width(self) -> float:
        return self.w - self.l_margin - self.r_margin

    def rule(self, gap: float = 3) -> None:
        self.ln(gap)
        self.set_draw_color(*RULE)
        self.set_line_width(0.2)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(gap)

    def flow(
        self,
        text: str,
        *,
        height: float,
        indent: float = 0,
    ) -> None:
        """Wrapped text at an explicit width.

        Widths are never left to `w=0`, which measures from wherever the cursor
        happens to be. A footer or a preceding cell can leave x at the right
        margin, and the remaining width then rounds to less than one character
        — which fpdf2 reports as a hard error rather than a wrap.
        """
        self.set_x(self.l_margin + indent)
        self.multi_cell(self.content_width - indent, height, _latin(text))

    def heading(self, text: str, size: int = 15) -> None:
        self.set_font("Helvetica", "B", size)
        self.set_text_color(*INK)
        self.flow(text, height=7)
        self.ln(1)

    def label(self, text: str) -> None:
        self.set_font("Helvetica", "B", 8)
        self.set_text_color(*MUTED)
        self.set_x(self.l_margin)
        self.cell(
            self.content_width, 4, _latin(text.upper()), new_x="LMARGIN", new_y="NEXT"
        )

    def body(self, text: str, size: float = 9.5, colour=INK, indent: float = 0) -> None:
        self.set_font("Helvetica", size=size)
        self.set_text_color(*colour)
        self.flow(text, height=4.6, indent=indent)


def _cover(pdf: ItineraryPDF, trip: Trip, info: LocalInfo) -> None:
    prefs = trip.preferences
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(*PRIMARY)
    pdf.cell(pdf.content_width, 5, "NOMAD", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    pdf.set_font("Helvetica", "B", 26)
    pdf.set_text_color(*INK)
    pdf.flow(trip.title or prefs.destination, height=11)
    pdf.ln(1)

    pdf.set_font("Helvetica", size=11)
    pdf.set_text_color(*MUTED)
    pdf.flow(prefs.destination, height=6)

    pdf.rule(5)

    rows = [
        ("Dates", f"{prefs.start_date:%a %d %b %Y}  to  {prefs.end_date:%a %d %b %Y}"),
        ("Travellers", str(prefs.travelers)),
        ("Budget", f"{prefs.currency} {prefs.budget:,.0f}"),
        ("Pace", prefs.pace.value.title()),
        ("Time zone", f"{info.timezone} (UTC{info.utc_offset_hours:+g})"),
        ("Language", info.language),
    ]
    for name, value in rows:
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*MUTED)
        pdf.set_x(pdf.l_margin)
        pdf.cell(34, 6, _latin(name))
        pdf.set_font("Helvetica", size=10)
        pdf.set_text_color(*INK)
        pdf.cell(pdf.content_width - 34, 6, _latin(value), new_x="LMARGIN", new_y="NEXT")

    pdf.rule(5)
    pdf.body(
        "Everything here works without a connection. Times and prices are "
        "estimates from the plan, not bookings.",
        colour=MUTED,
    )


def _days(pdf: ItineraryPDF, trip: Trip) -> None:
    currency = trip.preferences.currency
    by_date = {w.date: w for w in trip.weather}

    for day in trip.days:
        pdf.add_page()
        weather = by_date.get(day.date)

        pdf.label(f"Day {day.day_number}  ·  {day.date:%A %d %B}")
        pdf.heading(day.title or f"Day {day.day_number}", 17)

        if weather:
            pdf.body(
                f"{weather.description}, {weather.temp_min_c:.0f}-"
                f"{weather.temp_max_c:.0f} C, {weather.precipitation_chance}% "
                "chance of rain.",
                colour=MUTED,
            )
        if day.summary:
            pdf.body(day.summary, colour=MUTED)

        pdf.rule(4)

        for act in day.activities:
            if pdf.get_y() > pdf.h - 55:
                pdf.add_page()

            # Time column, then everything else indented beside it.
            pdf.set_x(pdf.l_margin)
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(*PRIMARY)
            pdf.cell(22, 5, _latin(act.start_time))

            pdf.set_font("Helvetica", "B", 11)
            pdf.set_text_color(*INK)
            pdf.multi_cell(pdf.content_width - 22, 5, _latin(act.place.name))

            bits = [act.place.opening_hours]
            if act.place.address:
                bits.append(act.place.address)
            bits.append(
                f"{currency} {act.estimated_cost:,.0f}"
                if act.estimated_cost
                else "Free"
            )
            if act.travel_time_minutes:
                bits.append(f"{act.travel_time_minutes} min by {act.travel_mode}")
            pdf.set_font("Helvetica", size=8.5)
            pdf.set_text_color(*MUTED)
            pdf.flow("  ·  ".join(bits), height=4.2, indent=22)

            if act.local_tip:
                pdf.set_font("Helvetica", "I", 8.5)
                pdf.set_text_color(*ACCENT)
                pdf.flow(act.local_tip, height=4.2, indent=22)

            pdf.set_font("Helvetica", size=7.5)
            pdf.set_text_color(*MUTED)
            coords = f"{act.place.coordinates.lat:.5f}, {act.place.coordinates.lng:.5f}"
            pdf.flow(coords, height=4, indent=22)
            pdf.ln(2.5)

        pdf.rule(2)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*INK)
        pdf.set_x(pdf.l_margin)
        pdf.cell(
            pdf.content_width,
            5,
            _latin(
                f"Day total {currency} {day.estimated_cost:,.0f}"
                f"   ·   {day.total_travel_minutes} min moving"
            ),
            new_x="LMARGIN",
            new_y="NEXT",
        )


def _reference(pdf: ItineraryPDF, trip: Trip, info: LocalInfo) -> None:
    pdf.add_page()
    pdf.heading("If something goes wrong", 17)
    pdf.body(
        f"{info.city}{', ' + info.region if info.region else ''}, {info.country}",
        colour=MUTED,
    )
    pdf.ln(2)

    for contact in info.emergency:
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(*INK)
        pdf.set_x(pdf.l_margin)
        pdf.cell(52, 6, _latin(contact.number))
        pdf.set_font("Helvetica", size=9.5)
        pdf.cell(pdf.content_width - 52, 6, _latin(contact.label),
                 new_x="LMARGIN", new_y="NEXT")
        if contact.note:
            pdf.set_font("Helvetica", size=8)
            pdf.set_text_color(*MUTED)
            pdf.flow(contact.note, height=4, indent=52)

    if info.nearby_help:
        pdf.rule(4)
        pdf.label("Nearest help")
        pdf.ln(1)
        for help_item in info.nearby_help:
            pdf.set_font("Helvetica", "B", 9)
            pdf.set_text_color(*INK)
            pdf.set_x(pdf.l_margin)
            pdf.cell(pdf.content_width, 5, _latin(help_item.label),
                     new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", size=7.5)
            pdf.set_text_color(*MUTED)
            pdf.flow(help_item.maps_url, height=3.8)
            pdf.ln(1)

    # --- phrases ----------------------------------------------------------
    pdf.add_page()
    pdf.heading(f"{info.language} when you need it", 17)
    pdf.ln(1)
    for phrase in info.phrases:
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(*INK)
        pdf.flow(phrase.local, height=5.5)
        pdf.set_font("Helvetica", size=9)
        pdf.set_text_color(*MUTED)
        pdf.flow(f"{phrase.english}  ·  {phrase.pronunciation}", height=4.4)
        pdf.ln(1.5)

    pdf.rule(3)
    pdf.body(f"Plugs: {info.plug_type}", colour=MUTED)
    pdf.body(f"Tipping: {info.tipping}", colour=MUTED)

    # --- packing ----------------------------------------------------------
    outstanding = [i for i in trip.packing_list if not i.packed]
    if outstanding:
        pdf.add_page()
        pdf.heading("Still to pack", 17)
        pdf.body(f"{len(outstanding)} of {len(trip.packing_list)} outstanding", colour=MUTED)
        pdf.ln(2)
        for item in outstanding:
            pdf.set_font("Helvetica", size=10)
            pdf.set_text_color(*INK)
            pdf.set_x(pdf.l_margin)
            pdf.cell(6, 5.5, "[ ]")
            pdf.multi_cell(pdf.content_width - 6, 5.5, _latin(item.label))
            if item.reason:
                pdf.set_font("Helvetica", size=8)
                pdf.set_text_color(*MUTED)
                pdf.flow(item.reason, height=4, indent=6)
            pdf.ln(0.5)


def build(trip: Trip, info: LocalInfo) -> bytes:
    """Render the whole trip to a PDF."""
    pdf = ItineraryPDF(trip)
    pdf.set_title(_latin(trip.title or trip.preferences.destination))
    pdf.set_author("Nomad")
    pdf.set_creator("Nomad")

    _cover(pdf, trip, info)
    _days(pdf, trip)
    _reference(pdf, trip, info)

    return bytes(pdf.output())


def filename(trip: Trip) -> str:
    slug = places_svc.slugify(trip.preferences.destination) or "trip"
    return f"nomad-{slug}-{date.today():%Y%m%d}.pdf"
