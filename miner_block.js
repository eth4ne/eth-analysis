const mysql = require('mysql');

const db_host = 'localhost';

const db_user = 'ethereum';
const db_pass = '';
const db_name = 'ethereum';

let cnt_block = 0;

let start = new Date();

function sleep(ms) {
  return new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
}

function mysql_query(conn, sql, data) {
  return new Promise((resolve, reject) => {
    conn.query(sql, data, (error, results, fields) => {
      if (error) reject(error);
      resolve(results);
    });
  })
}

let cache = {};
let conn = null;

async function run(from, to) {
  conn = await mysql.createConnection({host: db_host, user: db_user, password: db_pass, database: db_name});
  await conn.connect();
  const batchsize = 10000;
  const commit_period = 1000000;
  const log_period = 100000;
  for (let i = from; i < to; i+=batchsize) {
    let query = await mysql_query(conn, "SELECT `number`, `miner` FROM `blocks` WHERE `number`>=? AND `number`<?;", [i, i+batchsize]);
    cnt_block+=batchsize;
    if (query.length !== 0) {
      for (let j = 0; j < query.length; j++) {
        try{
          let miner = Buffer.from(query[j].miner).toString('hex');
          await add_account_block(miner, query[j].number);
        } catch {
          console.log('Error blk #%d', query[j].number);
        }
      }
    }
    if (i % log_period === 0) {
      let ms = new Date() - start;
      console.error('Blk height: %d, Blkn: %d(%d/s), Time: %dms', i, cnt_block, (cnt_block/ms*1000).toFixed(2), ms);
    }
    if (i % commit_period === 0) {
      await flush_accounts();
    }
  }
  await flush_accounts();
  conn.end();
  running = false;
}

async function add_account_block (address, number) {
  if (!(address in cache)) {
    let addr = Buffer.from(address, 'hex');
    let query = await mysql_query(conn, "SELECT * FROM `accounts` WHERE `address`=?;", [addr]);
    if (query.length !== 0) {
      cache[address] = {
        id: query[0].id,
        txn: query[0].txn,
        sent: query[0].sent,
        received: query[0].received,
        contract: query[0].contract,
        firsttx: query[0].firsttx,
        lasttx: query[0].lasttx,
        minedblockn: query[0].minedblockn,
        minedunclen: query[0].minedunclen,
        _type: query[0]._type,
      }
    } else {
      cache[address] = {
        id: null,
        txn: 0,
        sent: 0,
        received: 0,
        contract: 0,
        firsttx: null,
        lasttx: null,
        minedblockn: 0,
        minedunclen: 0,
        _type: 0,
      }
    }
  }

  cache[address].minedblockn += 1;
}

async function flush_accounts () {
  let cnt = 0;
  await conn.beginTransaction();
  for (let i in cache) {
    insert_account_batch(conn, cache[i].id, i, cache[i].txn, cache[i].sent, cache[i].received, cache[i].contract, cache[i].firsttx, cache[i].lasttx, cache[i].minedblockn, cache[i].minedunclen, cache[i]._type);
    cnt++;
  }
  try {
    console.log('Commiting %d accounts...', cnt);
    await conn.commit();
    cache = {};
  } catch (err) {
    console.log('Error flushing', i);
    try {
      conn.rollback();
      conn.destroy();
    } catch (err) {
      console.log('MariaDB error');
    }
    conn = await mariadb.createConnection({host: db_host, user: db_user, password: db_pass, database: db_name});
  }
}

async function insert_account_batch (conn, id, address, txn, sent, received, contract, firsttx, lasttx, minedblockn, minedunclen, _type) {
  try {
    if (id === null) {
      let addr = Buffer.from(address, 'hex');
      mysql_query(conn, "INSERT INTO `accounts` (`address`, `txn`, `sent`, `received`, `contract`, `firsttx`, `lasttx`, `minedblockn`, `minedunclen`, `_type`) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);", [addr, txn, sent, received, contract, firsttx, lasttx, minedblockn, minedunclen, _type]);
    } else {
      mysql_query(conn, "UPDATE `accounts` SET `minedblockn`=? WHERE `id`=?;", [minedblockn, id]);
    }
  } catch (err) {
    console.log(err);
    let addr = Buffer.from(address, 'hex');
    console.log('Error insertion address ', address);
  }
}


run(0, 15000000);
