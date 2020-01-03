# -*- coding: utf-8 -*-
from settings import M_DB, REDIS_CONNECT
import pymongo, math ,datetime,socket
import simplejson as json

RETRY_COUNT = 3

def get_login_name(self):
    '''
    通用的获得登录用户名和权限
    '''
    loginname_authority=self.get_secure_cookie("login")
    login_name=loginname_authority.split(':')[0]
    authority=loginname_authority.split(':')[1]
    return login_name,authority
def get_login_author_secure(self):
    '''
    通用的获得登录用户名和权限
    '''
    loginname_author_secure=self.get_secure_cookie("author_cookie")
    return loginname_author_secure

def get_all_conf(page=0, query={}, col=M_DB.control_conf):
    '''
    根据页数获取配置
    '''
    cf = col
    per_page = 30
    totalpage = int(math.ceil(cf.find(query).count(True)/(per_page*1.00)))
    all_conf = [u for u in cf.find(query).sort('created_time', pymongo.DESCENDING).skip(page*per_page).limit(per_page)]
    print all_conf
    return {'all_conf':all_conf, 'totalpage': totalpage}

def get_all_data(page=0, query={}, col=M_DB.preload_b):
    '''
    获取所有数据
    '''
    cf = col
    per_page = 10
    totalpage = int(math.ceil(cf.find(query).count(True)/(per_page*1.00)))
    all_conf = [u for u in cf.find(query).sort('created_time', pymongo.DESCENDING).skip(page*per_page).limit(per_page)]
    return {'all_data':all_conf, 'totalpage': totalpage}


def db_update(collection,find,modification):
    for retry_count in range(RETRY_COUNT):
        try:
            ret = collection.update(find, modification)
            if ret.get("updatedExisting") == True and ret.get("n") > 0:
                return
        except Exception, ex:
            print "db_update error, message=%s" % (ex)

def error_res(msg):

     return '<html><script type="text/javascript">alert("%s");history.go(-1)</script></html>' %(msg)



def func_lock(fn):
     '''
     方法锁
     '''
     def _func_lock():
         now = datetime.datetime.now()
         key = "preload_b_lock:%s_%s"%(fn.__name__, now.strftime('%Y-%m-%d_%H:%M'))
         hostname = socket.gethostname()
         #print 'hostname:%s  func:%s'%(hostname, fn.__name__)
         #fn()
         if REDIS_CONNECT.setnx(key, hostname):
             REDIS_CONNECT.expire(key, 60)
             print 'hostname:%s  func:%s'%(hostname, fn.__name__)
             fn()
         else:
             print '%s fn: %s start~but not me' %(now, fn.__name__)
             pass

     return _func_lock
