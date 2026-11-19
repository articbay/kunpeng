from unittest.mock import AsyncMock

import pytest

from kunpeng.clients.ozon import (OzonChatClient, OzonPostingClient,
                                  OzonProductClient, OzonQuestionClient,
                                  OzonReportClient, OzonReturnClient,
                                  OzonReviewClient)


@pytest.mark.asyncio
async def test_product_category_tree_uses_read_only_dictionary_endpoint():
    client = OzonProductClient("client-id", "api-key")
    client._request = AsyncMock(return_value={"result": []})

    await client.get_description_category_tree()

    client._request.assert_awaited_once_with(
        "POST",
        "/v1/description-category/tree",
        json={"language": "DEFAULT"},
    )


@pytest.mark.asyncio
async def test_fbs_list_uses_v4_cursor_contract():
    client = OzonPostingClient("client-id", "api-key")
    client._request = AsyncMock(
        return_value={"postings": [], "cursor": "", "has_next": False}
    )

    await client.get_fbs_postings(
        since="2026-08-01T00:00:00Z",
        to="2026-08-02T00:00:00Z",
        status="delivered",
        limit=100,
        cursor="next-page",
    )

    client._request.assert_awaited_once()
    method, path = client._request.await_args.args
    payload = client._request.await_args.kwargs["json"]
    assert (method, path) == ("POST", "/v4/posting/fbs/list")
    assert payload["filter"] == {
        "since": "2026-08-01T00:00:00Z",
        "to": "2026-08-02T00:00:00Z",
        "statuses": ["delivered"],
    }
    assert payload["cursor"] == "next-page"
    assert payload["sort_dir"] == "ASC"
    assert payload["with"] == {
        "analytics_data": True,
        "barcodes": True,
        "financial_data": True,
        "legal_info": True,
        "translit": False,
    }
    assert "offset" not in payload
    assert "dir" not in payload


@pytest.mark.asyncio
async def test_fbo_list_uses_v3_cursor_contract():
    client = OzonPostingClient("client-id", "api-key")
    client._request = AsyncMock(
        return_value={"postings": [], "cursor": "", "has_next": False}
    )

    await client.get_fbo_postings(
        since="2026-08-01T00:00:00Z",
        to="2026-08-02T00:00:00Z",
        status="delivered",
        limit=100,
        cursor="next-page",
    )

    client._request.assert_awaited_once()
    method, path = client._request.await_args.args
    payload = client._request.await_args.kwargs["json"]
    assert (method, path) == ("POST", "/v3/posting/fbo/list")
    assert payload["filter"] == {
        "since": "2026-08-01T00:00:00Z",
        "to": "2026-08-02T00:00:00Z",
        "statuses": ["delivered"],
    }
    assert payload["cursor"] == "next-page"
    assert payload["sort_dir"] == "ASC"
    assert payload["with"]["legal_info"] is True
    assert "offset" not in payload
    assert "dir" not in payload


@pytest.mark.asyncio
async def test_postings_report_uses_current_processed_at_contract():
    client = OzonReportClient("client-id", "api-key")
    client._request = AsyncMock(return_value={"result": {"code": "report-code"}})

    await client.create_postings_report(
        processed_at_from="2026-08-01T00:00:00Z",
        processed_at_to="2026-08-01T23:59:59Z",
        fulfillment_type="FBS",
    )

    client._request.assert_awaited_once_with(
        "POST",
        "/v1/report/postings/create",
        json={
            "filter": {
                "processed_at_from": "2026-08-01T00:00:00Z",
                "processed_at_to": "2026-08-01T23:59:59Z",
                "delivery_schema": ["fbs"],
            },
            "language": "RU",
        },
    )


@pytest.mark.asyncio
async def test_postings_report_rejects_unknown_fulfillment_type():
    client = OzonReportClient("client-id", "api-key")
    client._request = AsyncMock()

    with pytest.raises(ValueError, match="FBS or FBO"):
        await client.create_postings_report(
            processed_at_from="2026-08-01T00:00:00Z",
            processed_at_to="2026-08-01T23:59:59Z",
            fulfillment_type="FBP",
        )

    client._request.assert_not_awaited()


@pytest.mark.asyncio
async def test_return_list_supports_visual_status_change_filter():
    client = OzonReturnClient("client-id", "api-key")
    client._request = AsyncMock(return_value={"returns": [], "has_next": False})

    await client.get_returns_list(
        "2026-08-01T00:00:00Z",
        "2026-08-01T23:59:59Z",
        last_id=123,
        time_filter="visual_status_change_moment",
    )

    payload = client._request.await_args.kwargs["json"]
    assert payload["filter"] == {
        "visual_status_change_moment": {
            "time_from": "2026-08-01T00:00:00Z",
            "time_to": "2026-08-01T23:59:59Z",
        }
    }
    assert payload["last_id"] == 123


@pytest.mark.asyncio
async def test_customer_voice_clients_only_call_read_endpoints():
    review = OzonReviewClient("client-id", "api-key")
    question = OzonQuestionClient("client-id", "api-key")
    chat = OzonChatClient("client-id", "api-key")
    review._request = AsyncMock(return_value={})
    question._request = AsyncMock(return_value={})
    chat._request = AsyncMock(return_value={})

    await review.get_review_info("10")
    await review.get_review_comments("10", limit=50, offset=100)
    await question.get_question_list(limit=20, last_id="cursor-1")
    await question.get_question_answers("20", limit=30, last_id="cursor-2")
    await chat.get_chat_list(limit=40, cursor="cursor-3")
    await chat.get_chat_history("30", limit=50, from_message_id="40")

    assert [call.args[1] for call in review._request.await_args_list] == [
        "/v1/review/info",
        "/v1/review/comment/list",
    ]
    assert [call.args[1] for call in question._request.await_args_list] == [
        "/v1/question/list",
        "/v1/question/answer/list",
    ]
    assert [call.args[1] for call in chat._request.await_args_list] == [
        "/v3/chat/list",
        "/v3/chat/history",
    ]


@pytest.mark.asyncio
async def test_return_list_rejects_unknown_time_filter_before_request():
    client = OzonReturnClient("client-id", "api-key")
    client._request = AsyncMock(return_value={})

    with pytest.raises(ValueError, match="Unsupported Ozon return time filter"):
        await client.get_returns_list(
            "2026-08-01T00:00:00Z",
            "2026-08-01T23:59:59Z",
            time_filter="unknown",
        )

    client._request.assert_not_awaited()
