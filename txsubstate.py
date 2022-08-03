import pymysql.cursors
import time

db_host = 'localhost'
db_user = 'ethereum'
db_pass = '' #fill in the MariaDB/MySQL password.
db_name = 'ethereum'

start_block = 1
end_block = 1000000
interval = 100000

conn_mariadb = lambda host, user, password, database: pymysql.connect(host=host, user=user, password=password, database=database, cursorclass=pymysql.cursors.DictCursor)

#type
#1: miner
#3: uncle
#8: read by transfer tx
#9: write by transfer tx
#10: read by failed tx
#11: write by failed tx
#12: read by contract call tx
#13: write by contract call tx
#14: read by contract deploy tx
#15: write by contract deploy tx


def run(_from, _to):
  conn = conn_mariadb(db_host, db_user, db_pass, db_name)
  cursor = conn.cursor()
  start = time.time()
  cnt_block = 0
  cnt_tx = 0
  cnt_slot = 0
  for blockheight in range(_from, _to, interval):
    filename = 'txsubstate/TxSubstate{}-{}.txt'.format(blockheight, blockheight+interval-1)
    f = open(filename, 'r')
    blocks = f.read().split('/')[1:]
    for block in blocks:
      blocknumber = int(block.split('\n')[0].split(':')[1])
      cnt_block += 1

      block_data = block.replace('\n\n  ', '\n/\n  ').split('\n\n')

      block_txs = select_txs(cursor, blocknumber)
      block_tx_table = {}
      block_txs_read = []

      for tx in block_txs:
        block_tx_table[tx['hash'].hex()] = {'index': tx['transactionindex'], 'to': tx['input']}

      for data in block_data:
        type = data.split(':')[0]
        if type == 'Miner':
          miner = data.split('\n')
          miner_address = miner[0].split(':0x')[1].lower()
          miner_nonce = miner[1].split(':')[1]
          miner_balance = miner[2].split(':')[1]
          miner_codehash = miner[3].split(':0x')[1]
          miner_storageroot = miner[4].split(':0x')[1]
          insert_miner(cursor, blocknumber, miner_address, miner_nonce, miner_balance, miner_codehash, miner_storageroot)

        if type == 'Uncle':
          uncle = data.split('\n')
          uncle_address = uncle[0].split(':0x')[1].lower()
          uncle_nonce = uncle[1].split(':')[1]
          uncle_balance = uncle[2].split(':')[1]
          uncle_codehash = uncle[3].split(':0x')[1]
          uncle_storageroot = uncle[4].split(':0x')[1]
          insert_uncle(cursor, blocknumber, uncle_address, uncle_nonce, uncle_balance, uncle_codehash, uncle_storageroot)

        if type == 'TxHash':
          tx_vals = data.split('\n\n')[0].split('\n')
          deployedca = None
          cacode = None
          for val in tx_vals:
            key = val.split(':')[0].lstrip()
            if key == 'TxHash':
              txhash = val.split(':0x')[1]
            elif key == 'Type':
              txtype = val.split(':')[1]
            elif key == 'From':
              pass
            elif key == 'To':
              pass
            elif key == 'DeployedCA':
              deployedca = val.split(':0x')[1].lower()
            
          cnt_tx += 1

          readlist = data.split('/')[1].split('\n')[2:-1]
          writelist = '\n'.join('/'.join(data.split('/')[2:]).split('\n')[2:]).split('\n/\n')
          reads = []
          writes = []
          
          for read in readlist:
            read_address = read.split(':0x')[1].lower()
            reads.append({'address': read_address})

          for write in writelist:
            write_vals = write.split('\n')
            write_address = write_vals[0].split(':0x')[1].lower()
            write_data =  {
              'address': write_address,
              'nonce': None,
              'balance': None,
              'codehash': None,
              'code': None,
              'storageroot': None,
              'slotlogs': []
            }
            for val in write_vals:
              key = val.split(':')[0].lstrip()
              if key == 'Nonce':
                write_data['nonce'] = val.split(':')[1]
              elif key == 'Balance':
                write_data['balance'] = val.split(':')[1]
              elif key == 'CodeHash':
                write_data['codehash'] = val.split(':0x')[1]
              elif key == 'Code':
                write_data['code'] = val.split(':')[1]
                cacode = val.split(':')[1]
              elif key == 'StorageRoot':
                write_data['storageroot'] = val.split(':0x')[1]
              elif key == 'Storage':
                pass
              elif key == 'slot':
                cnt_slot += 1
                write_data['slotlogs'].append({
                  'hash': val.split(',value:0x')[0].split(':0x')[1],
                  'value': val.split(',value:0x')[1]
                })
            writes.append(write_data)
          if len(block_tx_table[txhash]['to']) == 0:
            txtype = 'ContractDeploy'
          block_txs_read.append({
            'index': block_tx_table[txhash]['index'],
            'hash': txhash,
            'type': txtype,
            'reads': reads,
            'writes': writes,
            'deployedca': deployedca,
            'cacode': cacode
          })
          
      block_txs_sorted = sorted(block_txs_read, key=lambda x: x['index'])

      for tx in block_txs_sorted:
        if tx['type'] == 'Transfer':
          type_value = 8
        elif tx['type'] == 'Failed':
          type_value = 10
        elif tx['type'] == 'ContractCall':
          type_value = 12
        elif tx['type'] == 'ContractDeploy':
          type_value = 14
          update_contract(cursor, deployedca, cacode)
        else:
          print(tx['type'])
          exit()
        for read in tx['reads']:
          insert_state(cursor, blocknumber, read['address'], None, None, None, None, tx['hash'], type_value)
        for write in tx['writes']:
          insert_state(cursor, blocknumber, write['address'], write['nonce'], write['balance'], write['codehash'], write['storageroot'], tx['hash'], type_value+1)
          if len(write['slotlogs']) > 0:
            state = get_latest_state(cursor)
            for slot in write['slotlogs']:
              insert_slot(cursor, state['id'], write['address'], slot['hash'], slot['value'])
      
      if blocknumber % 2000 == 0:
        conn.commit()
        seconds = time.time() - start
        print('#{}, Blkn: {}({:.2f}/s), Txn: {}({:.2f}/s), Slotn: {}({:.2f}/s), Time: {}ms'.format(blocknumber, cnt_block, cnt_block/seconds, cnt_tx, cnt_tx/seconds, cnt_slot, cnt_slot/seconds, int(seconds*1000)))
    print('Indexed {}'.format(filename))

