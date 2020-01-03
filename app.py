# -*- coding: utf-8 -*-
import tornado.ioloop
import tornado.web
import datetime
import time
from tornado.gen import coroutine
from tornado.httpserver import HTTPServer
from tornado.options import define, options
from bson import ObjectId
from pymongo import ASCENDING
from settings import *
from utils import db_update, get_all_data, error_res, func_lock,get_login_name,get_login_author_secure,get_all_conf
import os, random, StringIO, hashlib , urllib, urllib2
from send_task import send
from send_email import send_email
import simplejson as json
import traceback


preload_b = M_DB.preload_b     #普通定时任务
preload_b_e = M_DB.preload_b_e #每日定时任务
preload_b_result = M_DB.preload_b_result
preload_b_admin = M_DB.preload_b_admin

settings ={"template_path":TEMPLATE_PATH,
           "static_path": STATIC_PATH,
           "debug":DEBUG,
            "cookie_secret": "bZJc2sWbQLKos6GkHn/VB9oXwQt8S0R0kRvJ5/xJ89E=",
            "login_url": "/login",
           }


class BaseHandler(tornado.web.RequestHandler):
    def get_current_user(self):
        return self.get_secure_cookie("login")


class Login(BaseHandler):
    '''
    /首页 暂时做跳转
    '''

    def get(self):
        client_now=CLIENT_NOW
        self.render('login.html',error='',client_html=client_now)

class auth(BaseHandler):
    def get(self):
        token = self.get_argument('ioss', '')
        print 'token',token
        token_type = type(token)
        eoss = self.get_argument('eoss', '')
        print "eoss",eoss
        client_now=CLIENT_NOW
        if token != None and token != '':

            src = client_now + token + "CssoC"
            hashmd5 = hashlib.md5()
            hashmd5.update(src)
            hashmd5 = hashmd5.hexdigest()
            params = urllib.urlencode({'clientName': client_now, 'tokenId': token, 'md5Hash': hashmd5})
            urllib.ssl._DEFAULT_CIPHERS += 'HIGH:!DH:!aNULL'
            f = urllib.urlopen("https://sso.chinacache.com/queryByTokenId?%s" % params)
            data = f.read()
            param = "{\"clientName\":\"iss\",\"tokenId\":\"" + token + "\",\"md5Hash\":" + hashmd5 + "}"
            _dict = json.loads(data)
            # 比较成功，跳转index
            if _dict["hasLogon"] == True:
                login_name = _dict["account"]
                #M_DB.preload_b_admin.insert({'username': 'hu.zhang@chinacache.com', 'power': 'admin', 'created_time': datetime.datetime.now()})
                data = M_DB.preload_b_admin.find_one({"username": login_name});
                if str(data) == 'None':
                    self.set_secure_cookie("login", login_name + ":" + '')
                    self.set_secure_cookie("author_cookie", '')

                else:
                    self.set_secure_cookie("login", login_name + ":" + data['power'])
                    self.set_secure_cookie("author_cookie", str(data['power']))

                self.redirect('/tasks')
            else:
                self.render('login.html', error='error',client_html=client_now)
        elif eoss != '':
            self.render('login.html', error='error',client_html=client_now)
        else:
            self.render('login.html', error='',client_html=client_now)

    def post(self):
        print "post方法里面"


class Logout(BaseHandler):
    
    def get(self):
        self.set_secure_cookie("login", '')
        self.set_secure_cookie("author_cookie", '')

        self.redirect('/login')

class Tasks(BaseHandler):
    '''
    定日定时任务首页
    '''
    @tornado.web.authenticated
    def get(self):
	login_name,authority=get_login_name(self)
        author_secure = get_login_author_secure(self)
        res = get_all_data()
        self.render('tasks.html',author_secure=author_secure,loginname=login_name, query_id='', all_tasks=res['all_data'], totalpage=res['totalpage'], c_page = 0)

    def post(self):
	login_name,authority=get_login_name(self)
        author_secure = get_login_author_secure(self)
        query = {}
        query_id = self.get_argument('query_id', '')
        if query_id:
            try:
                query = {'_id': ObjectId(query_id)}
            except:
                query = {'username': query_id}
            #query = {'$or':[{'username':query_id},{'_id':query_id}]}
        c_page = int(self.get_argument('c_page', 0))
        res = get_all_data(c_page, query)
        self.render('tasks.html',author_secure=author_secure,loginname=login_name, query_id=query_id, all_tasks=res['all_data'], totalpage=res['totalpage'],c_page= c_page)


