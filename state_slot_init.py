import pymysql.cursors
import json
from web3 import Web3

db_host = 'localhost'
db_user = 'ethereum'
db_pass = '1234' #fill in the MariaDB/MySQL password.
db_name = 'ethereum'

conn_mariadb = lambda host, user, password, database: pymysql.connect(host=host, user=user, password=password, database=database, cursorclass=pymysql.cursors.DictCursor)

f = open('frontier.json', 'r')
alloc = json.loads(f.read())['alloc']
alloc = sorted(alloc.items(), key=lambda x: x[0])

conn = conn_mariadb(db_host, db_user, db_pass, db_name)
cursor = conn.cursor()

cursor.execute("TRUNCATE `addresses`;")
cursor.execute("TRUNCATE `contracts`;")
cursor.execute("TRUNCATE `slotlogs`;")
cursor.execute("TRUNCATE `slots`;")
cursor.execute("TRUNCATE `states`;")
conn.commit()

for account, balance in alloc:
  address = account[2:]
  addresshash = Web3.toHex(Web3.keccak(hexstr=address))[2:]

  sql = "SELECT * FROM `addresses` WHERE `address`=UNHEX(%s);"
  cursor.execute(sql, (address,))
  result = cursor.fetchone()
  if result == None:
    sql = "INSERT INTO `addresses` SET `address`=UNHEX(%s), `hash`=UNHEX(%s), `_type`=%s;"
    cursor.execute(sql, (address, addresshash, 10))
  address_id = cursor.lastrowid
  cursor.execute("INSERT INTO `states` (`blocknumber`, `type`, `address_id`, `balance`) VALUES (0, 31, %s, %s);", (address_id, balance['balance']))
  
conn.commit()
