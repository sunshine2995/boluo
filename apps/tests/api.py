#!/usr/bin/env python
# encoding: utf8
import sys
import os
import urllib
import urllib2
import json
from apps.member.models import Member
from apps.dbinstance import db
from apps import create_app

sys.path[0] = os.path.normpath(os.path.join(sys.path[0], '../../'))
values = {'name': '123456'}
url = 'http://localhost:8000/v1/member/register'


def http_get(values, url):
    vpath = urllib.urlencode(values)
    url = url + '?' + vpath
    response = urllib2.urlopen(url)  # 发送页面请求
    return response.read()  # 获取服务器返回的页面信息


def http_post(values, url):
    jdata = json.dumps(values, ensure_ascii=False).encode('utf-8')
    req = urllib2.Request(url, jdata)  # 生成页面请求的完整数据
    req.add_header('Content-Type', 'application/json')
    response = urllib2.urlopen(req)  # 发送页面请求
    return response.read()  # 获取服务器返回的页面信息


def test():
    app = create_app('config')
    db.init_app(app)
    member = Member(name='mlj')
    print member
    db.session.add(member)
    db.session.commit()


if __name__ == '__main__':
    # print http_get(values, url)
    test()
