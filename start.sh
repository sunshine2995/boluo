#!/usr/bin/bash

ps -elf | grep gunicorn > /dev/null 2>&1 
if [ $? -eq 0 ];then
    pkill -f /usr/bin/gunicorn
fi
sleep 1
echo "" > nohup.out
nohup gunicorn -c gunicorn.py uwsgi:app & > /dev/null 2>&1
sleep 1
echo "started"
ps -elf | grep gunicorn



