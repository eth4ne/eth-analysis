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

emptystorageroot = 'pty'
emptycodehash = 'pty'

#state operation type
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
#17: initial alloc

#tx type
#0: transfer (balance)
#1: failed transfer
#3: failed (not classified)
#4: contract deploy
#5: failed contract deploy
#6: contract call
#7: failed contract call

#type 0: EoA or CA (first appears in Tx)
#type 1: CA (null or not null), Deployed from EoA
#type 2: Null contract, deployed from EoA
#type 3: CA, not deployed from EoA
#type 4: EoA, may include null contract (transfer or write from CA)
#type 5: CA (not null), deployed from EoA
#type 6: EoA, first appears in Tx or contract write
#type 7: CA (transfer or write from CA)
#type 9: CA, first appears in Tx, read or presale
#type 10: EoA or CA (first appears as read in state access)
#type 11: Eoa or CA (first appears in presale)

def run(_from, _to):
  conn = conn_mariadb(db_host, db_user, db_pass, db_name)
  cursor = conn.cursor()
  start = time.time()
  cnt_block = 0
  cnt_tx = 0
  cnt_slot = 0
  cnt_state = 0
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
          miner_codehash = miner[3].split(':')[1][2:]
          miner_storageroot = miner[4].split(':')[1][2:]
          insert_miner(cursor, blocknumber, miner_address, miner_nonce, miner_balance, miner_codehash, miner_storageroot)

        if type == 'Uncle':
          uncle = data.split('\n')
          uncle_address = uncle[0].split(':0x')[1].lower()
          uncle_nonce = uncle[1].split(':')[1]
          uncle_balance = uncle[2].split(':')[1]
          uncle_codehash = uncle[3].split(':')[1][2:]
          uncle_storageroot = uncle[4].split(':')[1][2:]
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
                write_data['codehash'] = val.split(':')[1][2:]
              elif key == 'Code':
                write_data['code'] = val.split(':')[1]
                cacode = val.split(':')[1]
              elif key == 'StorageRoot':
                write_data['storageroot'] = val.split(':')[1][2:]
              elif key == 'Storage':
                pass
              elif key == 'slot':
                cnt_slot += 1
                write_data['slotlogs'].append({
                  'hash': val.split(',value:0x')[0].split(':0x')[1],
                  'value': val.split(',value:0x')[1]
                })
            writes.append(write_data)
          if txtype == 'Transfer':
            txclass = 0
          elif txtype == 'Failed_transfer':
            txclass = 1
          elif txtype == 'Failed_contractdeploy':
            txclass = 5
          elif txtype == 'Failed_contractcall':
            txclass = 7
          elif txtype == 'ContractDeploy':
            txclass = 4
          elif txtype == 'ContractCall':
            txclass = 6
          
          block_txs_read.append({
            'index': block_tx_table[txhash]['index'],
            'hash': txhash,
            'type': txtype,
            'reads': reads,
            'writes': writes,
            'deployedca': deployedca,
            'cacode': cacode,
            'txclass': txclass
          })
          
      block_txs_sorted = sorted(block_txs_read, key=lambda x: x['index'])

      for tx in block_txs_sorted:
        if tx['type'] == 'Transfer':
          type_value = 8
        elif tx['type'][:6] == 'Failed':
          type_value = 10
        elif tx['type'] == 'ContractCall':
          type_value = 12
        elif tx['type'] == 'ContractDeploy':
          type_value = 14
          update_contract(cursor, deployedca, cacode)
        else:
          print(tx['type'])
          exit()
        update_tx(cursor, tx['hash'], tx['txclass'])
        for read in tx['reads']:
          account = find_account(cursor, read['address'])
          if account == None:
            insert_account(cursor, read['address'], blocknumber, 10)
          insert_state(cursor, blocknumber, read['address'], None, None, None, None, tx['index'], type_value)
          cnt_state += 1
        for write in tx['writes']:
          account = find_account(cursor, write['address'])
          if account == None:
            if write['code'] == None:
              insert_account(cursor, write['address'], blocknumber, 4)
            else:
              insert_account(cursor, write['address'], blocknumber, 7)
              insert_contract(cursor, write['address'], tx['hash'], write['code'])
          elif account['_type'] == 0 or account['_type'] == 10 or account['_type'] == 11:
            if write['code'] == None:
              update_account_type(cursor, write['address'], 6)
            else:
              update_account_type(cursor, write['address'], 9)
          insert_state(cursor, blocknumber, write['address'], write['nonce'], write['balance'], write['codehash'], write['storageroot'], tx['index'], type_value+1)
          if len(write['slotlogs']) > 0:
            state = get_latest_state(cursor)
            for slot in write['slotlogs']:
              insert_slot(cursor, state['id'], write['address'], slot['hash'], slot['value'])
      
      if blocknumber % 2000 == 0:
        conn.commit()
        seconds = time.time() - start
        print('#{}, Blkn: {}({:.2f}/s), Txn: {}({:.2f}/s), Staten: {}({:.2f}/s), Slotn: {}({:.2f}/s), Time: {}ms'.format(blocknumber, cnt_block, cnt_block/seconds, cnt_tx, cnt_tx/seconds, cnt_state, cnt_state/seconds, cnt_slot, cnt_slot/seconds, int(seconds*1000)))
    print('Indexed {}'.format(filename))

