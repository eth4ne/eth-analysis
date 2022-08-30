import pymysql.cursors
import pymysql.err
import time

db_host = 'localhost'
db_user = 'ethereum'
db_pass = '' #fill in the MariaDB/MySQL password.
db_name = 'ethereum'

start_block = 1
end_block = 1100000
interval = 100000

commit_interval = 2000
log_interval = 2000
execute_interval = 2000

conn_mariadb = lambda host, user, password, database: pymysql.connect(host=host, user=user, password=password, database=database, cursorclass=pymysql.cursors.DictCursor)

emptystorageroot = 'pty'
emptycodehash = 'pty'

run_state = True
run_slot = True
run_contract = True
run_account = True
run_txtype = False

#state operation type
#1: miner
#3: uncle
#8: read by transfer tx
#9: write by transfer tx
#10: read by failed transfer tx
#11: write by failed transfer tx
#12: read by contract call tx
#13: write by contract call tx
#14: read by failed contract call tx
#15: write by failed contract call tx
#16: read by contract deploy tx
#17: write by contract deploy tx
#18: read by failed contract deploy tx
#19: write by failed contract deploy tx

#31: initial alloc


#tx type
#0: transfer (balance)
#1: failed transfer
#3: failed (not classified)
#4: contract deploy
#5: failed contract deploy
#6: contract call
#7: failed contract call

#account type (accounts table)
#type 0: Uncertain (EoA or CA, first appears as tx from or to)
#type 1: CA (deployed from EoA, parsed from transactionreceipt)

#account type (addresses table)
#type 4: Uncertain (EoA or CA, first appears as read in state access, includes contract failed to be deployed)
#type 5: Uncertain (EoA or CA, first appears as block or uncle miner)
#type 6: EoA (EoA or CA, first appears as write in state access)
#type 7: CA (null or not null), Deployed from EoA
#type 8: Uncertain (EoA or CA, first appears as block or uncle miner)
#type 9: CA (null or not null), Deployed from CA
#type 10: Uncertain (EoA or CA, presale)

slot_cache = {}
account_cache = {}

