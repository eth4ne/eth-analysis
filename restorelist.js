//--max_old_space_size=4096

const mysql = require('mysql');

const db_host = 'localhost';

const db_user = 'ethereum';
const db_pass = '1234';
const db_name = 'ethereum';

const epoch = 40320;
const block_start = 7000000;
const block_end = 7300000;

const log_period = 1000;

let cnt_block = 0, cnt_tx = 0;

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

let cache_account = {};
let cache_block = {};

let conn = null;

async function run(from, to) {
  conn = await mysql.createConnection({host: db_host, user: db_user, password: db_pass, database: db_name});
  await conn.connect();
  for (let i = from; i < to; i+=1) {
    let query = await mysql_query(conn, "SELECT `blocknumber`, `hash`, `input`, `from`, `to` FROM `transactions` WHERE `blocknumber`=?;", [i]);
    let cache_block_tmp = {};
    cnt_block+=1;
    if (query.length !== 0) {
      for (let j = 0; j < query.length; j++) {
        try {
          let from = Buffer.from(query[j].from).toString('hex');
          if (query[j].to !== null) {
            let to = Buffer.from(query[j].to).toString('hex');
            if (from === to) {
              update_account(from, query[j].blocknumber);
              cache_block_tmp[from] = 1;
            } else {
              update_account(from, query[j].blocknumber);
              update_account(to, query[j].blocknumber);
              cache_block_tmp[from] = 1;
              cache_block_tmp[to] = 1;
            }
          } else {
            update_account(from, query[j].blocknumber);
            cache_block_tmp[from] = 1;
          }
          cnt_tx++;
        } catch {
          console.error('Error blk #%d, j #%d', query[j].blocknumber, j);
        }
      }
    }
    cache_block[i] = cache_block_tmp;

    if ((i - from) % epoch == 0) {
      for (let j = 0; j < epoch; j++) {
        let block_removal = i - j - epoch;
        if (block_removal in cache_block) {
          for (let j in cache_block[block_removal]) {
            if (cache_account[j] == block_removal) {
              cache_account[j] = -block_removal;
            }
          }
          delete cache_block.block_removal;
        }
      }
    }
    if (i % log_period === 0) {
      let ms = new Date() - start;
      console.error('Blk height: %d, Blkn: %d(%d/s), Txn: %d(%d/s), Time: %dms', i, cnt_block, (cnt_block/ms*1000).toFixed(2), cnt_tx, (cnt_tx/ms*1000).toFixed(2), ms);
    }
  }
  conn.end();
  running = false;
}

async function update_account (address, blocknumber) {
  if (address in cache_account && cache_account[address] < 0) {
    console.log('Restore: 0x' + address + ' at #' + blocknumber + ' (last tx at #' + (-cache_account[address]) + ')');
  } 
  cache_account[address] = blocknumber;
}

run(block_start, block_end);