class EveryDayTasks(BaseHandler):
    '''
    每日定时任务首页
    '''
    @tornado.web.authenticated
    def get(self):

	login_name,authority=get_login_name(self)
        author_secure = get_login_author_secure(self)
        res = get_all_data(col=preload_b_e)
        self.render('everyday_tasks.html', author_secure=author_secure,loginname=login_name,query_id='', all_tasks=res['all_data'], totalpage=res['totalpage'], c_page = 0)

    def post(self):
	login_name,authority=get_login_name(self)
        author_secure = get_login_author_secure(self)
        query = {}
        query_id = self.get_argument('query_id', '')
        if query_id:
            try:
                query = {'_id': ObjectId(query_id)}
            except:
                query = {'username': query_id}
            #query = {'$or':[{'username':query_id},{'_id':query_id}]}
        c_page = int(self.get_argument('c_page', 0))
        res = get_all_data(c_page, query, preload_b_e)
        self.render('everyday_tasks.html',author_secure=author_secure,loginname=login_name, query_id=query_id, all_tasks=res['all_data'], totalpage=res['totalpage'],c_page= c_page)


class TaskInit(BaseHandler):
    '''
    任务初始化
    '''
    @tornado.web.authenticated
    def post(self):

        now = datetime.datetime.now()
        username = self.get_argument('username', '')
        type_select = self.get_argument('type_select', '')

        if type_select == 'normal':
            start_datetime_str = self.get_argument('start_datetime', '')
            start_datetime = datetime.datetime.strptime(start_datetime_str, '%Y-%m-%d %H:%M')
        else:
            start_datetime = self.get_argument('start_time', '')

        #if start_datetime < now:
        #    raise

        resource_url = self.get_argument('resource_url', '')
        concurrency = int(self.get_argument('concurrency', 1600))

        group_detail = []
        group_num = int(self.get_argument('group_num', 0))

        for g_n in xrange(group_num):
            new_g = g_n + 1
            clients = self.get_argument('%s-client' %(new_g))
            client_ips = clients.split('&')
            servers = self.get_argument('%s-server' %(new_g))
            server_ips = servers.split('&')
            group_detail.append([client_ips, server_ips])

        print '------TaskInit------'
        print username
        print start_datetime
        print resource_url
        print group_detail
        print '------TaskInit over------'

        if type_select == 'normal':
            preload_b.insert({'username':username,'start_datetime':start_datetime,'created_time':now,'resource_url':resource_url,'group_detail':group_detail, 'run_datetime': '', 'finish_datetime':'', 'concurrency':concurrency})
            self.redirect('/tasks')
        else:
            preload_b_e.insert({'username':username,'start_time':start_datetime,'created_time':now,'resource_url':resource_url,'group_detail':group_detail, 'run_datetime': '', 'concurrency':concurrency})
            self.redirect('/everyday/tasks')


    def get(self):
        '''
        创建任务
        '''
        login_name,authority=get_login_name(self)
        author_secure = get_login_author_secure(self)
        self.render('task_add.html',author_secure=author_secure,loginname=login_name)


class TaskDel(BaseHandler):
    '''
    任务删除
    '''
    @tornado.web.authenticated
    def get(self, task_id):
	login_name,authority=get_login_name(self)
        author_secure = get_login_author_secure(self)
        task = preload_b.find_one({'_id':ObjectId(task_id)})
        if not task_id:
            self.write(error_res('no task'))
        start_datetime = task['start_datetime']
        now = datetime.datetime.now()
        if now > start_datetime and now - start_datetime < datetime.timedelta(days=1):
            self.write(error_res('Delete the task must be a day later'))

        preload_b.remove({'_id':ObjectId(task_id)})
        preload_b_result.remove({'task_id':task_id})

        self.redirect('/tasks')


class EveryDayTaskDel(BaseHandler):
    '''
    每日任务删除
    '''
    @tornado.web.authenticated
    def get(self, task_id):
	login_name,authority=get_login_name(self)
        author_secure = get_login_author_secure(self)
        task = preload_b_e.find_one({'_id':ObjectId(task_id)})
        if not task_id:
            self.write(error_res('no task'))

        preload_b_e.remove({'_id':ObjectId(task_id)})

        self.redirect('/everyday/tasks')


