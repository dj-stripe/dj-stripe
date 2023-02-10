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


--
-- Rename field destination_clone on payout to destination
--
ALTER TABLE "djstripe_payout" RENAME COLUMN "destination_clone_id" TO "destination_id";
