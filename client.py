"""
Upbit MCP Client
=================
MCP 서버에 stdio로 연결하여 Upbit 데이터를 조회하는 대화형 클라이언트.

흐름:
  1. server.py를 subprocess로 실행하고 stdio 연결
  2. list_tools()로 사용 가능한 tool 목록 조회
  3. 사용자 입력에 따라 call_tool()로 서버에 요청
  4. 결과 출력
"""

import asyncio
import json
import os
import sys
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


# ── 메뉴 정의 ──────────────────────────────────────────────────
MENU = """
========================================
     Upbit MCP Client - 메인 메뉴
========================================
  1. 마켓(종목) 목록 조회
  2. 현재가(시세) 조회
  3. 호가창(주문장) 조회
  4. 분봉 캔들 데이터 조회
  5. 최근 체결 내역 조회
  6. 사용 가능한 tool 목록 보기
  0. 종료
========================================
"""


class UpbitMCPClient:
    """MCP 클라이언트: 서버 연결 -> tool 조회 -> tool 호출."""

    def __init__(self):
        self.session: ClientSession | None = None
        self.exit_stack = AsyncExitStack()

    async def connect(self):
        """MCP 서버를 subprocess로 실행하고 stdio 연결."""
        # server.py의 절대 경로를 구한다
        script_dir = os.path.dirname(os.path.abspath(__file__))
        server_path = os.path.join(script_dir, "server.py")

        print(f"[INFO] 서버 경로: {server_path}")
        print(f"[INFO] Python: {sys.executable}")

        params = StdioServerParameters(
            command=sys.executable,       # 현재 Python 인터프리터
            args=[server_path],
            env=None,
        )
        stdio_transport = await self.exit_stack.enter_async_context(
            stdio_client(params)
        )
        read_stream, write_stream = stdio_transport
        self.session = await self.exit_stack.enter_async_context(
            ClientSession(read_stream, write_stream)
        )
        await self.session.initialize()
        print("✅ MCP 서버에 연결되었습니다.\n")

    async def list_tools(self):
        """서버에 등록된 tool 목록 출력."""
        result = await self.session.list_tools()
        print("사용 가능한 Tool 목록:")
        print("-" * 50)
        for tool in result.tools:
            print(f"  - {tool.name}")
            if tool.description:
                first_line = tool.description.strip().split("\n")[0]
                print(f"    > {first_line}")
        print("-" * 50)
        return result.tools

    async def call_tool(self, name: str, arguments: dict) -> str:
        """tool 이름과 인자로 서버에 요청."""
        result = await self.session.call_tool(name, arguments)
        texts = [block.text for block in result.content if hasattr(block, "text")]
        return "\n".join(texts)

    async def close(self):
        await self.exit_stack.aclose()