class TaskDetail(BaseHandler):
    '''
    任务详情
    '''
    @tornado.web.authenticated
    def get(self, task_id):
	login_name,authority=get_login_name(self)
        author_secure = get_login_author_secure(self)
        res = preload_b_result.find({'task_id':task_id}).sort('group_num', ASCENDING)
        if res.count() == 0:
            self.write('no task')
            return

        total_num = {}
        qps_data = {}
        not_found_data  = {}
        error_data = {}
        result = []
        t = preload_b.find_one({'_id':ObjectId(task_id)})
        for r in res:
            group_num = r['group_num']
            total_num.setdefault(group_num, 0)
            total_num[group_num] += int(r['total_num'])
            #QPS总和
            qps_data.setdefault(group_num, 0)
            duration = r.get('duration', 0)
            if r.get('duration', 0) > 0:
                qps = round(float(r['total_num'])/int(duration),2)
                qps_data[group_num] += qps
            #404 总和
            not_found_data.setdefault(group_num, 0)
            not_found_data[group_num] += int(r.get('not_found_num',0))

            #error 总和
            error_data.setdefault(group_num, 0)
            error_data[group_num] += int(r.get('error_num', 0))

            #TODO
           # if r['finish_datetime']:
           #     du = r['finish_datetime'] - t['start_datetime']
           #     qps = round(float(r['total_num'])/du.seconds,2)
           #     qps_data[group_num] += qps

            result.append(r)

        self.render('task_detail.html',author_secure=author_secure,loginname=login_name, details= result, total_num=sorted(total_num.items(), key=lambda x: x[0]), qps_data=qps_data, not_found_data=not_found_data, error_data=error_data)


class TaskChange(BaseHandler):
    '''
    任务更改
    '''
    @tornado.web.authenticated
    def get(self, task_id):
	login_name,authority=get_login_name(self)
        author_secure = get_login_author_secure(self)
        task = preload_b.find_one({'_id': ObjectId(task_id)})
        if not task:
            error_res('no task')
            return
        start_datetime = task['start_datetime'].strftime('%Y-%m-%d %H:%M')

        self.render('task_change.html', author_secure=author_secure,loginname=login_name,task=task, start_datetime=start_datetime)

    @tornado.web.authenticated
    def post(self, task_id):
	login_name,authority=get_login_name(self)
        author_secure = get_login_author_secure(self)
        task = preload_b.find_one({'_id': ObjectId(task_id)})
        if not task:
            self.write(error_res('no task'))
            return
       # if task['run_datetime']:
       #     self.write(error_res('task had started'))
       #     return

        now = datetime.datetime.now()
        username = self.get_argument('username', '')
        start_datetime_str = self.get_argument('start_datetime', '')
        start_datetime = datetime.datetime.strptime(start_datetime_str, '%Y-%m-%d %H:%M')
        #if start_datetime < now:
        #    raise
        resource_url = self.get_argument('resource_url', '')
        concurrency = int(self.get_argument('concurrency', 0))

        group_detail = []
        group_num = int(self.get_argument('group_num', 0))

        for g_n in xrange(group_num):
            new_g = g_n + 1
            clients = self.get_argument('%s-client' %(new_g))
            client_ips = clients.split('&')
            servers = self.get_argument('%s-server' %(new_g))
            server_ips = servers.split('&')
            group_detail.append([client_ips, server_ips])

        print '------TaskChange------'
        print username
        print start_datetime
        print resource_url
        print group_detail
        print concurrency
        print '------TaskChange over------'

        db_update(preload_b,{'_id':ObjectId(task_id)}, {'$set':{'username':username,'start_datetime':start_datetime,'resource_url':resource_url,'group_detail':group_detail, 'concurrency':concurrency}})

        self.redirect('/tasks')



class EveryDayTaskChange(BaseHandler):
    '''
    任务更改
    '''
    @tornado.web.authenticated
    def get(self, task_id):
	login_name,authority=get_login_name(self)
        author_secure = get_login_author_secure(self)
        task = preload_b_e.find_one({'_id': ObjectId(task_id)})
        if not task:
            error_res('no task')
            return

        self.render('everyday_task_change.html',author_secure=author_secure,loginname=login_name, task=task)

    @tornado.web.authenticated
    def post(self, task_id):
	login_name,authority=get_login_name(self)
        author_secure = get_login_author_secure(self)
        task = preload_b_e.find_one({'_id': ObjectId(task_id)})
        if not task:
            self.write(error_res('no task'))
            return
       # if task['run_datetime']:
       #     self.write(error_res('task had started'))
       #     return

        now = datetime.datetime.now()
        username = self.get_argument('username', '')
        start_time = self.get_argument('start_time', '')
        #if start_datetime < now:
        #    raise
        resource_url = self.get_argument('resource_url', '')
        concurrency = int(self.get_argument('concurrency', 0))

        group_detail = []
        group_num = int(self.get_argument('group_num', 0))

        for g_n in xrange(group_num):
            new_g = g_n + 1
            clients = self.get_argument('%s-client' %(new_g))
            client_ips = clients.split('&')
            servers = self.get_argument('%s-server' %(new_g))
            server_ips = servers.split('&')
            group_detail.append([client_ips, server_ips])

        print '------TaskChange------'
        print username
        print start_time
        print resource_url
        print group_detail
        print concurrency
        print '------TaskChange over------'

        db_update(preload_b_e,{'_id':ObjectId(task_id)}, {'$set':{'username':username,'start_time':start_time,'resource_url':resource_url,'group_detail':group_detail, 'concurrency':concurrency}})

        self.redirect('/everyday/tasks')



