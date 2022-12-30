CUSTOM_SQL = {
    "postgresql": {
        "forward": """
            --
            -- Add field destination_clone to payout
            --
            ALTER TABLE "djstripe_payout" ADD COLUMN "destination_clone_id" varchar(255) NULL CONSTRAINT "djstripe_payout_destination_clone_id_ff0fec04_fk_djstripe_"
            REFERENCES "djstripe_djstripepaymentmethod"("id") DEFERRABLE INITIALLY IMMEDIATE;
            SET CONSTRAINTS "djstripe_payout_destination_clone_id_ff0fec04_fk_djstripe_" IMMEDIATE;
            CREATE INDEX "djstripe_payout_destination_clone_id_ff0fec04" ON "djstripe_payout" ("destination_clone_id");
            CREATE INDEX "djstripe_payout_destination_clone_id_ff0fec04_like" ON "djstripe_payout" ("destination_clone_id" varchar_pattern_ops);
            --
            -- Copy data from old column to new column
            --
            UPDATE djstripe_payout
            SET destination_clone_id = (SELECT id from djstripe_bankaccount WHERE djstripe_bankaccount.djstripe_id = djstripe_payout.destination_id)
            WHERE EXISTS(SELECT * from djstripe_bankaccount WHERE djstripe_bankaccount.djstripe_id = djstripe_payout.destination_id);
            --
            -- Remove field destination from payout
            --
            ALTER TABLE "djstripe_payout" DROP COLUMN "destination_id" CASCADE;
            -- ALTER TABLE "djstripe_payout" DROP COLUMN "destination_clone_id" CASCADE;
            --
            -- Rename field destination_clone on payout to destination
            --
            ALTER TABLE "djstripe_payout" RENAME COLUMN "destination_clone_id" TO "destination_id";
            """,
        "backward": """
            --
            -- Rename field destination_clone on payout to destination
            --
            SET CONSTRAINTS "djstripe_payout_destination_clone_id_ff0fec04_fk_djstripe_" IMMEDIATE;
            ALTER TABLE "djstripe_payout" DROP CONSTRAINT "djstripe_payout_destination_clone_id_ff0fec04_fk_djstripe_";
            ALTER TABLE "djstripe_payout" RENAME COLUMN "destination_id" TO "destination_clone_id";
            ALTER TABLE "djstripe_payout" ADD CONSTRAINT "djstripe_payout_destination_clone_id_ff0fec04_fk_djstripe_" FOREIGN KEY ("destination_clone_id") REFERENCES "djstripe_djstripepaymentmethod" ("id") DEFERRABLE INITIALLY DEFERRED;
            --
            -- Remove field destination from payout
            --
            ALTER TABLE "djstripe_payout" ADD COLUMN "destination_id" bigint NULL CONSTRAINT "djstripe_payout_destination_id_a5fa55c2_fk_djstripe_" REFERENCES "djstripe_bankaccount"("djstripe_id") DEFERRABLE INITIALLY DEFERRED; SET CONSTRAINTS "djstripe_payout_destination_id_a5fa55c2_fk_djstripe_" IMMEDIATE;
            CREATE INDEX "djstripe_payout_destination_id_a5fa55c2" ON "djstripe_payout" ("destination_id");
            --
            -- Raw SQL operation
            --
            UPDATE djstripe_payout SET destination_id = (select djstripe_id from djstripe_bankaccount where djstripe_bankaccount.id = djstripe_payout. destination_clone_id)
            WHERE EXISTS(select * from djstripe_bankaccount where djstripe_bankaccount.id = djstripe_payout.destination_clone_id);
            --
            -- Add field destination_clone to payout
            --
            ALTER TABLE "djstripe_payout" DROP COLUMN "destination_clone_id" CASCADE;
            """,
    },
    "sqlite": {
        "forward": """
            --
            -- Add field destination_clone to payout
            --
            ALTER TABLE "djstripe_payout" ADD COLUMN "destination_clone_id" varchar(255) NULL REFERENCES "djstripe_djstripepaymentmethod" ("id") DEFERRABLE INITIALLY DEFERRED;
            CREATE INDEX "djstripe_payout_destination_clone_id_ff0fec04" ON "djstripe_payout" ("destination_clone_id");

            --
            -- Raw SQL operation
            --
            UPDATE djstripe_payout SET destination_clone_id = (SELECT id from djstripe_bankaccount WHERE djstripe_bankaccount.djstripe_id = djstripe_payout.destination_id)
            WHERE EXISTS(SELECT * from djstripe_bankaccount WHERE djstripe_bankaccount.djstripe_id = djstripe_payout.destination_id);

            --
            -- Rename field destination_clone on payout to destination
            --
            CREATE TABLE "new__djstripe_payout" ("destination_id" varchar(255) NULL REFERENCES "djstripe_djstripepaymentmethod" ("id") DEFERRABLE INITIALLY DEFERRED, "djstripe_id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "id" varchar(255) NOT NULL UNIQUE, "livemode" bool NULL, "created" datetime NULL, "metadata" text NULL CHECK ((JSON_VALID("metadata") OR "metadata" IS NULL)), "description" text NULL, "djstripe_created" datetime NOT NULL, "djstripe_updated" datetime NOT NULL, "amount" decimal NOT NULL, "arrival_date" datetime NOT NULL, "currency" varchar(3) NOT NULL, "failure_code" varchar(32) NOT NULL, "failure_message" text NOT NULL, "method" varchar(8) NOT NULL, "statement_descriptor" varchar(255) NOT NULL, "status" varchar(10) NOT NULL, "type" varchar(12) NOT NULL, "balance_transaction_id" bigint NULL REFERENCES "djstripe_balancetransaction" ("djstripe_id") DEFERRABLE INITIALLY DEFERRED, "failure_balance_transaction_id" bigint NULL REFERENCES "djstripe_balancetransaction" ("djstripe_id") DEFERRABLE INITIALLY DEFERRED, "djstripe_owner_account_id" bigint NULL REFERENCES "djstripe_account" ("djstripe_id") DEFERRABLE INITIALLY DEFERRED, "automatic" bool NOT NULL, "source_type" varchar(12) NOT NULL);
            INSERT INTO "new__djstripe_payout" ("djstripe_id", "id", "livemode", "created", "metadata", "description", "djstripe_created", "djstripe_updated", "amount", "arrival_date", "currency", "failure_code", "failure_message", "method", "statement_descriptor", "status", "type", "balance_transaction_id", "failure_balance_transaction_id", "djstripe_owner_account_id", "automatic", "source_type", "destination_id") SELECT "djstripe_id", "id", "livemode", "created", "metadata", "description", "djstripe_created", "djstripe_updated", "amount", "arrival_date", "currency", "failure_code", "failure_message", "method", "statement_descriptor", "status", "type", "balance_transaction_id", "failure_balance_transaction_id", "djstripe_owner_account_id", "automatic", "source_type", "destination_clone_id" FROM "djstripe_payout";
            DROP TABLE "djstripe_payout";
            ALTER TABLE "new__djstripe_payout" RENAME TO "djstripe_payout";
            CREATE INDEX "djstripe_payout_destination_id_a5fa55c2" ON "djstripe_payout" ("destination_id");
            CREATE INDEX "djstripe_payout_balance_transaction_id_a9393fb6" ON "djstripe_payout" ("balance_transaction_id");
            CREATE INDEX "djstripe_payout_failure_balance_transaction_id_77d442db" ON "djstripe_payout" ("failure_balance_transaction_id");
            CREATE INDEX "djstripe_payout_djstripe_owner_account_id_8aac4e8e" ON "djstripe_payout" ("djstripe_owner_account_id");
            """,
        "backward": """
            --
            -- Rename field destination_clone on payout to destination
            --
            CREATE TABLE "new__djstripe_payout" ("destination_clone_id" varchar(255) NULL REFERENCES "djstripe_djstripepaymentmethod" ("id") DEFERRABLE INITIALLY DEFERRED, "djstripe_id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "id" varchar(255) NOT NULL UNIQUE, "livemode" bool NULL, "created" datetime NULL, "metadata" text NULL CHECK ((JSON_VALID("metadata") OR "metadata" IS NULL)), "description" text NULL, "djstripe_created" datetime NOT NULL, "djstripe_updated" datetime NOT NULL, "amount" decimal NOT NULL, "arrival_date" datetime NOT NULL, "currency" varchar(3) NOT NULL, "failure_code" varchar(32) NOT NULL, "failure_message" text NOT NULL, "method" varchar(8) NOT NULL, "statement_descriptor" varchar(255) NOT NULL, "status" varchar(10) NOT NULL, "type" varchar(12) NOT NULL, "balance_transaction_id" bigint NULL REFERENCES "djstripe_balancetransaction" ("djstripe_id") DEFERRABLE INITIALLY DEFERRED, "failure_balance_transaction_id" bigint NULL REFERENCES "djstripe_balancetransaction" ("djstripe_id") DEFERRABLE INITIALLY DEFERRED, "djstripe_owner_account_id" bigint NULL REFERENCES "djstripe_account" ("djstripe_id") DEFERRABLE INITIALLY DEFERRED, "automatic" bool NOT NULL, "source_type" varchar(12) NOT NULL);
            INSERT INTO "new__djstripe_payout" ("djstripe_id", "id", "livemode", "created", "metadata", "description", "djstripe_created", "djstripe_updated", "amount", "arrival_date", "currency", "failure_code", "failure_message", "method", "statement_descriptor", "status", "type", "balance_transaction_id", "failure_balance_transaction_id", "djstripe_owner_account_id", "automatic", "source_type", "destination_clone_id") SELECT "djstripe_id", "id", "livemode", "created", "metadata", "description", "djstripe_created", "djstripe_updated", "amount", "arrival_date", "currency", "failure_code", "failure_message", "method", "statement_descriptor", "status", "type", "balance_transaction_id", "failure_balance_transaction_id", "djstripe_owner_account_id", "automatic", "source_type", "destination_id" FROM "djstripe_payout";
            DROP TABLE "djstripe_payout";
            ALTER TABLE "new__djstripe_payout" RENAME TO "djstripe_payout";
            CREATE INDEX "djstripe_payout_destination_clone_id_ff0fec04" ON "djstripe_payout" ("destination_clone_id");
            CREATE INDEX "djstripe_payout_balance_transaction_id_a9393fb6" ON "djstripe_payout" ("balance_transaction_id");
            CREATE INDEX "djstripe_payout_failure_balance_transaction_id_77d442db" ON "djstripe_payout" ("failure_balance_transaction_id");
            CREATE INDEX "djstripe_payout_djstripe_owner_account_id_8aac4e8e" ON "djstripe_payout" ("djstripe_owner_account_id");

            --
            -- Remove field destination from payout
            --
            ALTER TABLE "djstripe_payout" ADD COLUMN "destination_id" bigint NULL REFERENCES "djstripe_bankaccount" ("djstripe_id") DEFERRABLE INITIALLY DEFERRED;
            CREATE INDEX "djstripe_payout_destination_id_a5fa55c2" ON "djstripe_payout" ("destination_id");

            --
            -- Raw SQL operation
            --
            UPDATE djstripe_payout SET destination_id = (select djstripe_id from djstripe_bankaccount where djstripe_bankaccount.id = djstripe_payout. destination_clone_id)
            WHERE EXISTS(select * from djstripe_bankaccount where djstripe_bankaccount.id = djstripe_payout.destination_clone_id);


            --
            -- Add field destination_clone to payout
            --
            CREATE TABLE "new__djstripe_payout" ("djstripe_id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "id" varchar(255) NOT NULL UNIQUE, "livemode" bool NULL, "created" datetime NULL, "metadata" text NULL CHECK ((JSON_VALID("metadata") OR "metadata" IS NULL)), "description" text NULL, "djstripe_created" datetime NOT NULL, "djstripe_updated" datetime NOT NULL, "amount" decimal NOT NULL, "arrival_date" datetime NOT NULL, "currency" varchar(3) NOT NULL, "failure_code" varchar(32) NOT NULL, "failure_message" text NOT NULL, "method" varchar(8) NOT NULL, "statement_descriptor" varchar(255) NOT NULL, "status" varchar(10) NOT NULL, "type" varchar(12) NOT NULL, "destination_id" bigint NULL REFERENCES "djstripe_bankaccount" ("djstripe_id") DEFERRABLE INITIALLY DEFERRED, "balance_transaction_id" bigint NULL REFERENCES "djstripe_balancetransaction" ("djstripe_id") DEFERRABLE INITIALLY DEFERRED, "failure_balance_transaction_id" bigint NULL REFERENCES "djstripe_balancetransaction" ("djstripe_id") DEFERRABLE INITIALLY DEFERRED, "djstripe_owner_account_id" bigint NULL REFERENCES "djstripe_account" ("djstripe_id") DEFERRABLE INITIALLY DEFERRED, "automatic" bool NOT NULL, "source_type" varchar(12) NOT NULL);
            INSERT INTO "new__djstripe_payout" ("djstripe_id", "id", "livemode", "created", "metadata", "description", "djstripe_created", "djstripe_updated", "amount", "arrival_date", "currency", "failure_code", "failure_message", "method", "statement_descriptor", "status", "type", "destination_id", "balance_transaction_id", "failure_balance_transaction_id", "djstripe_owner_account_id", "automatic", "source_type") SELECT "djstripe_id", "id", "livemode", "created", "metadata", "description", "djstripe_created", "djstripe_updated", "amount", "arrival_date", "currency", "failure_code", "failure_message", "method", "statement_descriptor", "status", "type", "destination_id", "balance_transaction_id", "failure_balance_transaction_id", "djstripe_owner_account_id", "automatic", "source_type" FROM "djstripe_payout";
            DROP TABLE "djstripe_payout";
            ALTER TABLE "new__djstripe_payout" RENAME TO "djstripe_payout";
            CREATE INDEX "djstripe_payout_destination_id_a5fa55c2" ON "djstripe_payout" ("destination_id");
            CREATE INDEX "djstripe_payout_balance_transaction_id_a9393fb6" ON "djstripe_payout" ("balance_transaction_id");
            CREATE INDEX "djstripe_payout_failure_balance_transaction_id_77d442db" ON "djstripe_payout" ("failure_balance_transaction_id");
            CREATE INDEX "djstripe_payout_djstripe_owner_account_id_8aac4e8e" ON "djstripe_payout" ("djstripe_owner_account_id");
            """,
    },
    "mysql": {
        "forward": """
            --
            -- Add field destination_clone to payout
            --
            ALTER TABLE `djstripe_payout` ADD COLUMN `destination_clone_id` varchar(255) NULL , ADD CONSTRAINT `djstripe_payout_destination_clone_id_ff0fec04_fk_djstripe_` FOREIGN KEY (`destination_clone_id`) REFERENCES `djstripe_djstripepaymentmethod`(`id`);
            CREATE INDEX `djstripe_payout_destination_clone_id_ff0fec04` ON `djstripe_payout` (`destination_clone_id`);
            --
            -- Raw SQL operation
            --
            UPDATE djstripe_payout SET destination_clone_id = (SELECT id from djstripe_bankaccount WHERE djstripe_bankaccount.djstripe_id = djstripe_payout.destination_id)
            WHERE EXISTS(SELECT * from djstripe_bankaccount WHERE djstripe_bankaccount.djstripe_id = djstripe_payout.destination_id);
            --
            -- Remove field destination from payout
            --
            ALTER TABLE `djstripe_payout` DROP FOREIGN KEY `djstripe_payout_destination_id_a5fa55c2_fk_djstripe_`;
            ALTER TABLE `djstripe_payout` DROP COLUMN `destination_id`;
            --
            -- Rename field destination_clone on payout to destination
            --
            ALTER TABLE `djstripe_payout` CHANGE `destination_clone_id` `destination_id` varchar(255) NULL;
            """,
        "backward": """
            --
            -- Rename field destination_clone on payout to destination
            --
            ALTER TABLE `djstripe_payout` CHANGE `destination_id` `destination_clone_id` varchar(255) NULL;
            --
            -- Remove field destination from payout
            --
            ALTER TABLE `djstripe_payout` ADD COLUMN `destination_id` bigint NULL , ADD CONSTRAINT `djstripe_payout_destination_id_a5fa55c2_fk_djstripe_` FOREIGN KEY (`destination_id`) REFERENCES `djstripe_bankaccount`(`djstripe_id`);
            CREATE INDEX `djstripe_payout_destination_id_a5fa55c2` ON `djstripe_payout` (`destination_id`);
            --
            -- Raw SQL operation
            --
            UPDATE djstripe_payout SET destination_id = (select djstripe_id from djstripe_bankaccount where djstripe_bankaccount.id = djstripe_payout. destination_clone_id)
            WHERE EXISTS(select * from djstripe_bankaccount where djstripe_bankaccount.id = djstripe_payout.destination_clone_id);
            --
            -- Add field destination_clone to payout
            --
            ALTER TABLE `djstripe_payout` DROP FOREIGN KEY `djstripe_payout_destination_clone_id_ff0fec04_fk_djstripe_`;
            ALTER TABLE `djstripe_payout` DROP COLUMN `destination_clone_id`;
            """,
    },
}


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
