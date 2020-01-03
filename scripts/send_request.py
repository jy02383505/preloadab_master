# -*- coding: utf-8 -*-
"""
用于发送请求，生成计算结果并发送电邮
此脚本放置于何处无特定要求，只需要每天发邮件的时候执行即可
执行方式
/opt/hopeservice/.venv/bin/python send_request.py <host> <port>
示例
/opt/hopeservice/.venv/bin/python send_request.py 223.202.203.103 8000
参数说明，第一参数是后台网站ip；第二参数是后台网站端口。
友情提示，最好使用Python2.7或以上执行脚本
"""
import httplib
import time
from sys import exit, argv

def do_send(host='223.202.203.103', port='8000', method='GET', url='/everyday/tasks/mail'):
    host = argv[1] if len(argv) > 1 else host
    port = argv[2] if len(argv) > 2 else port
    conn = httplib.HTTPConnection("%s:%s" % (host, port))
    headers = {"Content-type":"application/json"}
    conn.request(method, url, str({'papa': 'lym'}), headers)
    response = conn.getresponse()
    print response.read()
    conn.close()

if __name__ == '__main__':
    print time.strftime('%Y-%m-%d %H:%M:%S')
    do_send(url='/everyday/tasks/gather')
    time.sleep(4)
    do_send()
    print '\n-----over-----\n'
