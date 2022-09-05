const mysql = require('mysql');
const { exit } = require('process');

const db_host = 'localhost';

const db_user = 'ethereum';
const db_pass = '';
const db_name = 'ethereum';

let cnt_block = 0, cnt_tx = 0;
let running = false;
const query_size = 200;
let totalaccounts = 0;

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
  conn = await mysql.createConnection({host: db_host, user: db_user, password: db_pass, database: db_name, multipleStatements: true});
  await conn.connect();
  const batchsize = 100;
  const commit_period = 20000;
  const log_period = 2000;
  for (let i = from; i < to; i+=batchsize) {
    let query = await mysql_query(conn, "SELECT `blocknumber`, `from`, `to` FROM `transactions` WHERE `blocknumber`>=? AND `blocknumber`<?;", [i, i+batchsize]);
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
    if (i % commit_period === 0 && Object.keys(cache).length !== 0) {
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
  let accounts_insert = [];
  let accounts_update = [];
  for (let i in cache) {
    if (cache[i].id === null) {
      let address = Buffer.from(i, 'hex');
      accounts_insert.push([address, cache[i].txn, cache[i].sent, cache[i].received, cache[i].contract, cache[i].firsttx, cache[i].lasttx, cache[i].minedblockn, cache[i].minedunclen, cache[i]._type]);
    } else {
      accounts_update.push(cache[i].txn, cache[i].sent, cache[i].received, cache[i].contract, cache[i].firsttx, cache[i].lasttx, cache[i].id);
    }
    cnt++;
  }
  if (accounts_insert.length > 0) await insert_account_many(accounts_insert);
  if (accounts_update.length > 0) await update_account_many(accounts_update);
  try {
    console.error('Commiting %d accounts...', cnt);
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

async function insert_account_many (accounts) {
  try {
    totalaccounts += accounts.length;
    console.error('Insert %d accounts (%d total)', accounts.length, totalaccounts);
    for (let i = 0; i < accounts.length; i+=query_size) {
      await mysql_query(conn, "INSERT INTO `accounts` (`address`, `txn`, `sent`, `received`, `contract`, `firsttx`, `lasttx`, `minedblockn`, `minedunclen`, `_type`) VALUES ?", [accounts.slice(i, i+query_size)]);
    }
  } catch (err) {
    console.log(err);
    console.log('Error');
  }
}

async function update_account_many (accounts) {
  try {
    console.error('Update %d accounts', accounts.length/7);
    for (let i = 0; i < accounts.length; i+=query_size*7) {
      let query = "UPDATE `accounts` SET `txn`=?, `sent`=?, `received`=?, `contract`=?, `firsttx`=?, `lasttx`=? WHERE `id`=?;";
      let update = accounts.slice(i, i+query_size*7)
      query = query.repeat(update.length/7);
      await mysql_query(conn, query, update);
    }
  } catch (err) {
    console.log(err);
    console.log('Error');
  }
}

run(0, 15000000);