class TaskApiUpdate(BaseHandler):
    '''
    Api 任务update
    '''
    def post(self):

        now = datetime.datetime.now()
        req = json.loads(self.request.body)
        remote_ip = self.request.remote_ip

        task_id = req.get('task_id', '')
        #fc ip
        server_ip = req.get('server_ip', '')
        success_num = req.get('success_num', '')
        error_num = req.get('error_num', '')
        num_404 = req.get('not_found_num', '')
        total_num = req.get('total_num', '')
        is_finish = req.get('is_finish', 'false')
        duration = int(req.get('duration', 0))

        print '---TaskApiUpdate---'
        print 'remote_ip',remote_ip
        print 'task_id', task_id
        print 'server_ip', server_ip
        print 'success_num', success_num
        print 'error_num', error_num
        print 'num_404', num_404
        print 'is_finish', is_finish
        print 'total_num', total_num
        print 'duration', duration
        print '---TaskApiUpdate---end'

        if not task_id:
            print 'no task_id'
            raise
        if not success_num and not error_num and not num_404:
            print 'no num'
            raise

        old_task = preload_b_result.find_one({'task_id':task_id, 'client_ip':remote_ip, 'server_ip':server_ip})
        if not old_task:
            raise

        if is_finish == 'true':
            db_update(preload_b_result, {'task_id':task_id, 'client_ip':remote_ip, 'server_ip':server_ip}, {"$set":{'success_num':success_num, 'error_num':error_num, 'not_found_num':num_404, 'total_num':total_num, 'update_datetime':now, 'duration':duration}})
        else:
            db_update(preload_b_result, {'task_id':task_id, 'client_ip':remote_ip, 'server_ip':server_ip}, {"$set":{'success_num':success_num, 'error_num':error_num, 'not_found_num':num_404, 'total_num':total_num, 'update_datetime':now}})

        all_finish = True
        for t in preload_b_result.find({'task_id':task_id}):
            if not t['duration']:
                all_finish = False
                break

        if all_finish:
            #总任务成功
            print task_id, 'all_finish', now
            db_update(preload_b, {'_id': ObjectId(task_id), 'finish_datetime':''}, {'$set':{'finish_datetime':now}})

        w = {}
        w['code'] = 200
        self.write(json.dumps(w))


class TotalCount2Db(BaseHandler):
    '''
    Put vipshop total log into mongodb
    '''
    def post(self):
        data = eval(self.request.body)
        for k in data.keys():
            k_new = k.replace('.', '-')
            data[k_new] = data[k]
            del(data[k])
        remote_ip = self.request.remote_ip
        data['id'] = '%s_%s' % (remote_ip, time.strftime('%Y%m%d'))
        data['create_time'] = datetime.datetime.now()
        data['create_time_timestamp'] = time.time()
        found = M_DB.preload_b_total_count.find_one({'id': data['id']})
        w = {}
        if not found:
            result = M_DB.preload_b_total_count.insert_one(data)
            if not result.inserted_id:
                w['code'] = 404
                w['msg'] = 'Total counting data inserted unsuccessfully.'
                self.write(str(w))
                return
            w['inserted_id'] = str(result.inserted_id)
            w['code'] = 200
            w['msg'] = 'The total counting data has inserted successfully.'
            self.write(str(w))
        else:
            result = found
            w['code'] = 200
            w['msg'] = 'Fine,the total counting data has already existed.'
            w['inserted_id'] = found['_id']
            self.write(str(w))


class BranchCount2Db(BaseHandler):
    '''
    Put access log into mongodb
    '''
    def post(self):
        data = eval(self.request.body)
        for k in data.keys():
            k_new = k.replace('.', '-')
            data[k_new] = data[k]
            del(data[k])
        remote_ip = self.request.remote_ip
        data['remote_ip'] = remote_ip
        data['id'] = remote_ip + '_' + time.strftime('%Y%m%d')
        data['create_time'] = datetime.datetime.now()
        data['create_time_timestamp'] = time.time()
        found = M_DB.preload_b_branch_count.find_one({'id': data['id']})
        w = {}
        if not found:
            result = M_DB.preload_b_branch_count.insert_one(data)
            if not result.inserted_id:
                w['code'] = 404
                w['msg'] = '%s\'s counting and times data inserted unsuccessfully.' % remote_ip
                self.write(str(w))
                return
            w['inserted_id'] = str(result.inserted_id)
            w['code'] = 200
            w['msg'] = 'The %s\'s counting and times data has inserted successfully.' % remote_ip
            self.write(str(w))
        else:
            result = found
            w['code'] = 200
            w['msg'] = 'Fine,the %s\'s counting and times data has already existed.' % remote_ip
            w['inserted_id'] = found['_id']
            self.write(str(w))


