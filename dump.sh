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
  mysqldump -u ethereum ethereum --lock-tables=false --skip-add-locks --skip-comments --skip-add-drop-table --no-create-info --where "blocknumber >= $start AND blocknumber <= $end" contracts > $DESTINATION/contracts_$start-$end.sql
  if [ $i -le 15 ]
  then
    mysqldump -u ethereum ethereum --lock-tables=false --skip-add-locks --skip-comments --skip-add-drop-table --no-create-info --where "blocknumber >= $start AND blocknumber <= $end" uncles > $DESTINATION/uncles_$start-$end.sql
  fi
  if [ $i -ge 12 ]
  then
    mysqldump -u ethereum ethereum --lock-tables=false --skip-add-locks --skip-comments --skip-add-drop-table --no-create-info --where "blocknumber >= $start AND blocknumber<=$end" transactions_accesslist > $DESTINATION/transactions_accesslist_$start-$end.sql
  fi
done