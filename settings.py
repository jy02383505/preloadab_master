# -*- coding: utf-8 -*-
from pymongo import *
import os, redis

M_CONNECT = MongoClient("mongodb://localhost:27017/bermuda")
# M_CONNECT = MongoClient("mongodb://bermuda:bermuda_refresh@223.202.52.83:27018/bermuda")
#M_CONNECT = MongoClient("mongodb://bermuda:bermuda_refresh@172.16.11.190:27018,172.16.21.205:27018,172.16.21.198:27018/bermuda?replicaSet=bermuda_db")
#REDIS_INFO = ['172.16.21.205' ,6379]
# REDIS_INFO = ['223.202.52.82' ,6379]
REDIS_INFO = ['localhost' ,6379]
M_DB = M_CONNECT['bermuda']
REDIS_CONNECT =  redis.Redis(host=REDIS_INFO[0], port=REDIS_INFO[1], db=0, password="bermuda_refresh")
TEMPLATE_PATH=os.path.join(os.path.dirname(__file__),"templates")
STATIC_PATH=os.path.join(os.path.dirname(__file__),"static")
EMAIL_ADD = ['junyu.guo@chinacache.com', 'qingxu.deng@chinacache.com']
SUCCESS_EMAIL_ADD = ['yanming.liang@chinacache.com']
DEBUG = True
CLIENT_NOW="testpreloadab103"