def get_latest_state(cursor):
  sql = "SELECT * FROM `states` ORDER BY `id` DESC LIMIT 1;"
  cursor.execute(sql)
  result = cursor.fetchone()
  return result

def insert_slot(cursor, stateid, address, slot, slotvalue):
  sql = "SELECT * FROM `addresses` WHERE `address`=UNHEX(%s);"
  cursor.execute(sql, (address,))
  result = cursor.fetchone()
  if result == None:
    sql = "INSERT INTO `addresses` SET `address`=UNHEX(%s);"
    cursor.execute(sql, (address,))
    sql = "SELECT * FROM `addresses` WHERE `address`=UNHEX(%s);"
    cursor.execute(sql, (address,))
    result = cursor.fetchone()
  address_id = result['id']

  sql = "SELECT * FROM `slots` WHERE `slot`=UNHEX(%s);"
  cursor.execute(sql, (slot,))
  result = cursor.fetchone()
  if result == None:
    sql = "INSERT INTO `slots` SET `slot`=UNHEX(%s);"
    cursor.execute(sql, (slot,))
    sql = "SELECT * FROM `slots` WHERE `slot`=UNHEX(%s);"
    cursor.execute(sql, (slot,))
    result = cursor.fetchone()
  slot_id = result['id']

  sql = "INSERT INTO `slotlogs` (`stateid`, `address_id`, `slot_id`, `slotvalue`) VALUES (%s, %s, %s, UNHEX(%s));"
  cursor.execute(sql, (stateid, address_id, slot_id, slotvalue))

def update_contract(cursor, address, code):
  sql = "UPDATE `contracts` SET `code`=UNHEX(%s) WHERE `address`=UNHEX(%s);"
  cursor.execute(sql, (code, address)) 

def update_tx(cursor, txhash, txclass):
  sql = "UPDATE `transactions` SET `class`=%s WHERE `hash`=UNHEX(%s);"
  cursor.execute(sql, (txclass, txhash))

def update_account_type(cursor, address, type):
  sql = "UPDATE `accounts` SET `_type`=%s WHERE `address`=UNHEX(%s);"
  cursor.execute(sql, (type, address))

def insert_state(cursor, blocknumber, address, nonce, balance, codehash, storageroot, txindex, type_value):
  sql = "SELECT * FROM `addresses` WHERE `address`=UNHEX(%s);"
  cursor.execute(sql, (address,))
  result = cursor.fetchone()
  if result == None:
    sql = "INSERT INTO `addresses` SET `address`=UNHEX(%s);"
    cursor.execute(sql, (address,))
    sql = "SELECT * FROM `addresses` WHERE `address`=UNHEX(%s);"
    cursor.execute(sql, (address,))
    result = cursor.fetchone()
  address_id = result['id']

  if codehash == emptycodehash and storageroot == emptystorageroot:
    sql = "INSERT INTO `states` (`blocknumber`, `type`, `address_id`, `nonce`, `balance`, `codehash`, `storageroot`, `txindex`) VALUES (%s, %s, %s, %s, %s, NULL, NULL, %s);"
    cursor.execute(sql, (blocknumber, type_value, address_id, nonce, balance, txindex))
  elif codehash == emptycodehash:
    sql = "INSERT INTO `states` (`blocknumber`, `type`, `address_id`, `nonce`, `balance`, `codehash`, `storageroot`, `txindex`) VALUES (%s, %s, %s, %s, %s, NULL, UNHEX(%s), %s);"
    cursor.execute(sql, (blocknumber, type_value, address_id, nonce, balance, storageroot, txindex))
  elif storageroot == emptystorageroot:
    sql = "INSERT INTO `states` (`blocknumber`, `type`, `address_id`, `nonce`, `balance`, `codehash`, `storageroot`, `txindex`) VALUES (%s, %s, %s, %s, %s, UNHEX(%s), NULL, %s);"
    cursor.execute(sql, (blocknumber, type_value, address_id, nonce, balance, codehash, txindex))
  else:
    sql = "INSERT INTO `states` (`blocknumber`, `type`, `address_id`, `nonce`, `balance`, `codehash`, `storageroot`, `txindex`) VALUES (%s, %s, %s, %s, %s, UNHEX(%s), UNHEX(%s), %s);"
    cursor.execute(sql, (blocknumber, type_value, address_id, nonce, balance, codehash, storageroot, txindex))

