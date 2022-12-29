import pymysql.cursors
import pymysql.err
import argparse

db_host = 'localhost'
db_user = 'ethereum'
db_pass = '' #fill in the MariaDB/MySQL password.
db_name = 'ethereum'

parser = argparse.ArgumentParser(description='DB wiper')
parser.add_argument('-s', '--start', type=int, default=1, help='block to start from')
args = parser.parse_args()

start_block = args.start
result = input('Warning: destructive operation.\nWipe DB from block #{}? (y|n): '.format(start_block))
if result.lower() != 'y': exit(1)

conn_mariadb = lambda host, user, password, database: pymysql.connect(host=host, user=user, password=password, database=database, cursorclass=pymysql.cursors.DictCursor)

conn = conn_mariadb(db_host, db_user, db_pass, db_name)
cursor = conn.cursor()

def fetch_first_stateid(cursor, block):
  sql = "SELECT * FROM `states` WHERE `blocknumber`>=%s ORDER BY `id` ASC LIMIT 1;"
  cursor.execute(sql, (block,))
  result = cursor.fetchone()

  if result == None:
    print('Error: no state log found')
    exit(1)
  return result['id']

def fetch_first_slotid(cursor, stateid):
  sql = "SELECT * FROM `slotlogs` WHERE `stateid`>=%s ORDER BY `id` ASC LIMIT 1;"
  cursor.execute(sql, (stateid,))
  result = cursor.fetchone()

  if result == None:
    print('no slot log found')
    return None
  return result['id']

def set_autoincrement(cursor, table, value):
  sql = "ALTER TABLE `{}` AUTO_INCREMENT=%s;".format(table)
  cursor.execute(sql, (value,))

def delete_after(cursor, table, id):
  sql = "DELETE FROM `{}` WHERE `id`>=%s;".format(table)
  cursor.execute(sql, (id,))

start_stateid = fetch_first_stateid(cursor, start_block)
start_slotid = fetch_first_slotid(cursor, start_stateid)

print('Deleting records for states')
delete_after(cursor, 'states', start_stateid)
print('Setting AUTO_INCREMENT value for states')
set_autoincrement(cursor, 'states', start_stateid)

if start_slotid != None:
  print('Deleting records for slots')
  delete_after(cursor, 'slotlogs', start_slotid)
  print('Setting AUTO_INCREMENT value for slots')
  set_autoincrement(cursor, 'slotlogs', start_slotid)

conn.commit()

print('Complete.')