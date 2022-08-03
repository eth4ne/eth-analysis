const mysql = require('mysql');

const db_host = 'localhost';

const db_user = 'ethereum';
const db_pass = '';
const db_name = 'ethereum';

let cnt_block = 0, cnt_tx = 0;
let running = false;

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
  const batchsize = 100;
  const commit_period = 1000;
  const log_period = 1000;
  for (let i = from; i < to; i+=batchsize) {
    let query = await mysql_query(conn, "SELECT `blocknumber`, `hash`, `input`, `from`, `to` FROM `transactions` WHERE `blocknumber`>=? AND `blocknumber`<?;", [i, i+batchsize]);
    cnt_block+=batchsize;
    if (query.length !== 0) {
      for (let j = 0; j < query.length; j++) {
        try {
          let from = Buffer.from(query[j].from).toString('hex');
          if (query[j].to !== null) {
            let to = Buffer.from(query[j].to).toString('hex');
            if (from === to) {
              await add_account_tx(from, query[j].blocknumber, 2);
            } else {
              await add_account_tx(from, query[j].blocknumber, 0);
              await add_account_tx(to, query[j].blocknumber, 1);
            }
          } else {
            await add_account_tx(from, query[j].blocknumber, 3);
          }
          cnt_tx++;
        } catch {
          console.log('Error blk #%d, j #%d', query[j].blocknumber, j);
        }
      }
    }
    if (i % log_period === 0) {
      let ms = new Date() - start;
      console.error('Blk height: %d, Blkn: %d(%d/s), Txn: %d(%d/s), Time: %dms', i, cnt_block, (cnt_block/ms*1000).toFixed(2), cnt_tx, (cnt_tx/ms*1000).toFixed(2), ms);
    }
    if (i % commit_period === 0) {
      await flush_accounts();
    }
  }
  await flush_accounts();
  conn.end();
  running = false;
}

async function add_account_tx (address, blocknumber, type) {
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
        balance: query[0].balance,
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
        firsttx: blocknumber,
        lasttx: blocknumber,
        balance: null,
        minedblockn: 0,
        minedunclen: 0,
        _type: 0,
      }
    }
  }

  if (cache[address].firsttx == null) {
    cache[address].firsttx = blocknumber;
  }

  cache[address].txn += 1;
  if (type === 0) {
    cache[address].sent += 1;
  } else if (type === 1) {
    cache[address].received += 1;
  } else if (type === 2) {
    cache[address].sent += 1;
    cache[address].received += 1;
  } else if (type === 3) {
    cache[address].sent += 1;
    cache[address].contract += 1;
  }
  cache[address].lasttx = blocknumber;
}

async function flush_accounts () {
  let cnt = 0;
  await conn.beginTransaction();
  for (let i in cache) {
    insert_account_batch(cache[i].id, i, cache[i].txn, cache[i].sent, cache[i].received, cache[i].contract, cache[i].firsttx, cache[i].lasttx, cache[i].balance, cache[i].minedblockn, cache[i].minedunclen, cache[i]._type);
    cnt++;
  }
  try {
    console.log('Commiting %d accounts...', cnt);
    await conn.commit();
    cache = {};
  } catch (err) {
    console.log('Error flushing', i);
    try {
      await conn.rollback();
    } catch (err) {
      console.log('MariaDB error');
    }
    conn = await mariadb.createConnection({host: db_host, user: db_user, password: db_pass, database: db_name});
  }
}

async function insert_account_batch (id, address, txn, sent, received, contract, firsttx, lasttx, balance, minedblockn, minedunclen, _type) {
  try {
    if (id === null) {
      let addr = Buffer.from(address, 'hex');
      mysql_query(conn, "INSERT INTO `accounts` (`address`, `txn`, `sent`, `received`, `contract`, `firsttx`, `lasttx`, `balance`, `minedblockn`, `minedunclen`, `_type`) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);", [addr, txn, sent, received, contract, firsttx, lasttx, balance, minedblockn, minedunclen, _type]);
    } else {
      mysql_query(conn, "UPDATE `accounts` SET `txn`=?, `sent`=?, `received`=?, `contract`=?, `firsttx`=?, `lasttx`=? WHERE `id`=?;", [txn, sent, received, contract, firsttx, lasttx, id]);
    }
  } catch (err) {
    console.log(err);
    let addr = Buffer.from(address, 'hex');
    console.log('Error insertion address ', addr);
  }
}


run(0, 15000000);
