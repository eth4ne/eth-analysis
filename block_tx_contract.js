const Web3 = require('web3');
const mariadb = require('mariadb');
const net = require('net');

const db_socket = '/run/mysqld/mysqld.sock';

const db_user = 'ethereum';
const db_pass = '';
const db_name = 'ethereum';

const geth_ipc_path = '/ethereum/geth/geth.ipc';

let cnt_block = 0, cnt_tx = 0, cnt_uncle = 0;
let running = false;

function sleep(ms) {
  return new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
}

function connect_web3() {
  return new Web3(geth_ipc_path, net);
}

function connect_db() {
  return mariadb.createConnection({socketPath: db_socket, user: db_user, password: db_pass, database: db_name});
}

async function run(from, to) {
  let start = new Date();
  cnt_block = 0;
  cnt_tx = 0;
  cnt_uncle = 0;
  let web3 = connect_web3();
  let conn = await connect_db();
  await conn.query('SET SESSION foreign_key_checks=OFF;');
  await conn.beginTransaction();
  const commit_period_max = 100;
  let commit_period = 1;
  if (to - from > commit_period_max) {
    commit_period = commit_period_max;
  } else {
    commit_period = 1;
  }
  for (let i = from; i <= to; i++) {
    let query = await conn.query("SELECT * FROM `blocks` WHERE `number`=?;", [i]);
    if (query.length === 0) {
      try {
        let block = await web3.eth.getBlock(i);
        let txn = await web3.eth.getBlockTransactionCount(i);
        let unclen = block.uncles.length;
        await insert_block_batch(conn, block, txn);
        cnt_block++;
        for (let j = 0; j < txn; j++) {
          try {
            let tx = await web3.eth.getTransactionFromBlock(i, j);
            if (tx.to === null) {
              let receipt = await web3.eth.getTransactionReceipt(tx.hash);
              await insert_contract_batch(conn, receipt.contractAddress, tx.hash);
              await insert_account_batch(conn, null, receipt.contractAddress, 0, 0, 0, 0, null, null, null, null, null, 1);
            }
            await insert_tx_batch(conn, block, tx, 0);
            cnt_tx++;
          } catch {
            console.log('Error request: blk #%d, tx #%d', i, j);
            web3 = connect_web3();
          }
        }
        for (let j = 0; j < unclen; j++) {
          try {
            let uncle = await web3.eth.getUncle(i, j);
            insert_uncle_batch(conn, block, uncle, j);
            cnt_uncle++;
          } catch {
            console.log('Error request: blk #%d, ucl #%d', i, j);
            web3 = connect_web3();
          }
        }
      } catch (err) {
        console.error(err);
        console.log('Error processing blk #%d', i);
        web3 = connect_web3();
      }
      if (cnt_block % commit_period === 0) {
        try {
          await conn.commit();
          await conn.beginTransaction();
        } catch (err) {
          console.error(err);
          console.log('Error commiting: %d', cnt_block);
          try {
            conn.rollback();
            conn.destroy();
          } catch (err) {
          }
          conn = await connect_db();
          await conn.query('SET SESSION foreign_key_checks=OFF;');
          await conn.beginTransaction();
        }
      }
    }
    if (i % 1000 === 0) {
      let ms = new Date() - start;
      console.error('Blk height: %d, Blkn: %d(%d/s), Txn: %d(%d/s), Ucln: %d(%d/s), Time: %dms', i, cnt_block, (cnt_block/ms*1000).toFixed(2), cnt_tx, (cnt_tx/ms*1000).toFixed(2), cnt_uncle, (cnt_uncle/ms*1000).toFixed(2), ms);
    }
  }
  await conn.commit();
  await conn.end();
  running = false;
}

async function insert_block_batch (conn, block, txn) {
  try {
    await conn.query("INSERT INTO `blocks` (`number`, `timestamp`, `transactions`, `miner`, `difficulty`, `totaldifficulty`, `size`, `gasused`, `gaslimit`, `extradata`, `hash`, `parenthash`, `sha3uncles`, `stateroot`, `nonce`, `receiptsroot`, `transactionsroot`, `mixhash`) VALUES (?, ?, ?, UNHEX(SUBSTRING(?, 3)), ?, ?, ?, ?, ?, UNHEX(SUBSTRING(?, 3)), UNHEX(SUBSTRING(?, 3)), UNHEX(SUBSTRING(?, 3)), UNHEX(SUBSTRING(?, 3)), UNHEX(SUBSTRING(?, 3)), UNHEX(SUBSTRING(?, 3)), UNHEX(SUBSTRING(?, 3)), UNHEX(SUBSTRING(?, 3)), UNHEX(SUBSTRING(?, 3)));", [block.number, block.timestamp, txn, block.miner, block.difficulty, block.totalDifficulty, block.size, block.gasUsed, block.gasLimit, block.extraData, block.hash, block.parentHash, block.sha3Uncles, block.stateRoot, block.nonce, block.receiptsRoot, block.transactionsRoot, block.mixHash]);
  } catch (err) {
    console.log(err);
    console.log('Error insert: blk #%d', block.number);
  }
}

