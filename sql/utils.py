def get_sql_for_connection(schema_editor, direction: str) -> str:
    """
    Returns the vendor and the collection of SQL Statements depending on:

    1. The SQL Engine
    2. Direction of Migrations: forward or Backward
    """
    vendor = schema_editor.connection.vendor
    try:
        return vendor, CUSTOM_SQL[vendor][direction]
    except KeyError as error:
        # In case it's oracle or some other django supported db that we do not support yet.
        raise RuntimeError(
            f"We currently do not support {vendor}. Please open an issue at https://github.com/dj-stripe/dj-stripe/issues/new?assignees=&labels=discussion&template=feature-or-enhancement-proposal.md&title= if you'd like it supported.",
        ) from error
