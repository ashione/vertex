#!/usr/bin/env python3
"""Simple CLI to inspect OKX futures orders and trigger manual closes."""
import argparse
import json
from typing import Any, Dict, Iterable, List, Optional

from client import CryptoTradingClient

from config import CryptoTradingConfig


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inspect OKX futures orders and positions, optionally close an order's position",
    )
    parser.add_argument("--exchange", default="okx", help="Exchange alias, default: okx")
    parser.add_argument("--symbol", help="Instrument id, e.g. BTC-USDT-SWAP")

    parser.add_argument("--list", action="store_true", help="List futures orders instead of single lookup")
    parser.add_argument("--state", default="open", help="Order state for --list (default: open)")
    parser.add_argument("--limit", type=int, default=50, help="Maximum orders to return for --list")

    parser.add_argument("--show-positions", action="store_true", help="Display current futures positions")

    parser.add_argument("--order-id", help="OKX order id (ordId)")
    parser.add_argument("--client-order-id", help="Client order id (clOrdId)")

    parser.add_argument(
        "--close",
        action="store_true",
        help="Close the futures position after showing the order details",
    )
    parser.add_argument(
        "--position-side",
        choices=["long", "short"],
        help="Position side required when --close is passed",
    )
    parser.add_argument("--margin-mode", default="cross", help="OKX margin mode, defaults to cross")
    parser.add_argument("--size", type=float, help="Optional close size in contract units")
    parser.add_argument(
        "--currency",
        help="Optional currency when closing by coin value instead of contract size",
    )

    return parser.parse_args()


def pretty_print(title: str, payload: Dict[str, Any]) -> None:
    print(f"\n{title}")
    print("-" * len(title))
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def require_close_prerequisites(args: argparse.Namespace) -> Optional[str]:
    if not args.close:
        return None
    if not args.position_side:
        return "--position-side is required when --close is used"
    if not (args.order_id or args.client_order_id):
        return "--order-id or --client-order-id is required when --close is used"
    if not args.symbol:
        return "--symbol is required when --close is used"
    if args.list:
        return "--close cannot be combined with --list"
    return None


def confirm(prompt: str) -> bool:
    answer = input(f"{prompt} [y/N]: ").strip().lower()
    return answer in {"y", "yes"}


def ensure_action_requested(args: argparse.Namespace) -> Optional[str]:
    actions: Iterable[bool] = (
        args.list,
        args.show_positions,
        bool(args.order_id or args.client_order_id),
    )
    if not any(actions):
        return "Please specify --list, --show-positions, or an order identifier"
    return None


def build_order_lookup(order_resp: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    if "error" in order_resp:
        return {}

    orders = order_resp.get("data") or order_resp.get("orders") or []
    lookup: Dict[str, List[Dict[str, Any]]] = {}
    for order in orders:
        inst_id = order.get("instId") or order.get("symbol")
        if not inst_id:
            continue
        lookup.setdefault(inst_id, []).append(order)
    return lookup


def display_positions(
    resp: Dict[str, Any],
    symbol: Optional[str],
    order_lookup: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    order_error: Optional[Dict[str, Any]] = None,
) -> None:
    if "error" in resp:
        pretty_print("Positions Lookup Failed", resp)
        return

    positions = resp.get("data") or resp.get("positions") or []

    if symbol:
        positions = [pos for pos in positions if pos.get("symbol") == symbol or pos.get("instId") == symbol]

    enriched: List[Dict[str, Any]] = []
    for position in positions:
        inst_id = position.get("instId") or position.get("symbol")
        orders = order_lookup.get(inst_id, []) if order_lookup else []
        order_ids = [order.get("ordId") for order in orders if order.get("ordId")]
        client_ids = [order.get("clOrdId") for order in orders if order.get("clOrdId")]

        entry = dict(position)
        if order_ids:
            entry["orderIds"] = order_ids
        if client_ids:
            entry["clientOrderIds"] = client_ids

        enriched.append(entry)

    payload: Dict[str, Any] = {"count": len(enriched), "positions": enriched}
    if order_error:
        payload["order_lookup_error"] = order_error

    title = "Positions" if enriched else "No Positions Found"
    pretty_print(title, payload)


def main() -> None:
    args = parse_args()
    error = require_close_prerequisites(args)
    if error:
        raise SystemExit(error)

    error = ensure_action_requested(args)
    if error:
        raise SystemExit(error)

    config = CryptoTradingConfig()
    client = CryptoTradingClient(config)

    if args.exchange not in client.get_available_exchanges():
        raise SystemExit(f"Exchange '{args.exchange}' is not configured")

    print("🔍 Futures Order Inspection")
    print("=" * 30)

    if args.list:
        order_list = client.list_futures_orders(
            exchange=args.exchange,
            symbol=args.symbol,
            state=args.state,
            limit=args.limit,
        )

        if "error" in order_list:
            pretty_print("Order List Failed", order_list)
        else:
            pretty_print("Order List", order_list)

    orders_lookup: Optional[Dict[str, List[Dict[str, Any]]]] = None
    order_lookup_error: Optional[Dict[str, Any]] = None

    if args.show_positions:
        positions_resp = client.get_futures_positions(args.exchange)

        orders_for_positions = client.list_futures_orders(
            exchange=args.exchange,
            symbol=args.symbol,
            state="open",
            limit=args.limit,
        )

        if "error" in orders_for_positions:
            order_lookup_error = orders_for_positions
            orders_lookup = {}
        else:
            orders_lookup = build_order_lookup(orders_for_positions)

        display_positions(positions_resp, args.symbol, orders_lookup, order_lookup_error)

    if not (args.order_id or args.client_order_id):
        return

    if not args.symbol:
        raise SystemExit("--symbol is required when referencing a specific order")

    order_resp = client.get_futures_order(
        args.exchange,
        args.symbol,
        order_id=args.order_id,
        client_order_id=args.client_order_id,
    )

    if "error" in order_resp:
        pretty_print("Order Lookup Failed", order_resp)
        return

    pretty_print("Order Details", order_resp)

    if not args.close:
        return

    print("\n⚠️ About to close position using the parameters below:")
    close_preview = {
        "exchange": args.exchange,
        "symbol": args.symbol,
        "position_side": args.position_side,
        "margin_mode": args.margin_mode,
        "size": args.size,
        "currency": args.currency,
    }
    pretty_print("Close Preview", close_preview)

    if not confirm("Proceed with close-position request?"):
        print("Close operation cancelled by user.")
        return

    close_resp = client.close_futures_position(
        exchange=args.exchange,
        symbol=args.symbol,
        position_side=args.position_side,
        margin_mode=args.margin_mode,
        size=args.size,
        currency=args.currency,
    )

    if "error" in close_resp:
        pretty_print("Close Failed", close_resp)
    else:
        pretty_print("Close Result", close_resp)


if __name__ == "__main__":
    main()
