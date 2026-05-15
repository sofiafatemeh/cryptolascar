#!/bin/bash
cd /home/crypton/cryptolascar
exec /usr/bin/python3 main.py "$@" >> /home/crypton/cryptolascar/cron.log 2>&1
