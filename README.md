## Ethereum on-chain data analysis

* [ethereum.sql](ethereum.sql)
  * A SQL template to initialize the DB structure.

* [block_tx_contract.js](block_tx_contract.js)
  * A node.js script to index block/uncle/transaction/contract DB into MariaDB from geth, as ```blocks```, ```uncles```, ```transactions```, ```contracts``` table.
  * Includes stationkeeper functionality, which keep track the latest block and index them.

* [account.js](account.js)
  * A nods.js script to iterate through all records in the ```transactions``` table, and records 1st/last appearance on the chain of all accounts as ```accounts``` table.

* [miner_block.js](miner_block.js), [miner_uncle.js](miner_uncle.js)
  * Node.js scripts to iterate through the ```blocks``` and ```uncles``` table to count mined blocks and uncles for every account.

* [restorelist.js](restorelist.js)
  * A node.js script to look up through the tx record and fetch the list of accounts to be restored per block.

* [restorelist_all_from_states.js](restorelist_all_from_states.js)
  * A node.js script to look up through the state write record fetch the list of accounts to be restored per block, according to tx record.
  * Arguments
  <pre>
  node restorelist_all_from_states.js <i>epoch</i> <i>block_start</i> <i>block_end</i> <i>output_file_name</i>
  </pre>

* [state_slot_init.py](state_slot_init.py)
  * Initialize state access DB and slot log DB.

* [txsubstate.py](txsubstate.py)
  * Parse dumped txsubstate file and index into the DB.

* [wipe.py](wipe.py)
  * DB wiper.

* [frontier.json](frontier.json)
  * The original genesis.json for ethereum mainnet.

### Script requirements
* Node.js
  * MySQL
  * MariaDB
  * Web3.js
  * argparse
* Python 3
  * PyMySQL
  * web3.py

### DB structure and relationships

* TODO

### Setup the DB
* Install the requirements.
```sh
$ pip3 install pymysql web3
```
* Import the database scheme
  * Asseme that DB user is *user* and DB name is *ethereum*.
```sh
$ mysql -u user ethereum < ethereum.sql
```

#### Index tx state/slot update logs
* Insert the state update logs into the DB.
  * Assume that the state update logs are created for every 1000 block interval from the first to 10M blocks.
```sh
$ python3 txsubstate.py -s 1 -e 10000000 -d ./txsubstate -i 1000
```

#### Index blocks, uncles and tx receipts
* Fully sync the [Geth](https://github.com/ethereum/go-ethereum) client up to the latest block, by whatever method. (snap, full, full archive)
* Index block, uncles and tx receipts
  * Set ```geth_ipc_path``` and ```db_socket```, ```db_user```, ```db_pass``` properly before running the code below.
```sh
$ node block_tx_contract.js
```