#!/bin/bash
DESTINATION=./
START=0
END=1

for (( i=$START; i<$END; i++ ))
do
  if [ $i -eq 0 ]
  then
    start=0
  else
    start=$(($i*1000000+1))
  fi
  end=$((($i+1)*1000000))
  mysqldump -u ethereum ethereum --lock-tables=false --skip-add-locks --skip-comments --skip-add-drop-table --no-create-info --where "number >= $start AND number <= $end" blocks > $DESTINATION/blocks_$start-$end.sql
  mysqldump -u ethereum ethereum --lock-tables=false --skip-add-locks --skip-comments --skip-add-drop-table --no-create-info --where "blocknumber >= $start AND blocknumber <= $end" transactions > $DESTINATION/transactions_$start-$end.sql
  mysqldump -u ethereum ethereum --lock-tables=false --skip-add-locks --skip-comments --skip-add-drop-table --no-create-info --where "blocknumber >= $start AND blocknumber <= $end" uncles > $DESTINATION/uncles_$start-$end.sql
  if [ $i -ge 12 ]
  mysqldump -u ethereum ethereum --lock-tables=false --skip-add-locks --skip-comments --skip-add-drop-table --no-create-info --where "blocknumber >= $start AND blocknumber <= $end" contracts > $DESTINATION/contracts_$start-$end.sql
  then
    mysqldump -u ethereum ethereum --lock-tables=false --skip-add-locks --skip-comments --skip-add-drop-table --no-create-info --where "id >= (SELECT transactions_accesslist.id FROM transactions_accesslist LEFT JOIN transactions ON transactions_accesslist.hash=transactions.hash WHERE blocknumber>=$start AND blocknumber<=$end ORDER BY transactions_accesslist.id ASC LIMIT 1) AND id <= (SELECT transactions_accesslist.id FROM transactions_accesslist LEFT JOIN transactions ON transactions_accesslist.hash=transactions.hash WHERE blocknumber>=$start AND blocknumber<=$end ORDER BY transactions_accesslist.id DESC LIMIT 1)" transactions_accesslist > $DESTINATION/transactions_accesslist_$start-$end.sql
  fi
  then
  fi
done