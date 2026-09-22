"""test_mcp_server.py -- MCP 프로토콜 레벨 단위 테스트.

LLM 호출 없이 handle_request 의 라우팅(initialize/ping/tools/list/tools/call,
알 수 없는 메서드/도구, 알림)만 검증한다. LLM 도구 핸들러는 monkeypatch 로 대체한다.
"""

import documentation_agent.mcp_server as server


def test_initialize_returns_server_info():
    resp = server.handle_request({
        "jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {"protocolVersion": "2025-06-18"},
    })
    assert resp["id"] == 1
    info = resp["result"]["serverInfo"]
    assert info["name"] == "coopagent"
    assert info["version"] == "0.1.0"


def test_ping_returns_empty_result():
    resp = server.handle_request({"jsonrpc": "2.0", "id": 2, "method": "ping"})
    assert resp["result"] == {}


def test_tools_list_returns_four_tools():
    resp = server.handle_request({"jsonrpc": "2.0", "id": 3, "method": "tools/list"})
    names = {t["name"] for t in resp["result"]["tools"]}
    assert names == {
        "generate_requirements",
        "propose_rag_contracts",
        "list_generated_proposals",
        "get_proposal_contracts",
    }


def test_tools_call_routes_to_handler(monkeypatch):
    def fake_handler(args):
        return server.text_content("FAKE")

    monkeypatch.setitem(server.TOOL_HANDLERS, "list_generated_proposals", fake_handler)
    resp = server.handle_request({
        "jsonrpc": "2.0", "id": 4, "method": "tools/call",
        "params": {"name": "list_generated_proposals", "arguments": {}},
    })
    assert resp["result"]["content"][0]["text"] == "FAKE"


def test_tools_call_unknown_tool_returns_error():
    resp = server.handle_request({
        "jsonrpc": "2.0", "id": 5, "method": "tools/call",
        "params": {"name": "nope", "arguments": {}},
    })
    assert resp["error"]["code"] == -32602


def test_unknown_method_returns_error():
    resp = server.handle_request({"jsonrpc": "2.0", "id": 6, "method": "wat"})
    assert resp["error"]["code"] == -32601


def test_notification_returns_none():
    # id 가 없으면 알림(notification)이므로 응답을 돌려주지 않는다.
    assert server.handle_request({"jsonrpc": "2.0", "method": "ping"}) is None
