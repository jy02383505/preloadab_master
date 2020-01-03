# -*- coding: utf-8 -*-
from urllib2 import Request, urlopen, URLError, HTTPError
import simplejson as json
import datetime
from copy import deepcopy
from settings import M_DB,EMAIL_ADD
from send_email import send_email_for_start


def send(task_detail):
    '''
    send task
    '''
    now = datetime.datetime.now()
    group_detail = task_detail['group_detail']
    resource_url = task_detail['resource_url']
    concurrency = task_detail.get('concurrency', 1600)
    task_id = str(task_detail['_id'])
    error_ips = []

    for group_num, group in enumerate(group_detail):
        client = group[0]
        server = group[1]
        for client_index, client_ip in enumerate(client):
            send_data = {'task_id':task_id, 'group_num': group_num, 'resource_url':resource_url, 'client_index':client_index, 'client_count':len(client),'client_ip':client_ip, 'server_ips':','.join(server), 'concurrency': concurrency}
            print 'send_data',send_data
            save_data = {'task_id':task_id, 'group_num':group_num, 'client_ip':client_ip, 'run_datetime':now, 'send_error': None, 'success_num':0, "error_num":0, 'not_found_num': 0, 'total_num':0, 'update_datetime':None, 'concurrency':concurrency, 'duration':None}
            is_success, _error =  make_request(client_ip, json.dumps(send_data))
            if _error:
                save_data['send_error'] = _error
                error_ips.append(client_ip)
            for s_ip in server:
                _save_data = deepcopy(save_data)
                _save_data['server_ip'] = s_ip
                M_DB.preload_b_result.insert(_save_data)
    #邮件
    send_email_for_start(EMAIL_ADD, task_detail, error_ips)


def make_request(client_ip, send_data):
    '''
    send request
    '''
    success = False
    error = None
    for x in xrange(3):

        try:
            header = {'Content-type': 'application/json'}
            req = Request('http://%s:41108/preloadab' %(client_ip), send_data, header)
            res = urlopen(req, timeout=2)
        except HTTPError, e:
            print 'send', x, 'ip:', client_ip, 'Error Code', e.code
            error = e.code
            continue
        except URLError, e:
            print 'send', x, 'ip:', client_ip, 'Error reason', e.reason
            error = str(e.reason)
            continue
        except Exception, e:
            print 'send', x, 'ip:', client_ip, 'Error', e
            error = str(e)
            continue
        else:
            success = True
            error = None
            break
    return success, error