class DataGathering(BaseHandler):
    '''
    Compute final results.
    '''
    def get(self):
        remote_ip = self.request.remote_ip
        today_str = time.strftime('%Y-%m-%d 00:00:00')
        today_obj = datetime.datetime.strptime(today_str, '%Y-%m-%d %H:%M:%S')
        tomorrow_obj = today_obj + datetime.timedelta(days=1)
        access_targets = M_DB.preload_b.find_one({'created_time': {'$gte': today_obj, '$lte': tomorrow_obj}})
        if not access_targets:
            self.write({'msg': 'preload_b has nothing!', 'code': 500})
            return
        group_detail = access_targets.get('group_detail', '')
        groups = {}
        for group in group_detail:
            groups[group[0][0]] = group[1]
            for i in range(len(group[1])):
                ipp = group[1].pop()
                group[1].insert(0, ipp.split(':')[0])

        serveri = {}
        for k, v in groups.items(): # v has 3 elements
            one_group_ips = M_DB.preload_b_branch_count.find({'remote_ip': {'$in': v}, 'create_time': {'$gte': today_obj, '$lte': tomorrow_obj}})
            serveri[k] = {}
            for one_ip_dict in one_group_ips: # one_ip_dict big dict of one remote_ip
                for one_ip in one_ip_dict.values():
                    if isinstance(one_ip, dict) and one_ip.get('channel_name'):
                        if one_ip['channel_name'] not in serveri[k].keys():
                            serveri[k][one_ip['channel_name']] = {}
                            serveri[k][one_ip['channel_name']]['count'] = 0
                            serveri[k][one_ip['channel_name']]['start_timestamp'] = float(one_ip['start_timestamp'])
                            serveri[k][one_ip['channel_name']]['end_timestamp'] = float(one_ip['end_timestamp'])
                            serveri[k][one_ip['channel_name']]['count'] += float(one_ip['count'])
                            serveri[k][one_ip['channel_name']]['start'] = one_ip['start']
                            serveri[k][one_ip['channel_name']]['end'] = one_ip['end']
                        else:
                            serveri[k][one_ip['channel_name']]['count'] += float(one_ip['count'])
                            if serveri[k][one_ip['channel_name']]['start_timestamp'] > float(one_ip['start_timestamp']):
                                serveri[k][one_ip['channel_name']]['start_timestamp'] = float(one_ip['start_timestamp'])
                                serveri[k][one_ip['channel_name']]['start'] = one_ip['start']
                            if serveri[k][one_ip['channel_name']]['end_timestamp'] < float(one_ip['end_timestamp']):
                                serveri[k][one_ip['channel_name']]['end_timestamp'] = float(one_ip['end_timestamp'])
                                serveri[k][one_ip['channel_name']]['end'] = one_ip['end']
        total_count = M_DB.preload_b_total_count.find_one({'id': '113.108.239.71_%s' % time.strftime('%Y%m%d')})
        for v_t in total_count.values():
            if isinstance(v_t, dict):
                for k_s, v_s in serveri.items():
                    for channel_name in v_s.keys():
                        if channel_name == v_t['channel_name']:
                            v_s[channel_name]['success_rate'] = v_s[channel_name]['count'] / float(v_t['count']) if v_s[channel_name]['count'] < float(v_t['count']) else float(1)
        for kk in serveri.keys():
            kk_new = kk.replace('.', '-')
            serveri[kk_new] = serveri[kk]
            del(serveri[kk])
        for vv in serveri.values():
            for kkk in vv.keys():
                vv[kkk]['channel_name'] = kkk
                kkk_new = kkk.replace('.', '-')
                vv[kkk_new] = vv[kkk]
                del(vv[kkk])
        serveri['id'] = 'result_by_group_%s' % time.strftime('%Y%m%d')
        serveri['create_time'] = datetime.datetime.now()
        serveri['create_time_timestamp'] = time.time()
        found = M_DB.preload_b_result_group.find_one({'id': serveri['id']})
        w = {}
        if not found:
            result = M_DB.preload_b_result_group.insert_one(serveri)
            if not result.inserted_id:
                w['code'] = 404
                w['msg'] = 'The result_group has inserted unsuccessfully.'
                self.write(str(w))
                return
            w['inserted_id'] = str(result.inserted_id)
            w['code'] = 200
            w['msg'] = 'The result_group has inserted successfully.'
            self.write(str(w))
        else:
            w['code'] = 200
            w['msg'] = 'Fine,the result_group has already existed.'
            w['inserted_id'] = found['_id']
            self.write(str(w))


