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
  if [ $i -eq 0 ]
  then
    range_start=$((100000))
  else
    range_start=$(($start+200))
  fi
  range_end=$(($end-200))
  mysqldump -u ethereum ethereum --lock-tables=false --skip-add-locks --skip-comments --skip-add-drop-table --no-create-info --where "id >= (SELECT id FROM contracts WHERE creationtx=(SELECT hash FROM transactions WHERE blocknumber>=$start AND blocknumber<$range_start AND \`to\` IS NULL ORDER BY id ASC LIMIT 1)) AND id <= (SELECT id FROM contracts WHERE creationtx=(SELECT hash FROM transactions WHERE blocknumber<=$end AND blocknumber>$range_end AND \`to\` IS NULL ORDER BY id DESC LIMIT 1))" contracts > $DESTINATION/contracts_$start-$end.sql
done