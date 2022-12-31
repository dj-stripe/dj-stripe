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
