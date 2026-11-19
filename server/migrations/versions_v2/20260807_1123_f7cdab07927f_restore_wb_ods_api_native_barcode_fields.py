"""restore wb ods api native barcode fields

Revision ID: f7cdab07927f
Revises: 11f65441bb50
Create Date: 2026-08-07 11:23:58.328758

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "f7cdab07927f"
down_revision = "11f65441bb50"
branch_labels = None
depends_on = None


SCALAR_ODS_COLUMNS = (
    ("ods_wb_supplier_sales", "barcode"),
    ("ods_wb_supplier_orders", "barcode"),
    ("ods_wb_sales_reports", "sku"),
    ("ods_wb_goods_returns", "barcode"),
)
ARRAY_ODS_COLUMNS = (
    ("ods_wb_marketplace_orders", "skus"),
    ("ods_wb_new_orders", "skus"),
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


def _add_native_columns() -> None:
    for table_name, column_name in SCALAR_ODS_COLUMNS:
        op.add_column(
            table_name,
            sa.Column(
                column_name,
                sa.String(length=255),
                nullable=True,
                comment=f"API native field: {column_name}",
            ),
        )
    for table_name, column_name in ARRAY_ODS_COLUMNS:
        op.add_column(
            table_name,
            sa.Column(
                column_name,
                sa.JSON(),
                nullable=True,
                comment=f"API native field: {column_name}",
            ),
        )


def _backfill_native_columns() -> None:
    for table_name, column_name in SCALAR_ODS_COLUMNS:
        op.execute(
            sa.text(
                f"""
                UPDATE `{table_name}`
                SET `{column_name}` = COALESCE(
                    NULLIF(
                        JSON_UNQUOTE(JSON_EXTRACT(row_data, '$.{column_name}')),
                        'null'
                    ),
                    barcode_ori,
                    barcode_hand
                )
                """
            )
        )

    for table_name, column_name in ARRAY_ODS_COLUMNS:
        op.execute(
            sa.text(
                f"""
                UPDATE `{table_name}`
                SET `{column_name}` = COALESCE(
                    JSON_EXTRACT(row_data, '$.{column_name}'),
                    CASE
                        WHEN barcode_ori IS NOT NULL AND barcode_hand IS NOT NULL
                            THEN JSON_ARRAY(barcode_ori, barcode_hand)
                        WHEN barcode_ori IS NOT NULL THEN JSON_ARRAY(barcode_ori)
                        WHEN barcode_hand IS NOT NULL THEN JSON_ARRAY(barcode_hand)
                        ELSE NULL
                    END
                )
                """
            )
        )


def _drop_normalized_ods_columns() -> None:
    for table_name, _ in (*SCALAR_ODS_COLUMNS, *ARRAY_ODS_COLUMNS):
        op.drop_column(table_name, "barcode_hand")
        op.drop_column(table_name, "barcode_ori")


def upgrade() -> None:
    _add_native_columns()
    _backfill_native_columns()
    _drop_normalized_ods_columns()


def _add_normalized_ods_columns() -> None:
    for table_name, _ in (*SCALAR_ODS_COLUMNS, *ARRAY_ODS_COLUMNS):
        op.add_column(
            table_name,
            sa.Column("barcode_ori", sa.String(length=255), nullable=True),
        )
        op.add_column(
            table_name,
            sa.Column("barcode_hand", sa.String(length=255), nullable=True),
        )


def _backfill_normalized_ods_columns() -> None:
    for table_name, column_name in SCALAR_ODS_COLUMNS:
        op.execute(
            sa.text(
                f"""
                UPDATE `{table_name}`
                SET
                    barcode_ori = CASE
                        WHEN {_original_sql(f'`{column_name}`')}
                        THEN TRIM(`{column_name}`)
                        ELSE NULL
                    END,
                    barcode_hand = CASE
                        WHEN {_manual_sql(f'`{column_name}`')}
                        THEN TRIM(`{column_name}`)
                        ELSE NULL
                    END
                """
            )
        )

    for table_name, column_name in ARRAY_ODS_COLUMNS:
        op.execute(
            sa.text(
                f"""
                UPDATE `{table_name}` AS target
                SET
                    barcode_ori = (
                        SELECT values_table.barcode
                        FROM JSON_TABLE(
                            COALESCE(target.`{column_name}`, JSON_ARRAY()),
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
                            COALESCE(target.`{column_name}`, JSON_ARRAY()),
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


def downgrade() -> None:
    _add_normalized_ods_columns()
    _backfill_normalized_ods_columns()
    for table_name, column_name in reversed((*SCALAR_ODS_COLUMNS, *ARRAY_ODS_COLUMNS)):
        op.drop_column(table_name, column_name)
