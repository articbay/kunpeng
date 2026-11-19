from kunpeng.utils.barcodes import split_wb_barcodes


def test_split_wb_barcodes_separates_original_and_manual_values():
    assert split_wb_barcodes(["2044420598851", "TG-HC02904"]) == (
        "2044420598851",
        "TG-HC02904",
    )


def test_split_wb_barcodes_supports_single_manual_value():
    assert split_wb_barcodes("TG-BM008-001") == (None, "TG-BM008-001")


def test_split_wb_barcodes_ignores_empty_and_unclassified_values():
    assert split_wb_barcodes([None, "", "12345", "2048390807241"]) == (
        "2048390807241",
        None,
    )


def test_split_wb_barcodes_uses_first_value_of_each_kind():
    assert split_wb_barcodes(
        ["2044420598851", "2050687380351", "TG-HC02904", "TG-HC02906"]
    ) == ("2044420598851", "TG-HC02904")
