#!/bin/bash

for i in {0..16}
do
  if [ $i -eq 0 ]
  then
    start=0
  else
    start=$(($i*1000000+1))
  fi
  end=$((($i+1)*1000000))
  mysqldump -u ethereum ethereum --skip-comments --skip-add-drop-table --no-create-info --where "number >= $start AND number <= $end" blocks > blocks_$start-$end.sql
  mysqldump -u ethereum ethereum --skip-comments --skip-add-drop-table --no-create-info --where "blocknumber >= $start AND blocknumber <= $end" transactions > transactions_$start-$end.sql
  mysqldump -u ethereum ethereum --skip-comments --skip-add-drop-table --no-create-info --where "blocknumber >= $start AND blocknumber <= $end" uncles > uncles_$start-$end.sql
  if [ $i -eq 0 ]
  then
    range_start=$((100000))
  else
    range_start=$(($start+1000))
  fi
  range_end=$(($end-1000))
  mysqldump -u ethereum ethereum --lock-tables=false --skip-comments --skip-add-drop-table --no-create-info --where "id >= (SELECT id FROM contracts WHERE creationtx=(SELECT hash FROM transactions WHERE blocknumber>=$start AND blocknumber<$range_start AND \`to\` IS NULL ORDER BY id ASC LIMIT 1)) AND id <= (SELECT id FROM contracts WHERE creationtx=(SELECT hash FROM transactions WHERE blocknumber<=$end AND blocknumber>$range_end AND \`to\` IS NULL ORDER BY id DESC LIMIT 1))" contracts > contracts_$start-$end.sql
done