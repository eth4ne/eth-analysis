const mysql = require('mysql');

const Web3 = require('web3');
const net = require('net');
const { exit } = require('process');

const db_host = 'localhost';

const db_user = 'ethereum';
const db_pass = '';
const db_name = 'ethereum';

const geth_ipc_path = '/ethereum/geth-fast/geth.ipc';

let cnt_account = 0;
let running = false;

let start = new Date();

function sleep(ms) {
  return new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
}

function connect_web3() {
  return new Web3(geth_ipc_path, net);
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

//type 0: EoA or CA (first appears in Tx)
//type 1: CA (null or not null), Deployed from EoA
//type 2: Null contract, deployed from EoA
//type 3: CA, not deployed from EoA
//type 4: Null contract or EoA
//type 5: CA (not null), Deployed from EoA

async function run(from, to) {
  conn = await mysql.createConnection({host: db_host, user: db_user, password: db_pass, database: db_name});
  await conn.connect();
  const batchsize = 1;
  const commit_period = 1000;
  const log_period = 100;
  let query = await mysql_query(conn, "SELECT COUNT(*) AS `count` FROM `accounts`;");
  let count = query[0].count;
  let web3 = connect_web3();
  for (let i = 0; i < count; i+=batchsize) {
    let query = await mysql_query(conn, "SELECT * FROM `accounts` LIMIT ?, ?;", [i, batchsize]);
    if (query.length !== 0) {
      for (let j = 0; j < query.length; j++) {
        let address = '0x' + Buffer.from(query[j].address).toString('hex');
        try {
          let balance = await web3.eth.getBalance(address);
          //mysql_query(conn, "UPDATE `accounts` SET `balance`=? WHERE `id`=?;", [balance, query[j].id]);
          console.log("Account " + address + ": " + balance);
          //exit();
          cnt_account++;
        } catch (e) {
          console.log('Error account ' + address);
        }
      }
    }
    if (i % log_period === 0) {
      let ms = new Date() - start;
      console.error('Accountn: %d(%d/s), Time: %dms', cnt_account, (cnt_account/ms*1000).toFixed(2), ms);
    }
  }
  conn.end();
  running = false;
}

run(0, 14000000);
