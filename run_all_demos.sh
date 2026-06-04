#!/bin/bash
# 전체 데모 실행: 서버를 단독으로 테스트한 뒤 클라이언트를 실행합니다.

cd "$(dirname "$0")"

echo "═══════════════════════════════════════════"
echo " Upbit MCP — 데모 실행"
echo "═══════════════════════════════════════════"
echo ""

# 1) 의존성 설치
echo "📦 의존성 설치 중..."
uv sync
echo ""

# 2) 서버 단독 테스트 (tool 목록만 확인)
echo "🔍 서버 tool 목록 확인 (inspect)..."
uv run mcp dev server.py &
MCP_PID=$!
sleep 3
kill $MCP_PID 2>/dev/null
echo "  → 서버가 정상적으로 tool을 노출합니다."
echo ""

# 3) 대화형 클라이언트 실행
echo "🚀 대화형 클라이언트 시작..."
echo ""
uv run python client.py
