from pathlib import Path

import django.db.models.deletion
from django.db import migrations

import djstripe.fields


def get_sql_for_connection(schema_editor, direction: str) -> str:
    """
    Returns the vendor and the collection of SQL Statements depending on:

    1. The SQL Engine
    2. Direction of Migrations: forward or Backward
    """
    vendor = schema_editor.connection.vendor
    # Construct Path to SQL
    file_path = Path(__file__).parent / "sql" / f"migrate_{vendor}_{direction}.sql"
    try:
        sql_statement = Path(file_path).read_text()
    except FileNotFoundError as error:
        # In case it's oracle or some other django supported db that we do not support yet.
        raise RuntimeError(
            f"We currently do not support {vendor}. Please open an issue at https://github.com/dj-stripe/dj-stripe/issues/new?assignees=&labels=discussion&template=feature-or-enhancement-proposal.md&title= if you'd like it supported.",
        ) from error
    return vendor, sql_statement


def forwards_func(apps, schema_editor):
    vendor, sql_statement = get_sql_for_connection(schema_editor, "forward")
    with schema_editor.connection.cursor() as cursor:
        if vendor == "sqlite":
            cursor.executescript(sql_statement)
        else:
            cursor.execute(sql_statement)


def reverse_func(apps, schema_editor):
    vendor, sql_statement = get_sql_for_connection(schema_editor, "backward")
    with schema_editor.connection.cursor() as cursor:
        if vendor == "sqlite":
            cursor.executescript(sql_statement)
        else:
            cursor.execute(sql_statement)


class Migration(migrations.Migration):
    dependencies = [
        ("djstripe", "0012_2_8"),
    ]
    operations = [
        migrations.RunPython(forwards_func, reverse_func),
        migrations.AlterField(
            model_name="payout",
            name="destination",
            field=djstripe.fields.PaymentMethodForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                to="djstripe.djstripepaymentmethod",
            ),
        ),
    ]