# ── 대화형 루프 ────────────────────────────────────────────────
async def interactive_loop(client: UpbitMCPClient):
    """사용자 입력을 받아 적절한 tool을 호출."""
    while True:
        print(MENU)
        choice = input("선택 > ").strip()

        if choice == "0":
            print("종료합니다.")
            break

        elif choice == "1":
            qc = input("기준 통화 필터 (KRW/BTC/USDT, 전체는 Enter): ").strip()
            result = await client.call_tool("get_markets", {"quote_currency": qc})
            data = json.loads(result)
            print(f"\n마켓 목록 ({len(data)}개):")
            for m in data[:30]:
                print(f"  {m['market']:12s}  {m['korean_name']}  ({m['english_name']})")
            if len(data) > 30:
                print(f"  ... 외 {len(data) - 30}개")

        elif choice == "2":
            markets = input("마켓 코드 (예: KRW-BTC,KRW-ETH): ").strip()
            if not markets:
                markets = "KRW-BTC"
            result = await client.call_tool("get_ticker", {"markets": markets})
            data = json.loads(result)
            print("\n현재가 정보:")
            for t in data:
                change_mark = "▲" if t["change"] == "RISE" else "▼" if t["change"] == "FALL" else "-"
                print(f"  {change_mark} {t['market']}")
                print(f"     현재가: {t['trade_price']:,.0f}")
                print(f"     변동률: {t['signed_change_rate']:+.2f}%")
                print(f"     고가/저가: {t['high_price']:,.0f} / {t['low_price']:,.0f}")
                print(f"     24h 거래대금: {t['acc_trade_price_24h']:,.0f}")
                print()

        elif choice == "3":
            markets = input("마켓 코드 (예: KRW-BTC): ").strip()
            if not markets:
                markets = "KRW-BTC"
            result = await client.call_tool("get_orderbook", {"markets": markets})
            data = json.loads(result)
            for ob in data:
                print(f"\n호가창: {ob['market']}")
                print(f"  매도 총 잔량: {ob['total_ask_size']:.4f}")
                print(f"  매수 총 잔량: {ob['total_bid_size']:.4f}")
                print(f"  {'매도호가':>14s}  {'매도잔량':>12s}  |  {'매수호가':<14s}  {'매수잔량':<12s}")
                print("  " + "-" * 64)
                for u in ob["orderbook_units"][:10]:
                    print(
                        f"  {u['ask_price']:>14,.0f}  {u['ask_size']:>12.4f}  |  "
                        f"{u['bid_price']:<14,.0f}  {u['bid_size']:<12.4f}"
                    )

        elif choice == "4":
            market = input("마켓 코드 (예: KRW-BTC): ").strip() or "KRW-BTC"
            unit_str = input("분 단위 (1/3/5/10/15/30/60/240, 기본 5): ").strip() or "5"
            count_str = input("캔들 수 (기본 10, 최대 200): ").strip() or "10"
            result = await client.call_tool(
                "get_candles",
                {"market": market, "unit": int(unit_str), "count": int(count_str)},
            )
            data = json.loads(result)
            print(f"\n{market} {unit_str}분봉 (최근 {len(data)}개):")
            print(f"  {'시각':>20s}  {'시가':>12s}  {'고가':>12s}  {'저가':>12s}  {'종가':>12s}  {'거래량':>10s}")
            for c in data:
                time_short = c["candle_date_time_kst"][5:16]
                print(
                    f"  {time_short:>20s}  {c['opening_price']:>12,.0f}  "
                    f"{c['high_price']:>12,.0f}  {c['low_price']:>12,.0f}  "
                    f"{c['trade_price']:>12,.0f}  {c['candle_acc_trade_volume']:>10.4f}"
                )

        elif choice == "5":
            market = input("마켓 코드 (예: KRW-BTC): ").strip() or "KRW-BTC"
            count_str = input("체결 수 (기본 10, 최대 100): ").strip() or "10"
            result = await client.call_tool(
                "get_recent_trades",
                {"market": market, "count": int(count_str)},
            )
            data = json.loads(result)
            print(f"\n{market} 최근 체결 ({len(data)}건):")
            for t in data:
                side = "매수" if t["ask_bid"] == "BID" else "매도"
                print(f"  [{side}] 가격: {t['trade_price']:>12,.0f}  수량: {t['trade_volume']:.6f}")

        elif choice == "6":
            await client.list_tools()

        else:
            print("잘못된 입력입니다. 0~6 사이의 번호를 선택하세요.")


# ── 메인 진입점 ────────────────────────────────────────────────
async def main():
    client = UpbitMCPClient()
    try:
        await client.connect()
        await client.list_tools()
        await interactive_loop(client)
    except Exception as e:
        print(f"\n[ERROR] {e}")
        print("\n서버 단독 테스트를 먼저 해보세요:")
        print("  python server.py")
        print("\n위 명령에서 에러가 나면 의존성 설치가 필요합니다:")
        print("  pip install \"mcp[cli]\" httpx")
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