async function insert_tx_batch (conn, block, tx) {
  try {
    await conn.query("INSERT INTO `transactions` (`blocknumber`, `hash`, `from`, `to`, `gas`, `gasprice`, `input`, `nonce`, `transactionindex`, `value`, `v`, `r`, `s`, `type`, `_iscontract`) VALUES (?, UNHEX(SUBSTRING(?, 3)), UNHEX(SUBSTRING(?, 3)), UNHEX(SUBSTRING(?, 3)), ?, ?, UNHEX(SUBSTRING(?, 3)), ?, ?, ?, UNHEX(SUBSTRING(?, 3)), UNHEX(SUBSTRING(?, 3)), UNHEX(SUBSTRING(?, 3)), UNHEX(SUBSTRING(?, 3)), ?);", [block.number, tx.hash, tx.from, tx.to, tx.gas, tx.gasPrice, tx.input, tx.nonce, tx.transactionIndex, tx.value, tx.v, tx.r, tx.s, tx.type, null]);
  } catch (err) {
    console.log(err);
    console.log('Error insert: blk #%d, tx #%d', block.number, tx.transactionIndex);
  }
}

async function insert_uncle_batch (conn, block, uncle, uncleposition) {
  try {
    await conn.query("INSERT INTO `uncles` (`blocknumber`, `uncleheight`, `uncleposition`, `timestamp`, `miner`, `difficulty`, `size`, `gasused`, `gaslimit`, `extradata`, `hash`, `parenthash`, `sha3uncles`, `stateroot`, `nonce`, `receiptsroot`, `transactionsroot`, `mixhash`) VALUES (?, ?, ?, ?, UNHEX(SUBSTRING(?, 3)), ?, ?, ?, ?, UNHEX(SUBSTRING(?, 3)), UNHEX(SUBSTRING(?, 3)), UNHEX(SUBSTRING(?, 3)), UNHEX(SUBSTRING(?, 3)), UNHEX(SUBSTRING(?, 3)), UNHEX(SUBSTRING(?, 3)), UNHEX(SUBSTRING(?, 3)), UNHEX(SUBSTRING(?, 3)), UNHEX(SUBSTRING(?, 3)));", [block.number, uncle.number, uncleposition, uncle.timestamp, uncle.miner, uncle.difficulty, uncle.size, uncle.gasUsed, uncle.gasLimit, uncle.extraData, uncle.hash, uncle.parentHash, uncle.sha3Uncles, uncle.stateRoot, uncle.nonce, uncle.receiptsRoot, uncle.transactionsRoot, uncle.mixHash]);
  } catch (err) {
    console.log(err);
    console.log('Error insert: blk #%d, ucl #%d', block.number, uncleposition);
  }
}

async function insert_contract_batch (conn, address, txhash) {
  try {
    await conn.query("INSERT INTO `contracts` (`address`, `creationtx`) VALUES(UNHEX(SUBSTRING(?, 3)), UNHEX(SUBSTRING(?, 3)));", [address, txhash]);
  } catch (err) {
    console.log(err);
    console.log('Error insert: contract ', address);
  }
}

async function insert_account_batch (conn, id, address, txn, sent, received, contract, firsttx, lasttx, balance, minedblockn, minedunclen, _type) {
  try {
    if (id === null) {
      await conn.query("INSERT INTO `accounts` (`address`, `txn`, `sent`, `received`, `contract`, `firsttx`, `lasttx`, `balance`, `minedblockn`, `minedunclen`, `_type`) values (UNHEX(SUBSTRING(?, 3)), ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);", [address, txn, sent, received, contract, firsttx, lasttx, balance, minedblockn, minedunclen, _type]);
    } else {
      await conn.query("UPDATE `accounts` SET `txn`=?, `sent`=?, `received`=?, `contract`=?, `firsttx`=?, `lasttx`=? WHERE `id`=?;", [txn, sent, received, contract, firsttx, lasttx, id]);
    }
  } catch (err) {
    console.log(err);
    console.log('Error insert: account ', address);
  }
}

async function stationkeep() {
  if (running == false) {
    running = true;
    let conn = await connect_db();
    conn.query("SELECT * FROM `blocks` ORDER BY `number` DESC LIMIT 1;").then(async function(res) {
      let web3 = connect_web3();
      let latest = await web3.eth.getBlock('latest');
      if (res.length === 0) {
        console.error('Run from start');
        run(0, 1);
      }
      if (res[0].number < latest.number) {
        console.error('Run from %d to %d', res[0].number+1, latest.number-1);
        run(res[0].number+1, latest.number-1);
      } else {
        running = false;
      }
      conn.end();
    }).catch(err => {
      conn.end();
    });
  }
}

stationkeep();
setInterval(stationkeep, 1000);
