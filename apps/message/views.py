#!/use/bin/env python
# -*- coding: UTF-8 -*-

import redis
from bs4 import BeautifulSoup
from apps.utils import toolkit, aliyunsdkcore
from apps.utils.CCPRestSDK import REST
from config import ACCOUNT_SID, ACCOUNT_TOKEN,\
                   APP_ID, SERVER_IP, SERVER_PORT, SOFT_VERSION, BOLUO_URL, AUTO_PRODUCT_URL
from random import randint
from hashlib import md5
from apps.config import PUBLIC_KEY
from flask import request, render_template
from apps import app
from apps.dbinstance import db
from apps.member.models import Member,Member_real_info
from apps.news.models import News
from apps.utils import toolkit
from sqlalchemy import and_, or_
from apps.message.models import Push_info
from datetime import datetime



@app.route('/v1/verify/code/get', methods=['GET', 'POST'])
def send_verify_code():
    # 初始化REST SDK
    to_phone = request.form.get('phone')
    tempId = request.form.get('tem_id')
    key = request.form.get('key')
    response_data = {}

    mykey = '%s%s' % (PUBLIC_KEY, to_phone)
    if md5(mykey).hexdigest() != key:
        response_data["code"] = u"10003"
        response_data["desc"] = u"验证码发送失败"
        return toolkit.response(response_data, 200, None, True)

    if str(request.user_agent) == 'Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; WOW64; Trident/5.0)':
        response_data["code"] = u"10000"
        response_data["desc"] = u"验证码发送成功"
        print '=========ip攻击中========'
        return toolkit.response(response_data, 200, None, True)

    if to_phone is None:
        response_data["code"]=u"10002"
        response_data["content"] = u"手机号码不能为空"
        return toolkit.response(response_data, 200, None, True)

    rest = REST(SERVER_IP,SERVER_PORT,SOFT_VERSION)
    rest.setAccount(ACCOUNT_SID,ACCOUNT_TOKEN)
    rest.setAppId(APP_ID)
    redisClient = redis.StrictRedis(host='127.0.0.1',port=6379, db=0, password='1234qweP')
    verify_code = randint(100000,999999)
    key = "%s_%s" % (to_phone, verify_code)
    key1 = '%s_switch' % to_phone


    try:
        try:
            if not redisClient.get(key):
                redisClient.set(key, str(verify_code))
                redisClient.expire(key, 300)

            if not redisClient.get(key1):
                redisClient.set(key1, '1')
                redisClient.expire(key1, 500)
            else:
                redisClient.set(key1, '2')
        except(ValueError, TypeError):
            raise
        value1 = redisClient.get(key1)

        datas = [verify_code]
        tempId = 42447
        if value1 == '1':
            rest.sendTemplateSMS(to_phone,datas,int(tempId))
            print 'success for sms yuntongxun !!!!!!!!!!!'
        elif value1 == '2':
            aliyunsdkcore.AliyunMonitor().do_request(to_phone, verify_code)
            print 'success for sms aliyun !!!!!!!!!!!'
        response_data["code"] = u"10000"
        response_data["desc"] = u"验证码发送成功"
        return toolkit.response(response_data, 200, None, True)
    except:
        response_data["code"] = u"10004"
        response_data["desc"] = u"您发送的频率过快,请稍候再试"
        return toolkit.response(response_data, 200, None, True)


@app.route('/v1/verify/code/match', methods=['GET', 'POST'])
def match_verify_code():

    phone = request.form.get("phone")
    verify_code = request.form.get("verify_code")

    key = phone + "_" + verify_code 
    response_data = {}
    response_data["content"] = {}
    redisClient = redis.StrictRedis(host='127.0.0.1',port=6379, db=0, password='1234qweP')
    try:
        ttl = redisClient.ttl(key)
        if not ttl:
            response_data["code"]=u"10001"
            response_data["desc"] = u"验证码已经过期"
            return toolkit.response(response_data, 200, None, True)
        else:
            value = redisClient.get(key)
            print value
            print verify_code
            if value == verify_code:    
                response_data["code"]=u"10000"
                response_data["desc"] = u"验证码验证成功"
                return toolkit.response(response_data, 200, None, True)
            else:
                response_data["code"]=u"10002"
                response_data["desc"] = u"验证码验证失败"
                return toolkit.response(response_data, 200, None, True)
    except:
        response_data["code"]=u"10003"
        response_data["desc"] = u"您发送的频率过快,请稍候再试"
        return toolkit.response(response_data, 200, None, True)


def verify_code(phone, verify_code):
    key = phone + "_" + verify_code
    response_data = {}
    response_data["content"] = {}
    redisClient = redis.StrictRedis(host='127.0.0.1',port=6379, db=0, password='1234qweP')
    try:
        ttl = redisClient.ttl(key)
        if not ttl:
            response_data["code"]=u"10001"
            response_data["desc"] = u"验证码已经过期"
        else:
            value = redisClient.get(key)
            print value
            print verify_code
            if value == verify_code:
                response_data["code"]=u"10000"
                response_data["desc"] = u"验证码验证成功"
            else:
                response_data["code"]=u"10002"
                response_data["desc"] = u"验证码验证失败"
    except:
        response_data["code"]=u"10003"
        response_data["content"] = u"未知异常"
    return response_data


