#!/usr/bin/env python3
"""T9 OS v2 — t9_seed MCP Server
t9_seed.py를 MCP 서버로 래핑하여 cc가 Bash 경유 없이 도구로 직접 호출.

Usage:
    .mcp.json에 등록:
    {
      "mcpServers": {
        "t9-seed": {
          "command": "python3",
          "args": ["T9OS/mcp/t9_seed_server.py"]
        }
      }
    }
"""

import json
import sys
import subprocess
import os

SEED_PATH = os.path.join(os.path.dirname(__file__), '..', 't9_seed.py')
PROJECT_DIR = os.path.join(os.path.dirname(__file__), '..', '..')

def run_seed(args: list[str]) -> str:
    """t9_seed.py를 서브프로세스로 실행."""
    try:
        result = subprocess.run(
            ['python3', SEED_PATH] + args,
            capture_output=True, text=True, timeout=30,
            cwd=PROJECT_DIR
        )
        output = result.stdout.strip()
        if result.returncode != 0 and result.stderr:
            output += f"\n[stderr] {result.stderr.strip()}"
        return output or "(no output)"
    except subprocess.TimeoutExpired:
        return "[error] timeout (30s)"
    except Exception as e:
        return f"[error] {e}"

# MCP 도구 정의
TOOLS = {
    "t9_capture": {
        "description": "전개체 저장. 한빈의 날것 입력을 T9 OS에 등록.",
        "inputSchema": {
            "type": "object",
            "properties": {"text": {"type": "string", "description": "저장할 텍스트"}},
            "required": ["text"]
        },
        "handler": lambda args: run_seed(["capture", args["text"]])
    },
    "t9_status": {
        "description": "T9 OS 전체 현황 조회.",
        "inputSchema": {"type": "object", "properties": {}},
        "handler": lambda args: run_seed(["status"])
    },
    "t9_daily": {
        "description": "일일 브리프 생성. 마감일, 긴급 사항, 프로젝트 상태.",
        "inputSchema": {"type": "object", "properties": {}},
        "handler": lambda args: run_seed(["daily"])
    },
    "t9_search": {
        "description": "자유 검색 (FTS). 엔티티, 메타데이터, 본문 전체 검색.",
        "inputSchema": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "검색 쿼리"}},
            "required": ["query"]
        },
        "handler": lambda args: run_seed(["search", args["query"]])
    },
    "t9_transition": {
        "description": "엔티티 상태 전이.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "id": {"type": "string", "description": "엔티티 ID"},
                "phase": {"type": "string", "description": "목표 상태"},
                "reason": {"type": "string", "description": "전이 사유", "default": ""}
            },
            "required": ["id", "phase"]
        },
        "handler": lambda args: run_seed(["transition", args["id"], args["phase"]] + ([args.get("reason")] if args.get("reason") else []))
    },
    "t9_relate": {
        "description": "두 엔티티 간 관계 생성.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "id1": {"type": "string", "description": "소스 엔티티 ID"},
                "id2": {"type": "string", "description": "타겟 엔티티 ID"}
            },
            "required": ["id1", "id2"]
        },
        "handler": lambda args: run_seed(["relate", args["id1"], args["id2"]])
    },
    "t9_reindex": {
        "description": "MD 파일 → DB 동기화.",
        "inputSchema": {"type": "object", "properties": {}},
        "handler": lambda args: run_seed(["reindex"])
    },
}

def handle_jsonrpc(request: dict) -> dict:
    """JSON-RPC 요청 처리."""
    method = request.get("method", "")
    params = request.get("params", {})
    req_id = request.get("id")

    if method == "initialize":
        return {
            "jsonrpc": "2.0", "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "t9-seed", "version": "0.1.0"}
            }
        }
    elif method == "notifications/initialized":
        return None  # no response needed
    elif method == "tools/list":
        tools_list = []
        for name, tool in TOOLS.items():
            tools_list.append({
                "name": name,
                "description": tool["description"],
                "inputSchema": tool["inputSchema"]
            })
        return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": tools_list}}
    elif method == "tools/call":
        tool_name = params.get("name", "")
        tool_args = params.get("arguments", {})
        if tool_name in TOOLS:
            result = TOOLS[tool_name]["handler"](tool_args)
            return {
                "jsonrpc": "2.0", "id": req_id,
                "result": {"content": [{"type": "text", "text": result}]}
            }
        else:
            return {
                "jsonrpc": "2.0", "id": req_id,
                "error": {"code": -32601, "message": f"Unknown tool: {tool_name}"}
            }
    elif method == "ping":
        return {"jsonrpc": "2.0", "id": req_id, "result": {}}
    else:
        return None  # ignore unknown methods

def main():
    """stdio JSON-RPC 서버 메인 루프."""
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
            response = handle_jsonrpc(request)
            if response:
                sys.stdout.write(json.dumps(response) + "\n")
                sys.stdout.flush()
        except json.JSONDecodeError:
            pass
        except Exception as e:
            err = {"jsonrpc": "2.0", "id": None, "error": {"code": -32603, "message": str(e)}}
            sys.stdout.write(json.dumps(err) + "\n")
            sys.stdout.flush()

if __name__ == "__main__":
    main()