def get_latest_state(cursor):
  sql = "SELECT * FROM `states` ORDER BY `id` DESC LIMIT 1;"
  cursor.execute(sql)
  result = cursor.fetchone()
  return result

def insert_slot(cursor, stateid, address, slot, slotvalue):
  sql = "INSERT INTO `slotlogs` (`stateid`, `address`, `slot`, `slotvalue`) VALUES (%s, UNHEX(%s), UNHEX(%s), UNHEX(%s));"
  cursor.execute(sql, (stateid, address, slot, slotvalue))

def update_contract(cursor, address, code):
  sql = "UPDATE `contracts` SET `code`=UNHEX(%s) WHERE `address`=UNHEX(%s);"
  cursor.execute(sql, (code, address)) 

def insert_state(cursor, blocknumber, address, nonce, balance, codehash, storageroot, txhash, type_value):
  sql = "INSERT INTO `states` (`blocknumber`, `type`, `address`, `nonce`, `balance`, `codehash`, `storageroot`, `txhash`) VALUES (%s, %s, UNHEX(%s), %s, %s, UNHEX(%s), UNHEX(%s), UNHEX(%s));"
  cursor.execute(sql, (blocknumber, type_value, address, nonce, balance, codehash, storageroot, txhash))

def insert_miner(cursor, blocknumber, address, nonce, balance, codehash, storageroot):
  sql = "INSERT INTO `states` (`blocknumber`, `type`, `address`, `nonce`, `balance`, `codehash`, `storageroot`) VALUES (%s, %s, UNHEX(%s), %s, %s, UNHEX(%s), UNHEX(%s));"
  cursor.execute(sql, (blocknumber, 1, address, nonce, balance, codehash, storageroot))

def insert_uncle(cursor, blocknumber, address, nonce, balance, codehash, storageroot):
  sql = "INSERT INTO `states` (`blocknumber`, `type`, `address`, `nonce`, `balance`, `codehash`, `storageroot`) VALUES (%s, %s, UNHEX(%s), %s, %s, UNHEX(%s), UNHEX(%s));"
  cursor.execute(sql, (blocknumber, 3, address, nonce, balance, codehash, storageroot))

def select_txs(cursor, blocknumber):
  sql = "SELECT * FROM `transactions` WHERE `blocknumber`=%s;"
  cursor.execute(sql, (blocknumber,))
  result = cursor.fetchall()
  return result

def select_tx(cursor, txhash):
  sql = "SELECT * FROM `transactions` WHERE `hash`=UNHEX(%s);"
  cursor.execute(sql, (txhash,))
  result = cursor.fetchone()
  return result



run(start_block, end_block)