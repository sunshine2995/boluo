#!/bin/bash
CDIR=`dirname $0`
source $CDIR/../db/config.sh
if [ $# -eq 1 ]; then
	mysqldump -u$USERNAME -h $HOST -p$PASSWORD -l $WWW_DB > $1
else
	echo 'The number of the args is not right'
fi
