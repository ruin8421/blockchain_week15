"""
Upbit MCP Server
=================
Upbit 공개 API를 MCP tool로 노출하는 서버.

제공 tool:
  1. get_markets        — 거래 가능한 마켓(종목) 목록 조회
  2. get_ticker         — 현재가(시세) 조회
  3. get_orderbook      — 호가창(주문장) 조회
  4. get_candles        — 분봉 캔들 데이터 조회
  5. get_recent_trades  — 최근 체결 내역 조회

모든 API는 인증 없이 사용 가능한 Upbit 공개 REST API를 사용합니다.
"""

import json
import sys
import traceback

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    print("ERROR: mcp 패키지를 찾을 수 없습니다. 설치하세요: pip install 'mcp[cli]'", file=sys.stderr)
    sys.exit(1)

try:
    import httpx
except ImportError:
    print("ERROR: httpx 패키지를 찾을 수 없습니다. 설치하세요: pip install httpx", file=sys.stderr)
    sys.exit(1)

# ── MCP 서버 인스턴스 생성 ──────────────────────────────────────
mcp = FastMCP("Upbit Crypto Data")

BASE_URL = "https://api.upbit.com/v1"
HEADERS = {"Accept": "application/json"}


# ── 유틸리티 ────────────────────────────────────────────────────
async def _fetch(path: str, params: dict | None = None) -> list | dict:
    """Upbit REST API 호출 헬퍼."""
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(f"{BASE_URL}{path}", headers=HEADERS, params=params)
        resp.raise_for_status()
        return resp.json()


def _fmt_json(data) -> str:
    """JSON을 사람이 읽기 좋게 포맷."""
    return json.dumps(data, indent=2, ensure_ascii=False)


# ── Tool 1: 마켓 목록 ──────────────────────────────────────────
@mcp.tool()
async def get_markets(quote_currency: str = "") -> str:
    """
    Upbit에서 거래 가능한 마켓(종목) 목록을 조회합니다.

    Args:
        quote_currency: 기준 통화 필터 (예: "KRW", "BTC", "USDT").
                        비워두면 전체 마켓을 반환합니다.
    Returns:
        마켓 코드, 한글명, 영문명 목록 (JSON)
    """
    data = await _fetch("/market/all", {"isDetails": "false"})
    if quote_currency:
        qc = quote_currency.upper()
        data = [m for m in data if m["market"].startswith(qc + "-")]
    results = [
        {
            "market": m["market"],
            "korean_name": m["korean_name"],
            "english_name": m["english_name"],
        }
        for m in data
    ]
    return _fmt_json(results)


# ── Tool 2: 현재가 조회 ────────────────────────────────────────
@mcp.tool()
async def get_ticker(markets: str) -> str:
    """
    지정한 마켓의 현재가(시세) 정보를 조회합니다.

    Args:
        markets: 조회할 마켓 코드 (쉼표 구분).
                 예: "KRW-BTC" 또는 "KRW-BTC,KRW-ETH,KRW-XRP"
    Returns:
        현재가, 전일 대비 변동, 거래량 등 시세 정보 (JSON)
    """
    data = await _fetch("/ticker", {"markets": markets.upper()})
    results = []
    for t in data:
        results.append(
            {
                "market": t["market"],
                "trade_price": t["trade_price"],
                "signed_change_rate": round(t["signed_change_rate"] * 100, 2),
                "signed_change_price": t["signed_change_price"],
                "acc_trade_price_24h": t["acc_trade_price_24h"],
                "acc_trade_volume_24h": t["acc_trade_volume_24h"],
                "high_price": t["high_price"],
                "low_price": t["low_price"],
                "prev_closing_price": t["prev_closing_price"],
                "change": t["change"],
            }
        )
    return _fmt_json(results)


# ── Tool 3: 호가창(주문장) 조회 ─────────────────────────────────
@mcp.tool()
async def get_orderbook(markets: str) -> str:
    """
    지정한 마켓의 호가창(주문장, Orderbook) 데이터를 조회합니다.

    Args:
        markets: 조회할 마켓 코드 (쉼표 구분).
                 예: "KRW-BTC" 또는 "KRW-BTC,KRW-ETH"
    Returns:
        매도/매수 호가 리스트와 총 잔량 (JSON)
    """
    data = await _fetch("/orderbook", {"markets": markets.upper()})
    results = []
    for ob in data:
        units = []
        for u in ob["orderbook_units"]:
            units.append(
                {
                    "ask_price": u["ask_price"],
                    "bid_price": u["bid_price"],
                    "ask_size": u["ask_size"],
                    "bid_size": u["bid_size"],
                }
            )
        results.append(
            {
                "market": ob["market"],
                "total_ask_size": ob["total_ask_size"],
                "total_bid_size": ob["total_bid_size"],
                "orderbook_units": units,
            }
        )
    return _fmt_json(results)


# ── Tool 4: 분봉 캔들 조회 ─────────────────────────────────────
@mcp.tool()
async def get_candles(market: str, unit: int = 5, count: int = 10) -> str:
    """
    분봉(캔들스틱) 데이터를 조회합니다.

    Args:
        market: 마켓 코드. 예: "KRW-BTC"
        unit: 분 단위 (1, 3, 5, 10, 15, 30, 60, 240). 기본값 5분.
        count: 가져올 캔들 수 (최대 200). 기본값 10.
    Returns:
        시가, 고가, 저가, 종가, 거래량이 포함된 캔들 리스트 (JSON)
    """
    allowed_units = [1, 3, 5, 10, 15, 30, 60, 240]
    if unit not in allowed_units:
        return f"Error: unit은 {allowed_units} 중 하나여야 합니다."
    if count > 200:
        count = 200

    data = await _fetch(
        f"/candles/minutes/{unit}",
        {"market": market.upper(), "count": count},
    )
    results = []
    for c in data:
        results.append(
            {
                "candle_date_time_kst": c["candle_date_time_kst"],
                "opening_price": c["opening_price"],
                "high_price": c["high_price"],
                "low_price": c["low_price"],
                "trade_price": c["trade_price"],
                "candle_acc_trade_volume": c["candle_acc_trade_volume"],
            }
        )
    return _fmt_json(results)


# ── Tool 5: 최근 체결 내역 조회 ─────────────────────────────────
@mcp.tool()
async def get_recent_trades(market: str, count: int = 10) -> str:
    """
    최근 체결(거래) 내역을 조회합니다.

    Args:
        market: 마켓 코드. 예: "KRW-BTC"
        count: 가져올 체결 수 (최대 100). 기본값 10.
    Returns:
        체결 시각, 가격, 수량, 매수/매도 구분 (JSON)
    """
    if count > 100:
        count = 100

    data = await _fetch(
        "/trades/ticks",
        {"market": market.upper(), "count": count},
    )
    results = []
    for t in data:
        results.append(
            {
                "trade_date_time_kst": f"{t['trade_date_utc']} {t['trade_time_utc']} UTC",
                "trade_price": t["trade_price"],
                "trade_volume": t["trade_volume"],
                "ask_bid": t["ask_bid"],
            }
        )
    return _fmt_json(results)


# ── 서버 실행 ───────────────────────────────────────────────────
if __name__ == "__main__":
    mcp.run(transport="stdio")
