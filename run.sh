#!/bin/sh

HOME=/home/refresh/preloadab
PORT=8000

case "$1" in
    start)
        nohup python -u $HOME/app.py --port=$PORT > $HOME/nohup_center.out 2>&1 &
        echo $PORT 'center start !!'
    ;;
    stop)
        ps aux|grep python|grep app.py|grep preloadab|grep -v grep|awk '{print "kill -9 "$2}'|sh
        echo 'center stop !!'
    ;;
    *)
        echo 'use start|stop'
    ;;
esac

