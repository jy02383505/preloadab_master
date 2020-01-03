#!/usr/bin/env python
"""
用于分析总日志文件并将结果发送至后台接口
请将此脚本放置于产生总日志的机器上，并于每天3点执行一次
执行方式
/opt/hopeservice/.venv/bin/python log_count_channel.py <host> <port>
示例
/opt/hopeservice/.venv/bin/python log_count_channel.py 223.202.203.103 8000
参数说明，第一参数是后台网站ip；第二参数是后台网站端口。
"""
# import json
import commands
import time
import httplib
from sys import exit, argv
import logging

today = time.strftime('%Y-%m-%d', time.localtime(time.time()))
filepath = '/var/www/html/vipshop_%s.log' % today
# filepath = './vipshop_%s.log' % today

logging.basicConfig(
    level = logging.DEBUG,
    format = '%(asctime)s-%(filename)s[line: %(lineno)d](%(levelname)s)->%(message)s',
    datefmt = '%Y-%m-%d %H:%M:%S',
    filename = 'r_%s.txt' % today,
    filemode = 'a+'
)


def get_channel_info_by_cmd(filename='t.txt', pos=14, sep='', cmd='cat'):
    cmd = "%s %s | awk -F '%s' '{print $%s}' | sort | uniq -c" % (cmd, filename, sep, pos)
    output_str = commands.getoutput(cmd)
    output_list = output_str.split('\n')
    output_json = {}
    for channel_info in output_list:
        output_json[channel_info.split()[1]] = {}
        output_json[channel_info.split()[1]]['count'] = channel_info.split()[0]
        output_json[channel_info.split()[1]]['channel_name'] = channel_info.split()[1]
    return output_json


def get_channel_total_info(filename=filepath):
    return get_channel_info_by_cmd(filename, 3, '/')

def post_data(host='223.202.203.103', port='8000', thedata={}):
    host = argv[1] if len(argv) > 1 else host
    port = argv[2] if len(argv) > 2 else port
    if not thedata:
        thedata = get_channel_total_info()
    conn = httplib.HTTPConnection("%s:%s" % (host, port))
    headers = {"Content-type":"application/json"}
    logging.debug(str(thedata))
    conn.request("POST", "/everyday/tasks/total", str(thedata), headers)
    response = conn.getresponse()
    logging.debug(response.read())
    conn.close()

if __name__ == '__main__':
    st = time.time()
    post_data('223.202.203.103', '8000')
    # post_data()
    logging.debug('It takes %s second.' % (time.time() - st))