def run(_from, _to):
  conn = conn_mariadb(db_host, db_user, db_pass, db_name)
  cursor = conn.cursor()
  start = time.time()
  cnt_block = 0
  cnt_tx = 0
  cnt_slot = 0
  cnt_state = 0
  latest_state = get_latest_state(cursor)
  if latest_state == None:
    state_id = 0
  else:
    state_id = latest_state['id']
  state_updates = []
  slots = []
  for blockheight in range(_from, _to, interval):
    filename = 'txsubstate/TxSubstate{}-{}.txt'.format(blockheight, blockheight+interval-1)
    f = open(filename, 'r')
    blocks = f.read().split('/')[1:]
    for block in blocks:
      blocknumber = int(block.split('\n')[0].split(':')[1])
      cnt_block += 1

      txcount = block.count('!')
      for i in range(1, txcount+1):
        txbody = block.split('!')[i]
        txdata = txbody.split('@')[0].split('\n')[:-1]
        tx = {
          'index': i-1,
          'hash': None,
          'type': None,
          'from': None,
          'to': None,
          'deployedca': None,
        }
        for j in txdata:
          k = j.split(':')[0]
          v = j.split(':')[1]
          if k == 'TxHash':
            tx['hash'] = v[2:]
          elif k == 'Type':
            if v == 'Transfer':
              tx['type'] = 0
              state_type = 8
            elif v == 'Failed_transfer':
              tx['type'] = 1
              state_type = 10
            elif v == 'Failed_contractdeploy':
              tx['type'] = 5
              state_type = 18
            elif v == 'Failed_contractcall':
              tx['type'] = 7
              state_type = 14
            elif v == 'ContractDeploy':
              tx['type'] = 4
              state_type = 16
            elif v == 'ContractCall':
              tx['type'] = 6
              state_type = 12
            else:
              print('Unhandled txn type: {}'.format(v))
              exit()
          elif k == 'From':
            tx['from'] = v[2:]
          elif k == 'To':
            tx['to'] = v[2:]
          elif k == 'DeployedCA':
            tx['deployedca'] = v[2:]
        readlist = txbody.split('@')[1].split('#')[0].split('\n')[1:-1]
        for j in readlist:
          address = j.split(':')[1][2:].lower()
          if run_state == True:
            address_id = find_account_id(cursor, address)
            if address_id == None:
              address_id = insert_account(cursor, address, 4)
            state_update = prepare_state(blocknumber, address_id, None, None, None, None, tx['index'], state_type)
            state_updates.append(state_update)
            state_id += 1
            cnt_state += 1
            
        writelist = txbody.split('#')[1].split('$')[0].split('.')[1:]
        for j in writelist:
          write_data = j.split('\n')[:-1]
          write =  {
            'address': None,
            'nonce': None,
            'balance': None,
            'codehash': None,
            'code': None,
            'deployedbyca': False,
            'storageroot': None,
            'slotlogs': []
          }
          for ij in write_data:
            k = ij.split(':')[0]
            v = ij.split(':')[1]
            if k == 'address':
              write['address'] = v[2:]
            elif k == 'Deployedaddress':
              write['address'] = v[2:]
              write['deployedbyca'] = True
            elif k == 'Nonce':
              write['nonce'] = v
            elif k == 'Balance':
              write['balance'] = v
            elif k == 'CodeHash':
              write['codehash'] = v[2:]
            elif k == 'StorageRoot':
              write['storageroot'] = v[2:]
            elif k == 'Code':
              write['code'] = v
            elif k == 'Storage':
              pass
            elif k == 'slot':
              slot = {'slot': v.split(',')[0].split('0x')[1],'value': ij.split(',value:0x')[1]}
              write['slotlogs'].append(slot) 

          if run_state == True:        
            address_id = find_account_id(cursor, write['address'])
            if address_id == None:
              if write['code'] == None:
                address_id = insert_account(cursor, write['address'], 6)
              else:
                address_id = insert_account(cursor, write['address'], 7)
            state_update = prepare_state(blocknumber, address_id, write['nonce'], write['balance'], write['codehash'], write['storageroot'], tx['index'], state_type+1)
            state_updates.append(state_update)
            state_id += 1
            if run_slot == True:
              for ij in write['slotlogs']:
                slot_id = find_slot_id(cursor, ij['slot'])
                hexvalue = ij['value']
                if hexvalue == '0':
                  hexvalue = None
                else:
                  hexvalue = bytes.fromhex(hexvalue)
                slot = (state_id, address_id, slot_id, hexvalue)
                slots.append(slot)
                cnt_slot += 1
            cnt_state += 1

          if run_contract == True:
            if write['code'] != None:
              if write['deployedbyca'] == True:
                address_id = find_account_id(cursor, write['address'])
                if address_id == None:
                  address_id = insert_account(cursor, write['address'], 9)
                else:
                  update_account_type(cursor, address_id, 9)
                insert_contract(cursor, write['address'], tx['hash'], write['code'])
              else:
                if tx['deployedca'] == write['address']:
                  address_id = find_account_id(cursor, write['address'])
                  if address_id == None:
                    address_id = insert_account(cursor, write['address'], 7)
                  else:
                    update_account_type(cursor, address_id, 7)
                  insert_contract(cursor, write['address'], tx['hash'], write['code'])
                else:
                  print('Error: deployed ca and the address mismatch')
                  print('DeployedCA: {}, address: {}'.format(tx['deployedca'], write['address']))
          
          if run_account == True:
            if write['code'] == None:
              address_id = find_account_id(cursor, write['address'])
              if address_id == None:
                address_id = insert_account(cursor, write['address'], 6)
              
            #  exit()
        if run_txtype == True:
          update_tx(cursor, tx['hash'], tx['type'])
        cnt_tx += 1

      unclecount = block.count('^')

      for i in range(1, unclecount+1):
        uncle = block.split('^')[i].split('\n')[0:5]
        uncle_address = uncle[0].split(':0x')[1].lower()
        uncle_nonce = uncle[1].split(':')[1]
        uncle_balance = uncle[2].split(':')[1]
        uncle_codehash = uncle[3].split(':')[1][2:]
        uncle_storageroot = uncle[4].split(':')[1][2:]
        uncle_address_id = find_account_id(cursor, uncle_address)
        if uncle_address_id == None:
          uncle_address_id = insert_account(cursor, uncle_address, 8)
        #insert_uncle(cursor, blocknumber, uncle_address_id, uncle_nonce, uncle_balance, uncle_codehash, uncle_storageroot)
        state_update = prepare_state(blocknumber, uncle_address_id, uncle_nonce, uncle_balance, uncle_codehash, uncle_storageroot, None, 3)
        state_updates.append(state_update)
        state_id += 1

      miner = block.split('$')[1].split('\n')[0:5]
      miner_address = miner[0].split(':0x')[1].lower()
      miner_nonce = miner[1].split(':')[1]
      miner_balance = miner[2].split(':')[1]
      miner_codehash = miner[3].split(':')[1][2:]
      miner_storageroot = miner[4].split(':')[1][2:]
      miner_address_id = find_account_id(cursor, miner_address)
      if miner_address_id == None:
        miner_address_id = insert_account(cursor, miner_address, 8)
      state_update = prepare_state(blocknumber, miner_address_id, miner_nonce, miner_balance, miner_codehash, miner_storageroot, None, 1)
      state_updates.append(state_update)
      state_id += 1

      if blocknumber % execute_interval == 0:
        insert_state_batch(cursor, state_updates)
        state_id = cursor.lastrowid
        state_updates = []
        insert_slot_batch(cursor, slots)
        slots = []
      
      if blocknumber % commit_interval == 0:
        conn.commit()
      if blocknumber % log_interval == 0:
        seconds = time.time() - start
        print('#{}, Blkn: {}({:.2f}/s), Txn: {}({:.2f}/s), Staten: {}({:.2f}/s), Slotn: {}({:.2f}/s), Time: {}ms'.format(blocknumber, cnt_block, cnt_block/seconds, cnt_tx, cnt_tx/seconds, cnt_state, cnt_state/seconds, cnt_slot, cnt_slot/seconds, int(seconds*1000)))
    print('Indexed {}'.format(filename))

