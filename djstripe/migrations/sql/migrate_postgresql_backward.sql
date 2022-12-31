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
