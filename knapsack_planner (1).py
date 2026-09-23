#!/usr/bin/env python3
"""
Smart Knapsack Shopping Planner
===============================

A greedy 0/1 knapsack over shopping products.

Every product has a name, price, weight and value. Given a budget and a weight
limit, the planner ranks products by an efficiency metric (value per kg, or
value per rupee), then walks that ranking from the top, taking each item only if
it still fits inside BOTH constraints. Items that would overflow are skipped
(not stopped at) so a cheap/light item later in the list still gets a chance.

Run it:
    python3 knapsack_planner.py                     # demo with sample products
    python3 knapsack_planner.py --budget 3000 --weight 5
    python3 knapsack_planner.py --metric price      # value per rupee instead
    python3 knapsack_planner.py --interactive       # type your own products

Standard library only.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# 1. Data structure
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Product:
    """One thing you might buy."""

    name: str
    price: float  # what it costs
    weight: float  # what it weighs, in kg
    value: float  # how much you care about it

    def efficiency(self, metric: str) -> float:
        """Bang-for-buck score. Higher = pick sooner."""
        if metric == "price":
            return self.value / self.price if self.price > 0 else float("inf")
        return self.value / self.weight if self.weight > 0 else float("inf")

    def is_usable(self) -> bool:
        return self.price > 0 and self.weight > 0 and self.value > 0


@dataclass
class Plan:
    """The outcome of one greedy run."""

    selected: list[Product] = field(default_factory=list)
    skipped: list[Product] = field(default_factory=list)
    spent: float = 0.0
    weight_used: float = 0.0
    value_total: float = 0.0
    budget: float = 0.0
    weight_limit: float = 0.0
    note: str = ""

    @property
    def budget_left(self) -> float:
        return max(self.budget - self.spent, 0.0)

    @property
    def weight_left(self) -> float:
        return max(self.weight_limit - self.weight_used, 0.0)


# ---------------------------------------------------------------------------
# 2. The greedy algorithm
# ---------------------------------------------------------------------------


def greedy_knapsack(
    products: list[Product],
    budget: float,
    weight_limit: float,
    metric: str = "weight",
) -> Plan:
    """Pick items in descending efficiency order until a limit runs out.

    O(n log n) for the sort, O(n) for the scan.
    """
    plan = Plan(budget=budget, weight_limit=weight_limit)

    # --- edge cases ---------------------------------------------------------
    if budget <= 0 or weight_limit <= 0:
        plan.note = (
            f"budget is {budget:g}, so nothing can be bought"
            if budget <= 0
            else f"weight limit is {weight_limit:g} kg, so nothing can be carried"
        )
        plan.skipped = list(products)
        return plan

    usable = [p for p in products if p.is_usable()]
    if len(usable) != len(products):
        plan.note = f"ignored {len(products) - len(usable)} product(s) with a non-positive price, weight or value"

    if not usable:
        plan.note = plan.note or "no products to choose from"
        return plan

    # --- sort by efficiency, best first (ties broken by name for stability) --
    ranked = sorted(usable, key=lambda p: (-p.efficiency(metric), p.name))

    # --- greedy scan: take it if it fits, otherwise skip and keep going ------
    for product in ranked:
        if plan.spent + product.price > budget:
            plan.skipped.append(product)  # would blow the budget
            continue
        if plan.weight_used + product.weight > weight_limit:
            plan.skipped.append(product)  # would blow the weight limit
            continue

        plan.selected.append(product)
        plan.spent += product.price
        plan.weight_used += product.weight
        plan.value_total += product.value

    if not plan.selected:
        plan.note = "nothing fits — every single item is heavier or pricier than the limits allow"

    return plan


# ---------------------------------------------------------------------------
# 3. Output: product cards + dashboard
# ---------------------------------------------------------------------------

CARD_W = 50
DASH_W = 50
BAR_W = 24
CURRENCY = "₹"


def _rule(char: str) -> str:
    return char * CARD_W


def _money(amount: float) -> str:
    return f"{CURRENCY}{amount:,.2f}"


def _kg(amount: float) -> str:
    return f"{amount:,.2f} kg"


def _row(text: str = "", inner: int = DASH_W - 4) -> str:
    """One padded line inside the dashboard box."""
    return f"│  {text:<{inner}}  │"


def _card(content: str) -> str:
    """One padded line inside a product card."""
    return f"│{content:<{CARD_W}}│"


def _kv(label: str, number: str, unit: str = "") -> str:
    """A label / right-aligned number / unit row for the dashboard."""
    return f"{label:<17}{number:>13} {unit:<4}"


def render_card(product: Product, index: int, metric: str) -> list[str]:
    """A formatted text block describing one selected product."""
    unit = "/₹" if metric == "price" else "/kg"
    ratio = product.efficiency(metric)

    room = CARD_W - 7  # room for the "  1. " prefix and one trailing space
    name = product.name if len(product.name) <= room else product.name[: room - 1] + "…"

    return [
        f"┌{'─' * CARD_W}┐",
        _card(f" {index:>2}. {name}"),
        _card(""),
        _card(f"   price {_money(product.price):>12}   weight {_kg(product.weight):>10}"),
        _card(f"   value {product.value:>12,.2f}   ratio {ratio:>10,.1f} {unit}"),
        f"└{'─' * CARD_W}┘",
    ]


def print_cards(plan: Plan, metric: str) -> None:
    if not plan.selected:
        print("  (no products selected)\n")
        return
    for i, product in enumerate(plan.selected, start=1):
        for line in render_card(product, i, metric):
            print(line)
        print()


def _bar(fraction: float) -> str:
    fraction = min(max(fraction, 0.0), 1.0)
    filled = round(fraction * BAR_W)
    return "█" * filled + "░" * (BAR_W - filled)


def print_dashboard(plan: Plan) -> None:
    inner = DASH_W - 4
    top, mid, bot = f"╔{_rule('═')}╗", f"╠{_rule('═')}╣", f"╚{_rule('═')}╝"

    print(top)
    print(_row("SHOPPING DASHBOARD"))
    print(mid)
    print(_row(_kv("Total value", f"{plan.value_total:,.2f}")))
    print(_row(_kv("Total weight", f"{plan.weight_used:,.2f}", "kg")))
    print(_row(_kv("Total cost", _money(plan.spent))))
    print(_row(_kv("Budget remaining", _money(plan.budget_left))))
    print(_row(_kv("Weight remaining", f"{plan.weight_left:,.2f}", "kg")))
    print(_row())
    print(_row(_kv("Selected", f"{len(plan.selected)} of {len(plan.selected) + len(plan.skipped)}")))
    print(_row(_kv("Skipped", str(len(plan.skipped)))))
    print(_row())

    if plan.budget > 0:
        pct = plan.spent / plan.budget
        print(_row(f"Budget used  {_bar(pct)}  {pct * 100:5.1f}%"))
    if plan.weight_limit > 0:
        pct = plan.weight_used / plan.weight_limit
        print(_row(f"Weight used  {_bar(pct)}  {pct * 100:5.1f}%"))
    if plan.note:
        note = f"note: {plan.note}"
        if len(note) > inner:
            note = note[: inner - 1] + "…"
        print(_row())
        print(_row(note))
    print(bot)


# ---------------------------------------------------------------------------
# 4. Input: sample data, CLI params, or interactive entry
# ---------------------------------------------------------------------------

SAMPLE_PRODUCTS = [
    Product("Titanium travel mug", 1200, 0.45, 1800),
    Product("Power bank 20000mAh", 2400, 0.60, 3200),
    Product("Instant coffee 500g", 780, 0.50, 1150),
    Product("Mercury-free thermometer", 350, 0.08, 600),
    Product("Wool blend blanket", 1900, 1.80, 2400),
    Product("Solar lantern", 950, 0.35, 1400),
    Product("Cast iron tawa", 1450, 2.40, 1600),
    Product("Steel water bottle 1L", 620, 0.40, 1000),
    Product("Cotton duffel bag", 1100, 0.90, 1500),
    Product("Paperback atlas", 480, 0.75, 700),
    Product("Espresso machine", 8900, 4.20, 9500),
    Product("Folding camp stool", 1350, 1.60, 1750),
]


def read_interactive() -> tuple[list[Product], float, float]:
    """Ask the user for limits and products. Blank name ends entry."""
    try:
        budget = float(input("Budget limit: ").strip() or "0")
        weight_limit = float(input("Weight limit (kg): ").strip() or "0")
        print("Enter products (blank name to finish):\n")

        products: list[Product] = []
        while True:
            name = input(f"  #{len(products) + 1} name: ").strip()
            if not name:
                break
            price = float(input("      price: ").strip() or "0")
            weight = float(input("      weight (kg): ").strip() or "0")
            value = float(input("      value: ").strip() or "0")
            products.append(Product(name, price, weight, value))
            print()
    except (EOFError, KeyboardInterrupt):
        print("\nStopped.")
        sys.exit(1)
    except ValueError as exc:
        sys.exit(f"Please enter numbers for price, weight and value ({exc}).")

    return products, budget, weight_limit


# ---------------------------------------------------------------------------
# 5. CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    global CURRENCY

    parser = argparse.ArgumentParser(
        description="Greedy knapsack shopping planner: best products within a budget and a weight limit.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--budget", type=float, default=5000, help="maximum total price")
    parser.add_argument("--weight", type=float, default=5.0, help="maximum total weight in kg")
    parser.add_argument(
        "--metric",
        choices=("weight", "price"),
        default="weight",
        help="efficiency metric: value per kg, or value per rupee",
    )
    parser.add_argument("--currency", default="₹", help="symbol used when printing prices")
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="type your own products instead of using the sample list",
    )
    args = parser.parse_args(argv)

    CURRENCY = args.currency

    products, budget, weight_limit = (
        read_interactive() if args.interactive else (list(SAMPLE_PRODUCTS), args.budget, args.weight)
    )

    plan = greedy_knapsack(products, budget, weight_limit, metric=args.metric)

    print(f"\n{'=' * (CARD_W + 2)}")
    print(f" SMART KNAPSACK SHOPPING PLANNER".ljust(CARD_W + 2))
    print(f" budget {_money(budget)}   weight limit {_kg(weight_limit)}   "
          f"ranking by value {'per ₹' if args.metric == 'price' else 'per kg'}")
    print(f"{'=' * (CARD_W + 2)}\n")

    print(" SELECTED PRODUCT CARDS\n")
    print_cards(plan, args.metric)

    print_dashboard(plan)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
