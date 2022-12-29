//--max_old_space_size=4096

const mariadb = require('mariadb');
const fs = require('fs');
const { ArgumentParser } = require('argparse');

const parser = new ArgumentParser({ description: 'Restore list generator' })

const db_host = 'localhost';

const db_user = 'ethereum';
const db_pass = '1234';
const db_name = 'ethereum';

let epoch_inactivate_every = 40320;
let epoch_inactivate_older_than = 40320;
let block_start = 1;
let block_end = 100000;
let output_restore = 'restore.json';
let log_period = 10000;

let cnt_block = 0, cnt_state = 0;

let start = new Date();

let cache_account = {};
let cache_block = {};

let restore = {};

let conn = null;

parser.add_argument('-s', '--start', {metavar: 'N', type: 'int', nargs: '?', default: 1, help: 'block height to start (inclusive)'})
parser.add_argument('-e', '--end', {metavar: 'N', type: 'int', nargs: '?', default: 1000000, help: 'block height to end (inclusive)'})
parser.add_argument('-i', '--inactivate-every', {metavar: 'N', type: 'int', nargs: '?', default: 100000, help: 'run inactivation every N blocks'})
parser.add_argument('-t', '--inactivate-older-than', {metavar: 'N', type: 'int', nargs: '?', default: 100000, help: 'inactivate addresses older than N blocks'})
parser.add_argument('-o', '--output-filename', {metavar: 'output.json', type: 'str', nargs: '?', default: 'output.json', help: 'output to file'})
parser.add_argument('-l', '--log-every', {metavar: 'output.json', type: 'int', nargs: '?', default: 10000, help: 'print log every N blocks'})

let args = parser.parse_args();

block_start = args.start;
block_end = args.end;
epoch_inactivate_every = args.inactivate_every;
epoch_inactivate_older_than = args.inactivate_older_than;
output_restore = args.output_filename;
log_period = args.log_every;

async function run(from, to) {
  conn = await mariadb.createConnection({host: db_host, user: db_user, password: db_pass, database: db_name});
  let batch_size = 100;
  for (let i = from; i <= to; i+=batch_size) {
    let query = await conn.query("SELECT `address_id`, `blocknumber`, `type` FROM `states` WHERE `blocknumber`>=? AND `blocknumber`<?;", [i, Math.min(i+batch_size, to+1)]);
    let result = Array.from(Array(batch_size), () => {
      return [];
    });
    for (let j = 0; j < query.length; ++j) {
      result[query[j].blocknumber-i].push(query[j]);
    }
    query = null;
    if (global.gc) global.gc();
    for (let k = 0; k < batch_size; ++k) {
      let cache_block_tmp = {};
      for (let j in result[k]) {
        try {
          let addr = result[k][j].address_id;
          if (addr in cache_account) {
            let height_positive = cache_account[addr] >= 0 ? cache_account[addr] : -cache_account[addr];
            if (result[k][j].type & 1 == 1 && cache_account[addr] >= i+k - epoch_inactivate_every - 1 - epoch_inactivate_older_than && cache_account[addr] >= 0)
            delete cache_block[height_positive][addr];
          }
          update_account(addr, i+k, result[k][j].type & 1);
          if (addr in cache_account) cache_block_tmp[addr] = 1;
          cnt_state++;
        } catch {
          console.error('Error blk #%d, j #%d', result[k][j].blocknumber, j);
        }
      }

      cache_block[i+k] = cache_block_tmp;

      //simulate inactivation
      if ((i+k + 1 - from + epoch_inactivate_older_than) % epoch_inactivate_every == 0) {
        for (let j = 0; j < epoch_inactivate_every; ++j) {
          let block_removal = i+k - j - epoch_inactivate_older_than;
          if ((block_removal) in cache_block) {
            for (let l in cache_block[block_removal]) {
              if ((!(cache_account[l] & 0x80000000)) && cache_account[l] <= i+k - epoch_inactivate_older_than) {
                cache_account[l] = block_removal ^ 0x80000000;
              }
            }
            delete cache_block.block_removal;
          }
        }
      }
      if ((i+k) % log_period === 0) {
        let ms = new Date() - start;
        console.error('Blk height: %d, Blkn: %d(%d/s), Staten: %d(%d/s), Time: %dms', i+k, cnt_block, (cnt_block/ms*1000).toFixed(2), cnt_state, (cnt_state/ms*1000).toFixed(2), ms);
      }
    }
    cnt_block = Math.min(cnt_block+batch_size, to);
  }

  cache_account = null;

  console.error('Processing restore list');

  for (let i in restore) {
    for (let j in restore[i]) {
      let query = await conn.query("SELECT `address` FROM `addresses` WHERE `id`=?;", [restore[i][j]]);
      if (query.length > 0) restore[i][j] = '0x' + Buffer.from(query[0].address).toString('hex');
      else console.log(restore[i][j]);
    }
  }

  conn.end();

  let restore_json = JSON.stringify(restore, null, "  ");
  fs.writeFileSync(output_restore, restore_json);

  console.error('Saved result as ' + output_restore);

  running = false;
}

async function update_account (address, blocknumber, type) {
  if (type === 0) { //read
    if (address in cache_account && (cache_account[address] & 0x80000000)) {
      if (blocknumber in restore) {
        restore[blocknumber].push(address);
      } else {
        restore[blocknumber] = [address];
      }
      cache_account[address] = blocknumber;
    }
  } else if (type === 1) { //write
    if (address in cache_account && (cache_account[address] & 0x80000000)) {
      if (blocknumber in restore) {
        restore[blocknumber].push(address);
      } else {
        restore[blocknumber] = [address];
      }
    }
    cache_account[address] = blocknumber;
  }
}

run(block_start, block_end);
