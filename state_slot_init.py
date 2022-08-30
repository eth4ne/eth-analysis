import pymysql.cursors
import json

db_host = 'localhost'
db_user = 'ethereum'
db_pass = '1234' #fill in the MariaDB/MySQL password.
db_name = 'ethereum'

conn_mariadb = lambda host, user, password, database: pymysql.connect(host=host, user=user, password=password, database=database, cursorclass=pymysql.cursors.DictCursor)

f = open('frontier.json', 'r')
alloc = json.loads(f.read())['alloc']

conn = conn_mariadb(db_host, db_user, db_pass, db_name)
cursor = conn.cursor()

for account, balance in alloc.items():
  address = account[2:]

  sql = "SELECT * FROM `addresses` WHERE `address`=UNHEX(%s);"
  cursor.execute(sql, (address,))
  result = cursor.fetchone()
  if result == None:
    sql = "INSERT INTO `addresses` SET `address`=UNHEX(%s), `_type`=%s;"
    cursor.execute(sql, (address, 10))
  address_id = cursor.lastrowid
  cursor.execute("INSERT INTO `states` (`blocknumber`, `type`, `address_id`, `balance`) VALUES (0, 31, %s, %s);", (address_id, balance['balance']))

#cursor.execute("INSERT INTO `states` (`blocknumber`, `type`, `address`, `balance`) VALUES (0, 1, UNHEX('00000000000000000000000000000000'), 5000000000000000000);")
  
conn.commit()