def get_latest_state(cursor):
  sql = "SELECT * FROM `states` ORDER BY `id` DESC LIMIT 1;"
  cursor.execute(sql)
  result = cursor.fetchone()
  return result

def find_account_id(cursor, address):
  if address in account_cache:
    return account_cache[address]
  address_bytes = bytes.fromhex(address)
  sql = "SELECT * FROM `addresses` WHERE `address`=%s;"
  cursor.execute(sql, (address_bytes,))
  result = cursor.fetchone()
  if result == None:
    return None
  else:
    result = result['id']
  account_cache[address] = result
  return result

def find_slot_id(cursor, slot):
  if slot in slot_cache:
    return slot_cache[slot]
  slot_bytes = bytes.fromhex(slot)
  sql = "SELECT * FROM `slots` WHERE `slot`=%s;"
  cursor.execute(sql, (slot_bytes,))
  result = cursor.fetchone()
  if result == None:
    sql = "INSERT INTO `slots` SET `slot`=%s;"
    cursor.execute(sql, (slot_bytes,))
    result = cursor.lastrowid
  else:
    result = result['id']
  slot_cache[slot] = result
  return result

def insert_slot_batch(cursor, slots):
  sql = "INSERT INTO `slotlogs` (`stateid`, `address_id`, `slot_id`, `slotvalue`) VALUES (%s, %s, %s, %s);"
  cursor.executemany(sql, slots)

def prepare_state(blocknumber, address_id, nonce, balance, codehash, storageroot, txindex, type_value):
  if codehash == emptycodehash or codehash == None:
    codehash = None
  else:
    codehash = bytes.fromhex(codehash)
  if storageroot == emptystorageroot or storageroot == None:
    storageroot = None
  else:
    storageroot = bytes.fromhex(storageroot)

  return (blocknumber, type_value, txindex, address_id, nonce, balance, codehash, storageroot)

def insert_state_batch(cursor, states):
  sql = "INSERT INTO `states` (`blocknumber`, `type`, `txindex`, `address_id`, `nonce`, `balance`, `codehash`, `storageroot`) VALUES (%s, %s, %s, %s, %s, %s, %s, %s);"
  cursor.executemany(sql, states)

def update_tx(cursor, txhash, txclass):
  txhash = bytes.fromhex(txhash)
  sql = "UPDATE `transactions` SET `class`=%s WHERE `hash`=%s;"
  cursor.execute(sql, (txclass, txhash))

def insert_account(cursor, address, type):
  address = bytes.fromhex(address)
  sql = "INSERT INTO `addresses` (`address`, `_type`) VALUES (%s, %s);"
  cursor.execute(sql, (address, type))
  account_cache[address] = cursor.lastrowid
  return cursor.lastrowid

def insert_contract(cursor, address, creationtx, code):
  address = bytes.fromhex(address)
  creationtx = bytes.fromhex(creationtx)
  code = bytes.fromhex(code)
  sql = "INSERT INTO `contracts` (`address`, `creationtx`, `code`) VALUES (%s, %s, %s);"
  try:
    cursor.execute(sql, (address, creationtx, code))
  except pymysql.err.IntegrityError:
    update_contract(cursor, address, creationtx, code)

def update_contract(cursor, address, creationtx, code):
  sql = "UPDATE `contracts` SET `code`=%s, `creationtx`=%s WHERE `address`=%s;"
  cursor.execute(sql, (code, creationtx, address)) 

def update_account_type(cursor, address_id, type):
  sql = "UPDATE `addresses` SET `_type`=%s WHERE `id`=%s;"
  cursor.execute(sql, (type, address_id))

run(start_block, end_block)