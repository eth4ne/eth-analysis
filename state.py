import os

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
#32: read on hard fork
#33: write on hard fork

#63: kill account

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
#type 11: Uncertain (EoA or CA, not exist but delete requested)


def get_state(_from, _to, interval=1000, datadir='/ethereum/txsubstate'):
  state_updates = {}
  contract_updates = {}
  slot_updates = {}
  cnt_block = 0
  cnt_state = 0
  cnt_slot = 0
  cnt_tx = 0
  state_id = 0

  _from_ = _from
  _from = (_from-1) // interval * interval+1
  for blockheight in range(_from, _to, interval):
    filename = os.path.join(datadir, 'TxSubstate{:08}-{:08}.txt'.format(blockheight, blockheight+interval-1))
    f = open(filename, 'r')
    blocks = f.read().split('/')[1:]
    for block in blocks:
      blocknumber = int(block.split('\n')[0].split(':')[1])
      if blocknumber < _from_:
        continue
      if blocknumber >= _to:
        break
      cnt_block += 1
      block_states = []
      block_slots = []
      block_contracts = []

      txcount = block.count('!')

      if '*' in block:
        txstart = 0 #hard fork
      else:
        txstart = 1
      for i in range(txstart, txcount+1):
        txbody = block.split('!')[i]
        tx = {
          'index': i-1,
          'hash': None,
          'type': None,
          'from': None,
          'to': None,
          'deployedca': None,
        }
        if i == 0:
          state_type = 33
          tx['index'] = None
          txdata = []
        else:
          txdata = txbody.split('@')[0].split('\n')[:-1]
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
          address = j.split(':')[1][2:]
          state_update = prepare_state(state_id, blocknumber, address, None, None, None, None, tx['index'], state_type)
          block_states.append(state_update)
          state_id += 1
            
        writelist = txbody.split('#')[1].split('$')[0].split('.')[1:]
        for j in writelist:
          write_data = j.split('\n')[:-1]
          write = {
            'address': None,
            'nonce': None,
            'balance': None,
            'codehash': None,
            'code': None,
            'deployedbyca': False,
            'delete': False,
            'storageroot': None,
          }
          slots = []
          for ij in write_data:
            k = ij.split(':')[0]
            v = ij.split(':')[1]
            if k == 'address':
              write['address'] = v[2:]
            elif k == 'Deployedaddress':
              write['address'] = v[2:]
              write['deployedbyca'] = True
            elif k == 'deletedaddress':
              write['address'] = v[2:]
              write['delete'] = True
            elif k == 'Nonce':
              write['nonce'] = int(v)
            elif k == 'Balance':
              write['balance'] = int(v)
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
              if slot['value'] == '0':
                slot['value'] = None
              slots.append(slot)
    
          address = write['address']

          if write['delete'] == True and tx['type'] != 7:
            state_update = prepare_state(state_id, blocknumber, address, None, None, None, None, tx['index'], 63)
            for slot in slots:
              slot['address'] = address
              block_slots.append(slot)
            block_states.append(state_update)
            state_id += 1
          elif write['delete'] == True:
            #delete miner in failed contract call
            pass
          else:
            state_update = prepare_state(state_id, blocknumber, address, write['nonce'], write['balance'], write['codehash'], write['storageroot'], tx['index'], state_type+1)
            for slot in slots:
              slot['address'] = address
              block_slots.append(slot)
            block_states.append(state_update)
            state_id += 1
        
          cnt_state += 1

          if write['code'] != None:
            if write['deployedbyca'] == True:
              block_contracts.append({'address': write['address'], 'txhash': tx['hash'], 'code': write['code']})
          
        cnt_tx += 1

      unclecount = block.count('^')

      for i in range(1, unclecount+1):
        uncle = block.split('^')[i].split('\n')[0:5]
        uncle_address = uncle[0].split(':0x')[1].lower()
        uncle_nonce = int(uncle[1].split(':')[1])
        uncle_balance = int(uncle[2].split(':')[1])
        uncle_codehash = uncle[3].split(':')[1][2:]
        uncle_storageroot = uncle[4].split(':')[1][2:]

        state_update = prepare_state(state_id, blocknumber, uncle_address, uncle_nonce, uncle_balance, uncle_codehash, uncle_storageroot, None, 3)
        block_states.append(state_update)
        state_id += 1

      miner = block.split('$')[1].split('\n')[0:5]
      miner_address = miner[0].split(':0x')[1].lower()
      miner_nonce = int(miner[1].split(':')[1])
      miner_balance = int(miner[2].split(':')[1])
      miner_codehash = miner[3].split(':')[1][2:]
      miner_storageroot = miner[4].split(':')[1][2:]

      state_update = prepare_state(state_id, blocknumber, miner_address, miner_nonce, miner_balance, miner_codehash, miner_storageroot, None, 1)
      block_states.append(state_update)
      state_id += 1

      state_updates[blocknumber] = block_states
      slot_updates[blocknumber] = block_slots
      contract_updates[blocknumber] = block_contracts

  return state_updates, slot_updates

def prepare_state(state_id, blocknumber, address, nonce, balance, codehash, storageroot, txindex, type_value):
  emptycodehash = 'pty'
  emptystorageroot = 'pty'
  if codehash == emptycodehash or codehash == None:
    codehash = None
  if storageroot == emptystorageroot or storageroot == None:
    storageroot = None

  return {
    'blocknumber': blocknumber,
    'type': type_value,
    'txindex': txindex,
    'address': address,
    'nonce': nonce,
    'balance': balance,
    'codehash': codehash,
    'storageroot': storageroot
  }
