#!/bin/bash
# Upbit MCP 클라이언트 실행 스크립트
# client.py가 내부적으로 server.py를 subprocess로 실행합니다.

cd "$(dirname "$0")"
echo "🚀 Upbit MCP 클라이언트를 시작합니다..."
uv run python client.py