def insert_miner(cursor, blocknumber, address, nonce, balance, codehash, storageroot):
  sql = "SELECT * FROM `addresses` WHERE `address`=UNHEX(%s);"
  cursor.execute(sql, (address,))
  result = cursor.fetchone()
  if result == None:
    sql = "INSERT INTO `addresses` SET `address`=UNHEX(%s);"
    cursor.execute(sql, (address,))
    sql = "SELECT * FROM `addresses` WHERE `address`=UNHEX(%s);"
    cursor.execute(sql, (address,))
    result = cursor.fetchone()
  address_id = result['id']

  if codehash == emptycodehash and storageroot == emptystorageroot:
    sql = "INSERT INTO `states` (`blocknumber`, `type`, `address_id`, `nonce`, `balance`, `codehash`, `storageroot`) VALUES (%s, %s, %s, %s, %s, NULL, NULL);"
    cursor.execute(sql, (blocknumber, 1, address_id, nonce, balance))
  elif codehash == emptycodehash:
    sql = "INSERT INTO `states` (`blocknumber`, `type`, `address_id`, `nonce`, `balance`, `codehash`, `storageroot`) VALUES (%s, %s, %s, %s, %s, NULL, UNHEX(%s));"
    cursor.execute(sql, (blocknumber, 1, address_id, nonce, balance, storageroot))
  elif storageroot == emptystorageroot:
    sql = "INSERT INTO `states` (`blocknumber`, `type`, `address_id`, `nonce`, `balance`, `codehash`, `storageroot`) VALUES (%s, %s, %s), %s, %s, UNHEX(%s), NULL);"
    cursor.execute(sql, (blocknumber, 1, address_id, nonce, balance, codehash))
  else:
    sql = "INSERT INTO `states` (`blocknumber`, `type`, `address_id`, `nonce`, `balance`, `codehash`, `storageroot`) VALUES (%s, %s, %s, %s, %s, UNHEX(%s), UNHEX(%s));"
    cursor.execute(sql, (blocknumber, 1, address_id, nonce, balance, codehash, storageroot))

def insert_uncle(cursor, blocknumber, address, nonce, balance, codehash, storageroot):
  sql = "SELECT * FROM `addresses` WHERE `address`=UNHEX(%s);"
  cursor.execute(sql, (address,))
  result = cursor.fetchone()
  if result == None:
    sql = "INSERT INTO `addresses` SET `address`=UNHEX(%s);"
    cursor.execute(sql, (address,))
    sql = "SELECT * FROM `addresses` WHERE `address`=UNHEX(%s);"
    cursor.execute(sql, (address,))
    result = cursor.fetchone()
  address_id = result['id']

  if codehash == emptycodehash and storageroot == emptystorageroot:
    sql = "INSERT INTO `states` (`blocknumber`, `type`, `address_id`, `nonce`, `balance`, `codehash`, `storageroot`) VALUES (%s, %s, %s, %s, %s, NULL, NULL);"
    cursor.execute(sql, (blocknumber, 3, address_id, nonce, balance))
  elif codehash == emptycodehash:
    sql = "INSERT INTO `states` (`blocknumber`, `type`, `address_id`, `nonce`, `balance`, `codehash`, `storageroot`) VALUES (%s, %s, %s, %s, %s, NULL, UNHEX(%s));"
    cursor.execute(sql, (blocknumber, 3, address_id, nonce, balance, storageroot))
  elif storageroot == emptystorageroot:
    sql = "INSERT INTO `states` (`blocknumber`, `type`, `address_id`, `nonce`, `balance`, `codehash`, `storageroot`) VALUES (%s, %s, %s, %s, %s, UNHEX(%s), NULL);"
    cursor.execute(sql, (blocknumber, 3, address_id, nonce, balance, codehash))
  else:
    sql = "INSERT INTO `states` (`blocknumber`, `type`, `address_id`, `nonce`, `balance`, `codehash`, `storageroot`) VALUES (%s, %s, %s, %s, %s, UNHEX(%s), UNHEX(%s);"
    cursor.execute(sql, (blocknumber, 3, address_id, nonce, balance, codehash, storageroot))
  

def insert_account(cursor, address, blocknumber, type):
  sql = "INSERT INTO `accounts` (`address`, `txn`, `sent`, `received`, `contract`, `firsttx`, `lasttx`, `minedblockn`, `minedunclen`, `_type`) VALUES (UNHEX(%s), %s, %s, %s, %s, %s, %s, %s, %s, %s);"
  cursor.execute(sql, (address, 0, 0, 0, 0, blocknumber, blocknumber, 0, 0, type))

def insert_contract(cursor, address, creationtx, code):
  sql = "INSERT INTO `contracts` (`address`, `creationtx`, `code`) VALUES (UNHEX(%s), UNHEX(%s), UNHEX(%s));"
  cursor.execute(sql, (address, creationtx, code))

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
  
def find_account(cursor, address):
  sql = "SELECT * FROM `accounts` WHERE `address`=UNHEX(%s);"
  cursor.execute(sql, (address,))
  result = cursor.fetchone()
  return result

run(start_block, end_block)