class MailGatheredData(BaseHandler):
    """Report the accessing results by email"""
    def get(self):
        today_str = time.strftime('%Y%m%d')
        find_id = 'result_by_group_%s' % today_str
        result = M_DB.preload_b_result_group.find_one({'id': find_id})
        if not result:
            self.write({'msg': 'result_group has nothing!', 'code': 404})
            return
        for r in result.values():
            if isinstance(r, dict):
                rate_sum = 0
                for rr in r.values():
                    rate_sum += rr['success_rate']
                r['rate_sum'] = rate_sum
        result_to_pick = sorted([r for r in result.values() if isinstance(r, dict)], key=lambda serveri: serveri['rate_sum'])
        the_best = result_to_pick[-1]
        # after sorted the result list, cut the lowest and cut the highest, take the average
        result_to_pick = result_to_pick[1:-1]
        use_the_best = False
        if not result_to_pick:
            use_the_best = True
        result_second_best = result_to_pick[-1]

        result_chosen_sum = {}
        result_chosen_sum['create_time'] = result['create_time']
        result_chosen_sum['create_time_timestamp'] = result['create_time_timestamp']
        result_second_best['create_time'] = result['create_time']
        result_second_best['create_time_timestamp'] = result['create_time_timestamp']
        the_best['create_time'] = result['create_time']
        the_best['create_time_timestamp'] = result['create_time_timestamp']
        use_second_best = False
        try:
            for resulti in result_to_pick: # 4 clients
                for _k, _v in resulti.items(): # 6 channels
                    if isinstance(_v, dict):
                        if _k not in result_chosen_sum.keys():
                            result_chosen_sum[_k] = {}
                            result_chosen_sum[_k]['channel_name'] = _v['channel_name']
                            result_chosen_sum[_k]['count_sum'] = _v['count']
                            result_chosen_sum[_k]['success_rate_sum'] = _v['success_rate']
                            result_chosen_sum[_k]['start_timestamp'] = _v['start_timestamp']
                            result_chosen_sum[_k]['start'] = _v['start']
                            result_chosen_sum[_k]['end_timestamp'] = _v['end_timestamp']
                            result_chosen_sum[_k]['end'] = _v['end']
                        else:
                            result_chosen_sum[_k]['count_sum'] += _v['count']
                            result_chosen_sum[_k]['success_rate_sum'] += _v['success_rate']
                            if _v['start_timestamp'] < result_chosen_sum[_k]['start_timestamp']:
                                result_chosen_sum[_k]['start_timestamp'] = _v['start_timestamp']
                                result_chosen_sum[_k]['start'] = _v['start']
                            if _v['end_timestamp'] > result_chosen_sum[_k]['end_timestamp']:
                                result_chosen_sum[_k]['end_timestamp'] = _v['end_timestamp']
                                result_chosen_sum[_k]['end'] = _v['end']
                    else:
                        use_second_best = True
                        raise
        except Exception as e:
            pass

        second_flag = ''
        for _vv in result_chosen_sum.values():
            if isinstance(_vv, dict):
                _vv['count'] = _vv['count_sum'] / float(len(result_to_pick))
                _vv['success_rate'] = _vv['success_rate_sum'] / float(len(result_to_pick))
                if _vv['success_rate'] < 0.95:
                    use_second_best = True
                    break
                if _vv['success_rate'] > 1:
                    _vv['success_rate'] = 1

        result_chosen = result_chosen_sum
        if use_second_best:
            result_chosen = result_second_best
            second_flag = '*'
            for _vvv in result_chosen.values():
                if isinstance(_vvv, dict):
                    if _vvv['success_rate'] < 0.95:
                        ### if second_best success_rate is less than 0.95 use the best one
                        result_chosen = the_best
                        second_flag = '**'
                        break
        if use_the_best:
            result_chosen = the_best
            second_flag = '***'

        to_add = SUCCESS_EMAIL_ADD

        username = 'Vipshop'
        content = u'%sHi, there:<br/><br/><h3>%s 预加载成功率汇报:</h3>' %(second_flag, username)
        table = u'<table border="1"><tr>\
                    <th>日期</th>\
                    <th>频道名称</th>\
                    <th>任务成功数</th>\
                    <th>成功率</th>\
                    <th>开始时间</th>\
                    <th>结束时间</th>%s\
                </tr></table>'
        t_info = ''

        t_client = u'<tr><td>%s</td>' % time.strftime('%Y-%m-%d', result_chosen['create_time'].timetuple())
        t_channel_name = '<td>'
        t_success_number = '<td>'
        t_success_rate = '<td>'
        t_start_time = '<td>'
        t_end_time = '<td>'
        for channel_info in result_chosen.values():
            if isinstance(channel_info, dict):
                t_channel_name += u'%s<br>' % (channel_info['channel_name'])
                t_success_number += u'%s<br>' % (int(channel_info['count']))
                t_success_rate += u'%.6f%%<br>' % (channel_info['success_rate'] * 100)
                t_start_time += u'%s<br>' % (channel_info['start'][11:])
                t_end_time += u'%s<br>' % (channel_info['end'][11:])

        t_client += (t_channel_name + '</td>' + t_success_number + '</td>' + t_success_rate + '</td>' + t_start_time + '</td>' + t_end_time + '</td>')
        t_info += (t_client + '</tr>')

        content += table % t_info
        self.write(content)
        # send_email(to_add, 'Vipshop Preload Info Group By Channels', content)
        # self.write({'msg': 'email has sent!', 'code': 200})
        

