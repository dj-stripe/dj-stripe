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
