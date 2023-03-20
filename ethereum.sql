SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;


CREATE TABLE `accounts` (
  `id` int(11) NOT NULL,
  `address` binary(20) DEFAULT NULL,
  `txn` int(11) DEFAULT NULL,
  `sent` int(11) DEFAULT NULL,
  `received` int(11) DEFAULT NULL,
  `contract` int(11) DEFAULT NULL,
  `firsttx` int(11) DEFAULT NULL,
  `lasttx` int(11) DEFAULT NULL,
  `minedblockn` int(11) DEFAULT NULL,
  `minedunclen` int(11) DEFAULT NULL,
  `_type` tinyint(4) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=ascii COLLATE=ascii_general_ci;

CREATE TABLE `addresses` (
  `id` int(11) NOT NULL,
  `address` binary(20) NOT NULL,
  `hash` binary(32) NOT NULL,
  `_type` tinyint(4) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=ascii COLLATE=ascii_general_ci;

CREATE TABLE `blocks` (
  `number` int(11) NOT NULL,
  `timestamp` int(11) NOT NULL,
  `transactions` int(11) NOT NULL,
  `miner` binary(20) NOT NULL,
  `difficulty` bigint(20) NOT NULL,
  `totaldifficulty` char(32) NOT NULL,
  `size` int(11) NOT NULL,
  `gasused` int(11) NOT NULL,
  `gaslimit` int(11) NOT NULL,
  `extradata` varbinary(32) NOT NULL,
  `hash` binary(32) NOT NULL,
  `parenthash` binary(32) NOT NULL,
  `sha3uncles` binary(32) NOT NULL,
  `stateroot` binary(32) NOT NULL,
  `nonce` binary(8) NOT NULL,
  `receiptsroot` binary(32) NOT NULL,
  `transactionsroot` binary(32) NOT NULL,
  `mixhash` binary(32) NOT NULL,
  `logsbloom` blob DEFAULT NULL,
  `basefee` bigint(20) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=ascii COLLATE=ascii_general_ci;

CREATE TABLE `contracts` (
  `id` int(11) NOT NULL,
  `address` binary(20) NOT NULL,
  `blocknumber` int(11) NOT NULL,
  `transactionindex` int(11) NOT NULL,
  `code` mediumblob DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=ascii COLLATE=ascii_general_ci;

CREATE TABLE `slotlogs` (
  `id` bigint(20) NOT NULL,
  `stateid` bigint(20) NOT NULL,
  `address_id` int(11) NOT NULL,
  `slot_id` int(11) NOT NULL,
  `slotvalue` varbinary(64) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=ascii COLLATE=ascii_general_ci;

CREATE TABLE `slots` (
  `id` int(11) NOT NULL,
  `slot` binary(32) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=ascii COLLATE=ascii_general_ci;

CREATE TABLE `states` (
  `id` bigint(20) NOT NULL,
  `blocknumber` int(11) NOT NULL,
  `type` tinyint(4) DEFAULT NULL,
  `txindex` int(11) DEFAULT NULL,
  `address_id` int(11) NOT NULL,
  `nonce` int(11) DEFAULT NULL,
  `balance` decimal(32,0) DEFAULT NULL,
  `codehash` binary(32) DEFAULT NULL,
  `storageroot` binary(32) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=ascii COLLATE=ascii_general_ci;

CREATE TABLE `transactions` (
  `id` bigint(20) NOT NULL,
  `hash` binary(32) NOT NULL,
  `blocknumber` int(11) NOT NULL,
  `from` binary(20) NOT NULL,
  `to` binary(20) DEFAULT NULL,
  `gas` int(11) NOT NULL,
  `gasprice` bigint(20) NOT NULL,
  `input` mediumblob DEFAULT NULL,
  `nonce` int(11) NOT NULL,
  `transactionindex` int(11) NOT NULL,
  `value` char(32) NOT NULL,
  `v` binary(1) NOT NULL,
  `r` binary(32) NOT NULL,
  `s` binary(32) NOT NULL,
  `type` binary(1) NOT NULL,
  `maxfeepergas` bigint(20) DEFAULT NULL,
  `maxpriorityfeepergas` bigint(20) DEFAULT NULL,
  `class` tinyint(4) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=ascii COLLATE=ascii_general_ci;

CREATE TABLE `transactions_accesslist` (
  `id` int(11) NOT NULL,
  `blocknumber` int(11) NOT NULL,
  `transactionindex` int(11) NOT NULL,
  `address` binary(20) NOT NULL,
  `storagekeys` binary(32) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=ascii COLLATE=ascii_general_ci;

CREATE TABLE `uncles` (
  `id` int(11) NOT NULL,
  `blocknumber` int(11) NOT NULL,
  `uncleheight` int(11) NOT NULL,
  `uncleposition` int(11) NOT NULL,
  `timestamp` int(11) NOT NULL,
  `miner` binary(20) NOT NULL,
  `difficulty` bigint(20) NOT NULL,
  `size` int(11) NOT NULL,
  `gasused` int(11) NOT NULL,
  `gaslimit` int(11) NOT NULL,
  `extradata` varbinary(32) NOT NULL,
  `hash` binary(32) NOT NULL,
  `parenthash` binary(32) NOT NULL,
  `sha3uncles` binary(32) NOT NULL,
  `stateroot` binary(32) NOT NULL,
  `nonce` binary(8) NOT NULL,
  `receiptsroot` binary(32) NOT NULL,
  `transactionsroot` binary(32) NOT NULL,
  `mixhash` binary(32) NOT NULL,
  `logsbloom` blob DEFAULT NULL,
  `basefee` bigint(20) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=ascii COLLATE=ascii_general_ci;


ALTER TABLE `accounts`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `address` (`address`),
  ADD KEY `txn` (`txn`),
  ADD KEY `sent` (`sent`),
  ADD KEY `received` (`received`),
  ADD KEY `contract` (`contract`),
  ADD KEY `firsttx` (`firsttx`),
  ADD KEY `lasttx` (`lasttx`),
  ADD KEY `minedblockn` (`minedblockn`),
  ADD KEY `minedunclen` (`minedunclen`),
  ADD KEY `type` (`_type`);

ALTER TABLE `addresses`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `address` (`address`) USING BTREE,
  ADD UNIQUE KEY `hash` (`hash`),
  ADD KEY `_type` (`_type`);

ALTER TABLE `blocks`
  ADD PRIMARY KEY (`number`),
  ADD UNIQUE KEY `hash` (`hash`),
  ADD KEY `miner` (`miner`);

ALTER TABLE `contracts`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `address` (`address`),
  ADD KEY `blocknumber.txindex` (`blocknumber`,`transactionindex`);

ALTER TABLE `slotlogs`
  ADD PRIMARY KEY (`id`),
  ADD KEY `stateid` (`stateid`),
  ADD KEY `address_id` (`address_id`),
  ADD KEY `slot_id` (`slot_id`);

ALTER TABLE `slots`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `slot` (`slot`) USING BTREE;

ALTER TABLE `states`
  ADD PRIMARY KEY (`id`),
  ADD KEY `type` (`type`),
  ADD KEY `blocknumber` (`blocknumber`),
  ADD KEY `address_id` (`address_id`);

ALTER TABLE `transactions`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `hash` (`hash`),
  ADD KEY `blocknumber` (`blocknumber`),
  ADD KEY `from` (`from`),
  ADD KEY `to` (`to`),
  ADD KEY `class` (`class`);

ALTER TABLE `transactions_accesslist`
  ADD PRIMARY KEY (`id`),
  ADD KEY `blocknumber.txindex` (`blocknumber`,`transactionindex`);

ALTER TABLE `uncles`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `hash` (`hash`),
  ADD KEY `miner` (`miner`),
  ADD KEY `blocknumber` (`blocknumber`);


ALTER TABLE `accounts`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

ALTER TABLE `addresses`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

ALTER TABLE `contracts`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

ALTER TABLE `slotlogs`
  MODIFY `id` bigint(20) NOT NULL AUTO_INCREMENT;

ALTER TABLE `slots`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

ALTER TABLE `states`
  MODIFY `id` bigint(20) NOT NULL AUTO_INCREMENT;

ALTER TABLE `transactions`
  MODIFY `id` bigint(20) NOT NULL AUTO_INCREMENT;

ALTER TABLE `transactions_accesslist`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

ALTER TABLE `uncles`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