@app.route('/v1/message/address/upload/<phone>', methods=['GET', 'POST'])
def verify_address(phone):
    response_data = {'content':{}}
    member = Member.query.filter_by(phone=phone).first()

    if member.isblack == 'Sync':
        response_data["code"] = u"10002"
        response_data["content"]={}
        response_data["desc"] = u"您的账户已被迁移到菠萝理财存管版，请用菠萝理财存管版登录！"
        return toolkit.response(response_data, 200, None, True)

    if member is None:
        response_data["code"] = u"10001"
        response_data["desc"] = u"用户不存在"
        return toolkit.response(response_data, 200, None, True)
    member_id = str(member.id).replace('-', '')
    member_real_info_people = Member_real_info.query.filter_by(member_id=member_id).first()

    people_name= request.form.get('people_name')
    people_phone = request.form.get('people_phone')
    people_address = request.form.get('people_address')

    if people_name and people_phone and people_address:
        member_real_info_people.people_name = people_name
        member_real_info_people.people_phone=people_phone
        member_real_info_people.people_address=people_address
        db.session.merge(member_real_info_people)
        db.session.commit()

        response_data["code"] = u"10000"
        response_data["desc"] = u"成功"
        return toolkit.response(response_data, 200, None, True)
    else:
        response_data['content']["name"] = member_real_info_people.people_name if member_real_info_people.people_name else ''
        response_data['content']["phone"] = member_real_info_people.people_phone if member_real_info_people.people_phone else ''
        response_data['content']["address"] = member_real_info_people.people_address if member_real_info_people.people_address else ''
        response_data["code"] = u"10000"
        response_data["desc"] = u"成功"
        return toolkit.response(response_data, 200, None, True)


@app.route('/v1/verify/action/update/android', methods=['GET', 'POST'])
def action_update():
    response_data = {'code': '10000', 'desc': '请求成功'}
    response_data['data'] = {}
    response_data['data']['code'] = '70'
    response_data['data']['status'] = '1'
    response_data['data']['constraint_code'] = '61'
    response_data['data']['constraint_status'] = '0'
    response_data['data']['content'] = '新版本上线!'
    response_data['data']['url'] = 'http://www.boluolicai.com:8016/android_apk/boluolicai70.apk'
    response_data['data'] = [response_data['data']]
    response_data['is_maintain'] = '0'
    response_data['maintain_content'] = 'hello'
    return toolkit.response(response_data, 200, None, True)


@app.route('/v1/<name_or_phone>/message/box', methods=['GET','POST'])
def message_box(name_or_phone):
    response_data = {}

    # m = Member.query.filter(or_(Member.name == name_or_phone, Member.phone == name_or_phone)).first()
    # if m is None:
    #     response_data["code"] = u"10001"
    #     response_data["desc"] = u"用户不存在"
    #     response_data['content'] = {}
    #     return toolkit.response(response_data, 200, None, True)
    # member_id = str(m.id).replace('-','')
    message_list = []
    messages = Push_info.query.filter_by(state=3).order_by(Push_info.push_date.desc()).all()
    if messages is None:
        pass
    else:
        for message in messages:
            push_time = datetime.strftime(message.push_date,'%Y-%m-%d %H:%M:%S')
            message_url = BOLUO_URL + '/v1/messagebox/detail/' + message.id
            res_dict = {'title': message.theme, 'url': message_url, 'date': push_time,'content':message.content}
            message_list.append(res_dict)
    response_data['content'] = message_list
    response_data['code'] = u'10000'
    response_data['desc'] = u'成功'
    return toolkit.response(response_data, 200, None, True)


@app.route('/v1/messagebox/detail/<id>', methods=['GET','POST'])
def message_box_detail(id):
    response_data = {}
    message = Push_info.query.filter_by(id=id).first()
    response_data['title'] = message.theme
    response_data['content'] = message.content
    response_data['date'] = message.push_date
    return render_template('html5/xiaoxixq.html',response_data=response_data)


# 首页消息弹窗
@app.route('/v1/home_pop', methods=['GET', 'POST'])
def message_home_pop():
    response_data = {}
    response_data["code"] = u"10000"
    response_data["desc"] = u"请求成功"
    response_data["content"] = {}

    # 弹窗图片地址与h5地址
    con = News.query.filter(and_(News.title==u'首页消息弹窗', News.sortid == 33)).first()
    if con:
        img = con.image
        response_data["content"]["img"] = AUTO_PRODUCT_URL + img
        con.content = con.content.strip()
        try:
            soup = BeautifulSoup(con.content, "html.parser")
            url = soup.body.string
            if len(url) <= 1:
                url = ''
        except:
            url = con.content
        response_data["content"]["url"] = url
        response_data["content"]["open_sign"] = 1

    return toolkit.response(response_data, 200, None, True)