@func_lock
def check_task():
    '''
    检查任务
    '''
    #@tornado.web.authenticated
    now = datetime.datetime.now()
    now_date_s = now.strftime('%Y-%m-%d')
    print '---check_task start---', now
    #检查每日任务
    everyday_tasks = preload_b_e.find()
    for e_t in everyday_tasks:
        e_start_time = e_t['start_time']
        e_start_hour , e_start_min = e_start_time.split(':')
        if now.hour == int(e_start_hour) and now.minute == int(e_start_min):
            #创建定时任务
            resource_url = e_t['resource_url'].replace('$date', now_date_s)
            preload_b.insert({'username':e_t['username'],'start_datetime':now,'created_time':now,'resource_url':resource_url,'group_detail':e_t['group_detail'], 'run_datetime': '', 'finish_datetime':'', 'concurrency':e_t['concurrency'],'e_id':e_t['_id']})


    tasks = preload_b.find({'run_datetime':"","start_datetime":{"$lte":now}})
    to_run = []
    for task in tasks:
        task_id = task['_id']
        old_res = preload_b_result.find({'task_id':task_id}).count()
        #2次检查
        if old_res > 0:
            continue
        to_run.append(task)

    #print to_run

    for t in to_run:
        send(t)
        db_update(preload_b, {'_id': ObjectId(t['_id'])}, {"$set":{"run_datetime":now}})

    print '---check_task start over---'


@func_lock
def check_task_to_email():
    '''
    检查任务并发邮件
    '''
    now = datetime.datetime.now()
    min_datetime = now - datetime.timedelta(minutes=10)

    tasks = preload_b.find({"run_datetime":{"$lte":now},"finish_datetime":""})
    #to_add = ['junyu.guo@chinacache.com']
    to_add = EMAIL_ADD

    for t in tasks:
        task_id = t['_id']
        username = t['username']
        content = u'Hi,ALL:<br/><br/>%s 预加载任务执行中 情况如下~<br/>\n' %(username)
        table = u'<table border="1">\n<tr><th>client</th><th>server_ip</th><th>success num</th><th>error num</th><th>404 num</th><th>total num</th><th>duration</th><th>error</th></tr>\n%s</table>'
        smail_task = preload_b_result.find({'task_id':str(task_id), 'update_datetime':{'$lte':now,'$gt':min_datetime}})
        if smail_task.count() == 0:
            continue
        _tbody = ''
        for s in smail_task:
            t_info = u'<tr><td>%s</td><td style="text-align:center">%s</td><td style="text-align:center">%s</td> <td style="text-align:center">%s</td><td style="text-align:center">%s</td> <td style="text-align:center">%s</td> <td style="text-align:center">%s</td> <td style="text-align:center">%s</td></tr>\n'%(s['client_ip'],s['server_ip'], s['success_num'],s['error_num'],s['not_found_num'],s['total_num'],s['duration'],s['send_error'] )
            _tbody += t_info
        content += table%(_tbody)
        send_email(to_add, 'preload task info', content)

