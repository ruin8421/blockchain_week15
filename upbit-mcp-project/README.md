# Upbit MCP — 암호화폐 데이터 조회 시스템

Upbit 거래소의 공개 API를 **MCP(Model Context Protocol) 서버/클라이언트 구조**로 감싸서,
코인 가격·호가창·캔들·체결 데이터를 조회할 수 있는 프로그램입니다.

## 프로젝트 개요

| 구분 | 설명 |
|------|------|
| **MCP Server** | Upbit REST API를 5개의 tool로 노출 (`server.py`) |
| **MCP Client** | 서버에 stdio로 연결하여 대화형으로 데이터 조회 (`client.py`) |
| **통신 방식** | stdio (표준 입출력) — 별도 포트 불필요 |
| **외부 API** | Upbit 공개 API (`api.upbit.com/v1`) — 인증 불필요 |

## 아키텍처

```text
┌──────────────────┐
│   MCP Client     │  사용자 입력 → 메뉴 선택
│   (client.py)    │
└────────┬─────────┘
         │  list_tools() / call_tool()
         │  (stdio 통신)
┌────────▼─────────┐
│   MCP Server     │  tool 함수 실행
│   (server.py)    │
└────────┬─────────┘
         │  HTTP GET 요청
         ▼
┌──────────────────┐
│  Upbit REST API  │  api.upbit.com/v1
│  (공개 엔드포인트) │
└──────────────────┘
```

### 호출 흐름 상세

1. 클라이언트가 `server.py`를 subprocess로 실행하고 stdio 연결
2. `list_tools()` → 서버가 등록한 5개 tool 목록 반환
3. 사용자가 메뉴를 선택하면 `call_tool(name, args)` 호출
4. 서버가 Upbit API에 HTTP 요청 → 응답을 가공하여 반환
5. 클라이언트가 결과를 포맷하여 터미널에 출력

## 제공 Tool 목록

| # | Tool 이름 | 설명 | 주요 파라미터 |
|---|-----------|------|--------------|
| 1 | `get_markets` | 거래 가능한 마켓(종목) 목록 | `quote_currency`: KRW, BTC, USDT 등 |
| 2 | `get_ticker` | 현재가·변동률·거래량 조회 | `markets`: "KRW-BTC,KRW-ETH" |
| 3 | `get_orderbook` | 호가창(주문장) 매도/매수 호가 | `markets`: "KRW-BTC" |
| 4 | `get_candles` | 분봉 캔들 (시가/고가/저가/종가) | `market`, `unit` (1~240분), `count` |
| 5 | `get_recent_trades` | 최근 체결 내역 | `market`, `count` (최대 100) |

## 사전 요구사항

- **Python 3.10 이상**
- **uv** (Python 패키지 매니저) — [설치 안내](https://docs.astral.sh/uv/getting-started/installation/)

```bash
# uv 설치 (macOS/Linux)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

## 빠른 시작

### 1. 프로젝트 준비

```bash
cd upbit-mcp-project
uv sync          # 의존성 설치 (mcp, httpx)
```

### 2. 클라이언트 실행 (권장)

```bash
uv run python client.py
```

클라이언트가 자동으로 서버를 subprocess로 실행하고 stdio로 연결합니다.
별도의 서버 실행은 필요 없습니다.

### 3. 셸 스크립트로 실행

```bash
chmod +x run_client.sh
./run_client.sh
```

### 4. 서버 단독 테스트 (개발/디버깅용)

```bash
# MCP Inspector로 tool 목록과 호출 테스트
uv run mcp dev server.py
```

## 사용 예시

### 실행 화면

```
✅ MCP 서버에 연결되었습니다.

📦 사용 가능한 Tool 목록:
--------------------------------------------------
  • get_markets
    └ Upbit에서 거래 가능한 마켓(종목) 목록을 조회합니다.
  • get_ticker
    └ 지정한 마켓의 현재가(시세) 정보를 조회합니다.
  • get_orderbook
    └ 지정한 마켓의 호가창(주문장, Orderbook) 데이터를 조회합니다.
  • get_candles
    └ 분봉(캔들스틱) 데이터를 조회합니다.
  • get_recent_trades
    └ 최근 체결(거래) 내역을 조회합니다.
--------------------------------------------------

╔══════════════════════════════════════════════════╗
║          Upbit MCP Client — 메인 메뉴            ║
╠══════════════════════════════════════════════════╣
║  1. 마켓(종목) 목록 조회                          ║
║  2. 현재가(시세) 조회                             ║
║  3. 호가창(주문장) 조회                           ║
║  4. 분봉 캔들 데이터 조회                         ║
║  5. 최근 체결 내역 조회                           ║
║  6. 사용 가능한 tool 목록 보기                    ║
║  0. 종료                                         ║
╚══════════════════════════════════════════════════╝

선택 ▶ 2
마켓 코드 (예: KRW-BTC,KRW-ETH): KRW-BTC,KRW-ETH

💰 현재가 정보:
  🟢 KRW-BTC
     현재가: 143,500,000
     변동률: +2.35%
     고가/저가: 144,000,000 / 140,200,000
     24h 거래대금: 285,432,100,000

  🔴 KRW-ETH
     현재가: 3,285,000
     변동률: -1.12%
     고가/저가: 3,350,000 / 3,250,000
     24h 거래대금: 98,120,500,000
```

### 호가창 조회 예시

```
선택 ▶ 3
마켓 코드 (예: KRW-BTC): KRW-BTC

📊 호가창: KRW-BTC
  매도 총 잔량: 5.2341
  매수 총 잔량: 8.1205
          매도호가      매도잔량  |  매수호가          매수잔량
  ----------------------------------------------------------------
   143,600,000        0.1200  |  143,500,000        0.3500
   143,700,000        0.0800  |  143,400,000        0.5100
   ...
```

## 폴더 구조

```text
upbit-mcp-project/
├── server.py           # MCP 서버 (Upbit API → 5개 tool)
├── client.py           # MCP 클라이언트 (대화형 CLI)
├── pyproject.toml      # 프로젝트 메타데이터 및 의존성
├── run_client.sh       # 클라이언트 실행 스크립트
├── run_all_demos.sh    # 전체 데모 실행 스크립트
└── README.md           # 이 문서
```

## 핵심 코드 설명

### server.py — MCP 서버

```python
from mcp.server.fastmcp import FastMCP
import httpx

mcp = FastMCP("Upbit Crypto Data")

@mcp.tool()
async def get_ticker(markets: str) -> str:
    """현재가 조회 tool"""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://api.upbit.com/v1/ticker",
            params={"markets": markets}
        )
        return json.dumps(resp.json(), indent=2)

