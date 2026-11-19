import importlib.util
import sys
from pathlib import Path

from kunpeng.models.ods.wildberries.product_search_text import ODSWBProductSearchText
from kunpeng.models.ods.wildberries.region_sale import ODSWBRegionSale
from kunpeng.models.ods.wildberries.search_traffic import ODSWBSearchTraffic
from kunpeng.models.ods.wildberries.seller_balance import ODSWBSellerBalance

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "migrate-kunpeng-test-wb-domain-tables.py"


def _load_script():
    spec = importlib.util.spec_from_file_location("wb_domain_table_copy", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_wb_domain_models_use_canonical_english_tables():
    assert ODSWBRegionSale.__tablename__ == "ods_wb_finance_region_sales"
    assert ODSWBSellerBalance.__tablename__ == "ods_wb_finance_seller_balance"
    assert ODSWBProductSearchText.__tablename__ == "ods_wb_traffic_product_search_texts"
    assert ODSWBSearchTraffic.__tablename__ == "ods_wb_traffic_search_traffic"


def test_test_database_copy_script_is_copy_only():
    module = _load_script()
    assert module.ALLOWED_DATABASE == "kunpeng_test"
    assert {item.target for item in module.TABLE_COPIES} == {
        "ods_wb_finance_region_sales",
        "ods_wb_finance_seller_balance",
        "ods_wb_traffic_product_search_texts",
        "ods_wb_traffic_search_traffic",
    }
    source = SCRIPT_PATH.read_text(encoding="utf-8").upper()
    assert "DROP TABLE" not in source
    assert "TRUNCATE TABLE" not in source
    assert "DELETE FROM" not in source
