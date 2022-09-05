//--max_old_space_size=4096

const mysql = require('mysql');
const fs = require('fs');
const process = require('process');

const db_host = 'localhost';

const db_user = 'ethereum';
const db_pass = '';
const db_name = 'ethereum';

let epoch = 40320;
let block_start = 1;
let block_end = 100000;
let output_restore = 'restore.json';

const log_period = 1000;

let cnt_block = 0, cnt_state = 0;

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

let restore = {};

let conn = null;

let args = process.argv;
if (args.length >= 2) {
  block_start = parseInt(args[2]);
}
if (args.length >= 3) {
  block_end = parseInt(args[3]);
}
if (args.length >= 4) {
  epoch = parseInt(args[4]);
}
if (args.length >= 5) {
  output_restore = args[5];
}

async function run(from, to) {
  conn = await mysql.createConnection({host: db_host, user: db_user, password: db_pass, database: db_name});
  await conn.connect();
  for (let i = from; i <= to; i+=1) {
    //read, write
    let query = await mysql_query(conn, "SELECT `address`, `blocknumber`, `type` FROM `states` LEFT JOIN `addresses` ON `states`.`address_id`=`addresses`.`id` WHERE `blocknumber`=?;", [i]);
    let cache_block_tmp = {};
    cnt_block+=1;
    if (query.length !== 0) {
      for (let j = 0; j < query.length; j++) {
        try {
          let addr = Buffer.from(query[j].address).toString('hex');
          if (query[j].type % 2 == 0) { //read
            update_account(addr, i, 0);
          } else { //write
            update_account(addr, i, 1);
          }
          cache_block_tmp[addr] = 1;
          cnt_state++;
        } catch {
          console.error('Error blk #%d, j #%d', query[j].blocknumber, j);
        }
      }
    }

    cache_block[i] = cache_block_tmp;

    //simulate inactivation
    if ((i + 1 - from) % epoch == 0) {
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
      console.error('Blk height: %d, Blkn: %d(%d/s), Txn: %d(%d/s), Time: %dms', i, cnt_block, (cnt_block/ms*1000).toFixed(2), cnt_state, (cnt_state/ms*1000).toFixed(2), ms);
    }
  }
  conn.end();

  let restore_json = JSON.stringify(restore, null, "  ");
  fs.writeFileSync(output_restore, restore_json);

  console.error('Saved result as ' + output_restore);

  running = false;
}

async function update_account (address, blocknumber, type) {
  if (type == 0) { //read
    if (address in cache_account && cache_account[address] < 0) {
      //console.log('Restore: 0x' + address + ' at #' + blocknumber + ' (last tx at #' + (-cache_account[address]) + ')');
      if (blocknumber in restore) {
        restore[blocknumber].push('0x'+address);
      } else {
        restore[blocknumber] = ['0x'+address];
      }
      cache_account[address] = blocknumber;
    }
  } else if (type == 1) { //write
    if (address in cache_account && cache_account[address] < 0) {
      //console.log('Restore: 0x' + address + ' at #' + blocknumber + ' (last tx at #' + (-cache_account[address]) + ')');
      if (blocknumber in restore) {
        restore[blocknumber].push('0x'+address);
      } else {
        restore[blocknumber] = ['0x'+address];
      }
    }
    cache_account[address] = blocknumber;
  }
}

run(block_start, block_end);