mcp.run(transport="stdio")
```

- `FastMCP`로 서버 인스턴스 생성
- `@mcp.tool()` 데코레이터로 함수를 tool로 등록
- `httpx`로 Upbit API 비동기 호출
- `transport="stdio"`로 표준 입출력 통신

### client.py — MCP 클라이언트

```python
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# 서버를 subprocess로 실행
params = StdioServerParameters(
    command="python", args=["server.py"]
)
transport = stdio_client(params)
session = ClientSession(read_stream, write_stream)

# tool 목록 조회
tools = await session.list_tools()

# tool 호출
result = await session.call_tool("get_ticker", {"markets": "KRW-BTC"})
```

- `StdioServerParameters`로 서버 프로세스 설정
- `stdio_client()`로 연결
- `list_tools()`와 `call_tool()`로 서버와 통신

## Upbit API 참고

이 프로젝트에서 사용하는 Upbit 공개 API 엔드포인트:

| 엔드포인트 | 설명 |
|-----------|------|
| `GET /v1/market/all` | 거래 가능 마켓 목록 |
| `GET /v1/ticker?markets=` | 현재가 정보 |
| `GET /v1/orderbook?markets=` | 호가 정보 |
| `GET /v1/candles/minutes/{unit}?market=&count=` | 분봉 데이터 |
| `GET /v1/trades/ticks?market=&count=` | 최근 체결 내역 |

공식 문서: https://docs.upbit.com/reference

## MCP 개념 정리

| 용어 | 설명 |
|------|------|
| **MCP** | Model Context Protocol — AI 모델이 외부 tool을 호출하기 위한 표준 프로토콜 |
| **MCP Server** | tool을 정의하고 노출하는 서버 프로세스 |
| **MCP Client** | server에 연결하여 tool을 조회하고 호출하는 클라이언트 |
| **Tool** | 서버가 노출하는 하나의 기능 단위 (함수 + 스키마) |
| **stdio 통신** | 표준 입출력을 통한 프로세스 간 통신 방식 |
| **list_tools()** | 서버에 등록된 tool 목록을 조회하는 프로토콜 메서드 |
| **call_tool()** | 특정 tool을 이름과 인자로 호출하는 프로토콜 메서드 |

## 트러블슈팅

| 문제 | 해결 |
|------|------|
| `uv: command not found` | uv를 먼저 설치: `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| `ModuleNotFoundError: mcp` | `uv sync` 실행하여 의존성 설치 |
| 네트워크 오류 / Timeout | 인터넷 연결 확인, Upbit API 상태 확인 |
| `httpx.HTTPStatusError 429` | API 호출 빈도 제한 — 잠시 대기 후 재시도 |

## 라이선스

교육용 프로젝트입니다.
