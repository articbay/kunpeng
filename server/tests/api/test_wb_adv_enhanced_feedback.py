from kunpeng.api.v1.wildberries import _build_adv_enhanced_response


def test_enhanced_sync_response_keeps_all_child_results():
    response = _build_adv_enhanced_response(
        {
            "status": "partial_success",
            "results": {
                "norm_query_bids": {
                    "status": "success",
                    "message": "同步完成",
                    "api_count": 25,
                    "count": 25,
                },
                "norm_query_stats": {
                    "status": "error",
                    "message": "WB接口调用失败",
                    "api_count": 0,
                    "count": 0,
                },
            },
        }
    )

    assert response.status == "partial_success"
    assert response.message == "增强广告数据部分完成：1项成功，1项失败"
    assert response.synced_count == {"norm_query_bids": 25}
    assert response.results["norm_query_stats"]["message"] == "WB接口调用失败"


def test_enhanced_sync_response_accepts_legitimate_empty_result():
    response = _build_adv_enhanced_response(
        {
            "status": "success",
            "results": {
                "norm_query_list": {
                    "status": "success",
                    "message": "WB接口正常返回空数据",
                    "api_count": 0,
                    "count": 0,
                }
            },
        }
    )

    assert response.status == "success"
    assert response.synced_count == {"norm_query_list": 0}
    assert response.results["norm_query_list"]["status"] == "success"


def test_enhanced_sync_response_flags_api_data_without_stored_rows():
    response = _build_adv_enhanced_response(
        {
            "status": "success",
            "results": {
                "norm_query_bids": {
                    "status": "success",
                    "message": "同步完成",
                    "api_count": 25,
                    "count": 0,
                }
            },
        }
    )

    assert response.status == "error"
    assert response.synced_count == {}
    assert response.results["norm_query_bids"]["status"] == "error"
    assert (
        response.results["norm_query_bids"]["message"]
        == "WB接口返回了 25 条数据，但没有数据成功入库"
    )


def test_enhanced_sync_response_preserves_parent_error_without_child_results():
    response = _build_adv_enhanced_response(
        {"status": "error", "message": "增强广告同步初始化失败", "results": {}}
    )

    assert response.status == "error"
    assert response.message == "增强广告同步初始化失败"
    assert response.results == {}
