"""standardize wb barcode fields

Revision ID: 11f65441bb50
Revises: ce9fc5966dd6
Create Date: 2026-08-05 21:21:58.950382

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "11f65441bb50"
down_revision = "ce9fc5966dd6"
branch_labels = None
depends_on = None


ODS_SCALAR_COLUMNS = (
    ("ods_wb_supplier_sales", "barcode"),
    ("ods_wb_supplier_orders", "barcode"),
    ("ods_wb_sales_reports", "sku"),
    ("ods_wb_goods_returns", "barcode"),
)
ODS_ARRAY_COLUMNS = (
    ("ods_wb_marketplace_orders", "skus"),
    ("ods_wb_new_orders", "skus"),
)
DWD_OLD_COLUMNS = (
    ("dwd_wb_order_detail", "barcode"),
    ("dwd_wb_order_statistics_detail", "barcode"),
    ("dwd_wb_return_detail", "barcode"),
    ("dwd_wb_return_detail", "bar_code"),
)
ALL_TABLES = (
    "ods_wb_supplier_sales",
    "ods_wb_supplier_orders",
    "ods_wb_sales_reports",
    "ods_wb_goods_returns",
    "ods_wb_marketplace_orders",
    "ods_wb_new_orders",
    "dwd_wb_order_detail",
    "dwd_wb_order_statistics_detail",
    "dwd_wb_return_detail",
)


def _original_sql(expression: str) -> str:
    return f"TRIM({expression}) REGEXP '^[0-9]{{13}}$'"


def _manual_sql(expression: str) -> str:
    trimmed = f"TRIM({expression})"
    return (
        f"{trimmed} REGEXP '^[A-Za-z0-9_-]+$' "
        f"AND {trimmed} REGEXP '[A-Za-z]' "
        f"AND {trimmed} REGEXP '[0-9]'"
    )


def _add_normalized_columns() -> None:
    for table_name in ALL_TABLES:
        api_suffix = (
            " (API: skus)"
            if table_name in {"ods_wb_marketplace_orders", "ods_wb_new_orders"}
            else ""
        )
        op.add_column(
            table_name,
            sa.Column(
                "barcode_ori",
                sa.String(length=255),
                nullable=True,
                comment=f"原生条形码{api_suffix}",
            ),
        )
        op.add_column(
            table_name,
            sa.Column(
                "barcode_hand",
                sa.String(length=255),
                nullable=True,
                comment=f"手调条形码{api_suffix}",
            ),
        )


def _backfill_scalar_ods() -> None:
    for table_name, old_column in ODS_SCALAR_COLUMNS:
        op.execute(
            sa.text(
                f"""
                UPDATE `{table_name}`
                SET
                    barcode_ori = CASE
                        WHEN {_original_sql(f'`{old_column}`')}
                        THEN TRIM(`{old_column}`)
                        ELSE NULL
                    END,
                    barcode_hand = CASE
                        WHEN {_manual_sql(f'`{old_column}`')}
                        THEN TRIM(`{old_column}`)
                        ELSE NULL
                    END
                """
            )
        )


def _backfill_array_ods() -> None:
    for table_name, old_column in ODS_ARRAY_COLUMNS:
        op.execute(
            sa.text(
                f"""
                UPDATE `{table_name}` AS target
                SET
                    barcode_ori = (
                        SELECT values_table.barcode
                        FROM JSON_TABLE(
                            COALESCE(target.`{old_column}`, JSON_ARRAY()),
                            '$[*]' COLUMNS (
                                position FOR ORDINALITY,
                                barcode VARCHAR(255) PATH '$'
                            )
                        ) AS values_table
                        WHERE {_original_sql('values_table.barcode')}
                        ORDER BY values_table.position
                        LIMIT 1
                    ),
                    barcode_hand = (
                        SELECT values_table.barcode
                        FROM JSON_TABLE(
                            COALESCE(target.`{old_column}`, JSON_ARRAY()),
                            '$[*]' COLUMNS (
                                position FOR ORDINALITY,
                                barcode VARCHAR(255) PATH '$'
                            )
                        ) AS values_table
                        WHERE {_manual_sql('values_table.barcode')}
                        ORDER BY values_table.position
                        LIMIT 1
                    )
                """
            )
        )


def _backfill_dwd() -> None:
    op.execute(
        sa.text(
            f"""
            UPDATE dwd_wb_order_detail AS target
            LEFT JOIN ods_wb_marketplace_orders AS source
              ON source.shop_id = target.shop_id
             AND source.order_id = target.order_id
            SET
                target.barcode_ori = COALESCE(
                    source.barcode_ori,
                    CASE WHEN {_original_sql('target.barcode')}
                         THEN TRIM(target.barcode) END
                ),
                target.barcode_hand = COALESCE(
                    source.barcode_hand,
                    CASE WHEN {_manual_sql('target.barcode')}
                         THEN TRIM(target.barcode) END
                )
            """
        )
    )
    op.execute(
        sa.text(
            f"""
            UPDATE dwd_wb_order_statistics_detail AS target
            LEFT JOIN ods_wb_supplier_orders AS source
              ON source.shop_id = target.shop_id
             AND source.srid = target.srid
            SET
                target.barcode_ori = COALESCE(
                    source.barcode_ori,
                    CASE WHEN {_original_sql('target.barcode')}
                         THEN TRIM(target.barcode) END
                ),
                target.barcode_hand = COALESCE(
                    source.barcode_hand,
                    CASE WHEN {_manual_sql('target.barcode')}
                         THEN TRIM(target.barcode) END
                )
            """
        )
    )
    op.execute(
        sa.text(
            f"""
            UPDATE dwd_wb_return_detail AS target
            LEFT JOIN ods_wb_goods_returns AS source
              ON source.shop_id = target.shop_id
             AND source.srid = target.srid
            SET
                target.barcode_ori = COALESCE(
                    source.barcode_ori,
                    CASE WHEN {_original_sql('target.barcode')}
                         THEN TRIM(target.barcode) END,
                    CASE WHEN {_original_sql('target.bar_code')}
                         THEN TRIM(target.bar_code) END
                ),
                target.barcode_hand = COALESCE(
                    source.barcode_hand,
                    CASE WHEN {_manual_sql('target.barcode')}
                         THEN TRIM(target.barcode) END,
                    CASE WHEN {_manual_sql('target.bar_code')}
                         THEN TRIM(target.bar_code) END
                )
            """
        )
    )


def _drop_old_columns() -> None:
    for table_name, old_column in DWD_OLD_COLUMNS:
        op.drop_column(table_name, old_column)
    for table_name, old_column in ODS_ARRAY_COLUMNS:
        op.drop_column(table_name, old_column)
    for table_name, old_column in ODS_SCALAR_COLUMNS:
        op.drop_column(table_name, old_column)


def upgrade() -> None:
    _add_normalized_columns()
    _backfill_scalar_ods()
    _backfill_array_ods()
    _backfill_dwd()
    _drop_old_columns()


def _restore_legacy_columns() -> None:
    for table_name, old_column in ODS_SCALAR_COLUMNS:
        op.add_column(
            table_name,
            sa.Column(old_column, sa.String(length=255), nullable=True),
        )
        op.execute(
            sa.text(
                f"""
                UPDATE `{table_name}`
                SET `{old_column}` = COALESCE(barcode_ori, barcode_hand)
                """
            )
        )

    for table_name, old_column in ODS_ARRAY_COLUMNS:
        op.add_column(
            table_name,
            sa.Column(old_column, sa.JSON(), nullable=True),
        )
        op.execute(
            sa.text(
                f"""
                UPDATE `{table_name}`
                SET `{old_column}` = CASE
                    WHEN barcode_ori IS NOT NULL AND barcode_hand IS NOT NULL
                        THEN JSON_ARRAY(barcode_ori, barcode_hand)
                    WHEN barcode_ori IS NOT NULL THEN JSON_ARRAY(barcode_ori)
                    WHEN barcode_hand IS NOT NULL THEN JSON_ARRAY(barcode_hand)
                    ELSE NULL
                END
                """
            )
        )

    for table_name in (
        "dwd_wb_order_detail",
        "dwd_wb_order_statistics_detail",
        "dwd_wb_return_detail",
    ):
        op.add_column(
            table_name,
            sa.Column("barcode", sa.String(length=255), nullable=True),
        )
        op.execute(
            sa.text(
                f"""
                UPDATE `{table_name}`
                SET barcode = COALESCE(barcode_ori, barcode_hand)
                """
            )
        )
    op.add_column(
        "dwd_wb_return_detail",
        sa.Column("bar_code", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    _restore_legacy_columns()
    for table_name in reversed(ALL_TABLES):
        op.drop_column(table_name, "barcode_hand")
        op.drop_column(table_name, "barcode_ori")
