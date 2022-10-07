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

* [restorelist_all_from_accounts.js](restorelist_all_from_accounts.js)
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

### Script requirements
* Node.js
  * MySQL
  * MariaDB
  * Web3.js
  * argparse
* Python 3
  * PyMySQL

### DB structure and relationships

