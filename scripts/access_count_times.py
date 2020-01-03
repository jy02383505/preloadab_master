#!/usr/bin/env python
"""
用于分析日志文件并将结果发送至后台接口
请将此脚本放置于产生访问日志的每一台设备上（目前分为6组的18台设备），并于每天6点之后（经验值，不妥可延后）执行一次
执行方式
/opt/hopeservice/.venv/bin/python access_count_times.py <host> <port>
示例
/opt/hopeservice/.venv/bin/python access_count_times.py 223.202.203.103 8000
参数说明，第一参数是后台网站ip；第二参数是后台网站端口。
"""
# import json
import commands
import time
from sys import exit, argv
import threading
import Queue
import logging
import httplib 

today = time.strftime('%Y%m%d', time.localtime(time.time()))
filepath = '/data/proclog/log/squid/access/*%s*' % today
# filepath = '*20170707*'
q = Queue.Queue()

logging.basicConfig(
    level = logging.DEBUG,
    format = '%(asctime)s-%(filename)s[line: %(lineno)d](%(levelname)s)->%(message)s',
    datefmt = '%Y-%m-%d %H:%M:%S',
    filename = 'r_%s.txt' % today,
    filemode = 'a+'
)


def get_channel_info_by_cmd(filename='t.txt', pos=14, sep='', cmd='zcat'):
    cmd = "%s %s | grep cdn-img | grep -vE 'TCP_HIT/404 | TCP_MISS/404' | awk -F '%s' '{print $%s}' | sort | uniq -c" % (cmd, filename, sep, pos)
    output_str = commands.getoutput(cmd)
    output_list = output_str.split('\n')
    output_json = {}
    for channel_info in output_list:
        output_json[channel_info.split()[1]] = {}
        output_json[channel_info.split()[1]]['count'] = channel_info.split()[0]
        output_json[channel_info.split()[1]]['channel_name'] = channel_info.split()[1]
    return output_json

# t1
def get_channel_info_from_server(filename=filepath):
    q.put(get_channel_info_by_cmd(filename, 14, ' ', 'zcat'))

# t2
def get_times_per_channel(filename=filepath):
    sep = ' '
    pos = '1, $12, $14'
    cmd = "zcat %s | grep cdn-img | awk -F '%s' '{print $%s}' | sort -n" % (filename, sep, pos)
    time_str = commands.getoutput(cmd)
    time_list = time_str.split('\n')
    time_dict = {}
    for time_info in time_list:
        time_dict[time_info.split()[2]] = {}

    for time_info in time_list:
        time_info_list = time_info.split()
        if not time_dict[time_info_list[2]].get('start_timestamp'):
            time_dict[time_info_list[2]]['start_timestamp'] = time_info_list[0]
            time_dict[time_info_list[2]]['start'] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(float(time_info_list[0])))
            time_dict[time_info_list[2]]['end_timestamp'] = time_info_list[0]
            time_dict[time_info_list[2]]['end'] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(float(time_info_list[0])))
        else:
            if float(time_dict[time_info_list[2]]['start_timestamp']) > float(time_info_list[0]):
                time_dict[time_info_list[2]]['start_timestamp'] = time_info_list[0]
                time_dict[time_info_list[2]]['start'] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(float(time_info_list[0])))
            if float(time_dict[time_info_list[2]]['end_timestamp']) < float(time_info_list[0]):
                time_dict[time_info_list[2]]['end_timestamp'] = time_info_list[0]
                time_dict[time_info_list[2]]['end'] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(float(time_info_list[0])))
    q.put(time_dict)

def post_data(host='223.202.203.103', port='8000', thedata={}):
    host = argv[1] if len(argv) > 1 else host
    port = argv[2] if len(argv) > 2 else port
    if not thedata:
        thedata = get_channel_total_info()
    conn = httplib.HTTPConnection("%s:%s" % (host, port))
    headers = {"Content-type":"application/json"}
    conn.request("POST", "/everyday/tasks/branch", str(thedata), headers)
    response = conn.getresponse()
    logging.debug('response: %s' % response.read())
    conn.close()

threads = []
t1 = threading.Thread(target=get_channel_info_from_server, args=(filepath,))
threads.append(t1)
t2 = threading.Thread(target=get_times_per_channel, args=(filepath,))
threads.append(t2)

if __name__ == '__main__':
    st = time.time()
    result = []
    for t in threads:
        t.setDaemon(True)
        t.start()
    t1.join()
    t2.join()
    while not q.empty():
        result.append(q.get())
    for k1, v1 in result[0].items():
        for k2, v2 in result[1].items():
            if k1 == k2:
                v1.update(v2)
    post_data('223.202.203.103', '8000', result[0])
    # post_data()
    logging.debug('result[0]: %s' % result[0])
    logging.debug('It takes %s seconds.' % (time.time() - st))