class UserConfig(BaseHandler):
    '''
    用户界面管理
    '''
    @tornado.web.authenticated
    def get(self):
        login_name,authority=get_login_name(self)
        author_secure = get_login_author_secure(self)
        res= get_all_conf(col=preload_b_admin)
        self.render('user_conf.html', author_secure=author_secure,query_id='',loginname=login_name,authority=authority, all_conf=res['all_conf'], totalpage=res['totalpage'],c_page=0)

    def post(self):
        login_name,authority=get_login_name(self)
        author_secure = get_login_author_secure(self)
        query = {}
        query_id = self.get_argument('query_id', '')
        if query_id:
            query = {'$or':[{'username':query_id}]}
        c_page = int(self.get_argument('c_page', 0))
        res = get_all_conf(c_page, query, col=preload_b_admin)
        self.render('user_conf.html', author_secure=author_secure,query_id=query_id, loginname=login_name,authority=authority,all_conf=res['all_conf'], totalpage=res['totalpage'],c_page= c_page)

class UserConfigAdd(BaseHandler):
    '''
    用户添加界面
    '''
    @tornado.web.authenticated
    def get(self):
        login_name,authority=get_login_name(self)
        author_secure = get_login_author_secure(self)
        if author_secure=='admin':
            self.render('user_conf_add.html',author_secure=author_secure,loginname=login_name,authority=authority)
        else:
            self.redirect('/user_conf')

    def post(self):
        login_name,author=get_login_name(self)
        author_secure = get_login_author_secure(self)
        authority = self.get_arguments('authority') 
        user = self.get_argument('user', '')
        author=''
        author_all=''
        for line in authority:
            if line=='admin':
                author='admin'
            author_all=author_all+line+','
        author_all=author_all[:-1]

        if not user:
            return self.write(error_res('Please put user'))

        if not authority:
            return self.write(error_res('Please put authority'))
        print user
        print authority
        is_had = preload_b_admin.find({'username':user}).count()
        print is_had
        if is_had > 0:
            return self.write(error_res('This UserConfig had already added'))
        if author=='admin':
            preload_b_admin.insert({'username':user,'power':'admin','created_time':datetime.datetime.now()})
        else:
            preload_b_admin.insert({'username':user,'power':author_all,'created_time':datetime.datetime.now()})
        
        self.redirect('/user_conf')

class UserConfigDel(BaseHandler):
    '''
    用户配置删除
    '''
    @tornado.web.authenticated
    def get(self, conf_id):
        login_name,authority=get_login_name(self)
        author_secure = get_login_author_secure(self)
        info = preload_b_admin.find_one({'_id':ObjectId(conf_id)})
        if not info:
            return self.write(error_res('This UserConfig had already deleted'))
        try:
            preload_b_admin.remove({'_id':ObjectId(conf_id)})
        except Exception,e:
            print 'UserConfig del is %s' %(e)            

        self.redirect('/user_conf') 
class NotFoundHandler(BaseHandler):
    def get(self):
        self.write_error(404)
    def write_error(self, status_code, **kwargs):
        if status_code == 404:
            self.render('404.html')
        elif status_code == 500:
            self.render('500.html')
        else:
            self.write('error:' + str(status_code))


def make_app():
    return tornado.web.Application([
        (r"/", Login),
        (r"/login", Login),
        (r"/logout", Logout),
        (r"/auth", auth),
        (r"/user_conf/del/([a-zA-Z0-9]+)", UserConfigDel),
        (r"/user_conf", UserConfig),
        (r"/user_conf/add", UserConfigAdd),
        (r"/tasks", Tasks),
        (r"/task/add", TaskInit),
        (r"/task/del/([a-zA-Z0-9]+)", TaskDel),
        (r"/task/change/([a-zA-Z0-9]+)", TaskChange),
        (r"/task/detail/([a-zA-Z0-9]+)", TaskDetail),
        (r"/task/api/update", TaskApiUpdate),
        (r"/everyday/tasks", EveryDayTasks),
        (r"/everyday/task/change/([a-zA-Z0-9]+)", EveryDayTaskChange),
        (r"/everyday/task/del/([a-zA-Z0-9]+)", EveryDayTaskDel),
        (r"/everyday/tasks/total", TotalCount2Db),
        (r"/everyday/tasks/branch", BranchCount2Db),
        (r"/everyday/tasks/gather", DataGathering),
        (r"/everyday/tasks/mail", MailGatheredData),
        (r".*", NotFoundHandler),
        ], **settings)


def run(port):
    app = make_app()
    app.listen(port)
    # tornado.ioloop.PeriodicCallback(check_task, 1000*60).start()
    # tornado.ioloop.PeriodicCallback(check_task_to_email, 1000*60*5).start()
    tornado.ioloop.IOLoop.current().start()


if __name__ == "__main__":
    # define('port', default=9000, help='run on this port', type=int) # 31 port 8000 occupied
    define('port', default=8000, help='run on this port', type=int)
    tornado.options.parse_command_line()
    run(options.port)
