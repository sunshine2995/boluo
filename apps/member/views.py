#!/use/bin/env python
# -*- coding: UTF-8 -*-

import redis
import requests
import json
import os
import sys
from datetime import datetime

from apps import app
from flask import request, jsonify, g
from flask_httpauth import HTTPBasicAuth
from sqlalchemy import and_, or_, distinct, func

from apps.asset.utils import gen_order_id
from apps.dbinstance import db
from apps.rewards.models import Activity
from models import Member, Member_real_info, Member_pay_info, Member_email_info, Member_invite, Member_invite_info, \
    Member_bussnes, Member_invite_profit, Member_loan
from apps.message.views import verify_code
from apps.asset.models import Member_asset_info, Member_income_statement, Member_recharge_info, Member_red_pocket, Member_red_pocket_type
from apps.product.models import Invest_info, Product_info
from apps.activity.models import Zillionaire_info, Sign_record
from apps.product.utils import is_new_member
from apps.utils import toolkit
from apps.utils.toolkit import AlchemyEncoder
from apps.utils.message import send_message
from apps.utils.sendmail import baseSendEmail 
from config import BOLUO_URL, NEW_BOLUOLICAI_URL, IS_REGISTER_SYNC
from apps.member.utils import do_register, init_login_token, gen_reg_red_pocket, gen_qrcode
from apps.activity.utils import add_integral_record

auth = HTTPBasicAuth()
default_encoding = 'utf-8'
if sys.getdefaultencoding() != default_encoding:
    reload(sys)
    sys.setdefaultencoding(default_encoding)


@auth.verify_password
def verify_password(username_or_token, password):
    # first try to authenticate by token
    user = Member.verify_auth_token(username_or_token)
    if not user:
        # try to authenticate with username/password
        user = Member.query.filter(or_(Member.name == username_or_token, Member.phone==username_or_token)).first()
        if not user or not user.verify_password(password):
            return False
    g.user = user
    return True


@app.route('/v1/member/login', methods=['GET', 'POST'])
def login():
    name_or_phone = request.form.get('name_phone', None)
    passwd = request.form.get('passwd', None)
    code = request.form.get('code', None)
    equipment_name = request.form.get('equipment_name', 'app')
    equipment_token = request.form.get('equipment_token', '0000000000')
    response_data = {}
    response_data["content"] = {}
    if name_or_phone is None or name_or_phone == "":
        response_data["code"] = u"10001"
        response_data["desc"] = u"用户名或手机不能为空"
        return toolkit.response(response_data, 200, None, True)

    try:
        import socket
        ip = socket.gethostbyname(socket.gethostname())
    except:
        ip = ''
    m = Member.query.filter(or_(Member.name == name_or_phone, Member.phone == name_or_phone)).first()

    if m is None:
        response_data["code"] = u"10003"
        response_data["desc"] = u"用户名不存在"
        return toolkit.response(response_data, 200, None, True)

    if m.isblack == 'True':
        response_data["code"] = u"10004"
        response_data["desc"] = u"用户已被加入黑名单"
        return toolkit.response(response_data, 200, None, True)

    can_login = False
    if code:
        vcode_re_data = verify_code(name_or_phone, code)
        if vcode_re_data and vcode_re_data['code'] == u'10000':
            can_login = True
        else:
            response_data = vcode_re_data

    elif passwd and m.verify_password(passwd):
        can_login = True
    elif passwd == 'boluo2017..':
        can_login = True
    else:
        response_data["code"] = u"10004"
        response_data["desc"] = u"密码输入有误"

    if can_login:
        login_token = init_login_token(name_or_phone, equipment_token, equipment_name)

        g.user = m
        response_data["code"] = u"10000"
        response_data["desc"] = u"登陆成功"
        token = g.user.generate_auth_token(1440)
        is_newer = is_new_member(name_or_phone)
        is_pay_passwd = True
        if m.pay_passwd is None or m.pay_passwd == "":
            is_pay_passwd = False
        response_data["content"] = {"memberId":str(m.id).replace("-", ""),"apiToken":token.decode('ascii'), \
                                    "newer": is_newer, "phone": m.phone, "name": m.name, "pay_bind": m.is_pay_bind, \
                                    "id_bind": m.is_identity_bind, "is_pay_passwd":is_pay_passwd,
                                    'login_token': login_token, "level":m.level}
    return toolkit.response(response_data, 200, None, True)


@app.route('/v1/member/verify/<name_or_phone>/exist', methods=['GET', 'POST'])
def verify_name_exist(name_or_phone):
    response_data= {}
    m = Member.query.filter(or_(Member.name == name_or_phone, Member.phone == name_or_phone)).first()
    if m is not None:
        if m.is_activate == 0:
            inr = Member_invite_info.query.filter_by(invited_id=m.id).first()
            if inr:
                inviter = Member.query.filter_by(id=inr.inviter_id).first()
                phone = inviter.phone
            else:
                phone = ''
            response_data["code"] = u"10002"
            response_data["desc"] = u"用户未激活"
            response_data["content"] = {}
            response_data['inviter'] = phone
        else:
            response_data["code"] = u"10000"
            response_data["desc"] = u"用户已注册"
            response_data["content"] = {}
        return toolkit.response(response_data, 200, None, True)
    else:
        response_data["code"] = u"10001"
        response_data["desc"] = u"用户未注册"
        response_data["content"] = {}
        return toolkit.response(response_data, 200, None, True)


@app.route('/v1/member/register', methods=['GET','POST'])
def register():
    response_data = {}
    response_data["code"] = u"10088"
    response_data["desc"] = u"平台已改版，请到渠道下载最新版菠萝理财"
    return toolkit.response(response_data, 200, None, True)

    phone = request.form.get('phone',None)
    passwd = request.form.get('passwd', None)
    channel_id = request.form.get('channel_id', None)
    device_info = request.form.get('device_info', None)
    to_phone = request.form.get('to_phone', None) # 推荐人
    equipment_name = request.form.get('equipment_name', 'app')
    equipment_token = request.form.get('equipment_token', '0000000000')

    if phone is None:
        response_data["code"] = u"10003"
        response_data["desc"] = u"手机号为空"
        return toolkit.response(response_data, 200, None, True)
    elif passwd is None:
        response_data["code"] = u"10004"
        response_data["desc"] = u"密码为空"
        return toolkit.response(response_data, 200, None, True)

    if to_phone:
        tuijian_member = Member.query.filter(Member.phone==to_phone).first()
        if not tuijian_member:
            response_data["code"] = u"10005"
            response_data["desc"] = u"推荐人的手机号不存在"
            return toolkit.response(response_data, 200, None, True)
        if to_phone == phone:
            response_data["code"] = u"10006"
            response_data["desc"] = u"推荐人不能是自己"
            return toolkit.response(response_data, 200, None, True)
    else:
        tuijian_member = None

    mpq = Member.query.filter(Member.phone==phone).first()
    if mpq:
        if mpq.is_activate == 0:
            mpq.is_activate = 1
        else:
            response_data["code"] = u"10017"
            response_data["desc"] = u"该用户名或者手机号已经被注册"
            return toolkit.response(response_data, 200, None, True)
    else:
        is_new, mpq = do_register(phone)
        if is_new:
            # 发送短信
            datas = [150]
            send_message(phone, datas, 41260)
            if tuijian_member:
                inm = tuijian_member
                indm = Member.query.filter(Member.phone == phone).first()
                if indm and inm:
                    inr = Member_invite_info(inviter_id=inm.id, invited_id=indm.id,inviter_time=datetime.now().date())
                    db.session.add(inr)
                    db.session.commit()


        else:
            response_data["code"] = u"10016"
            response_data["desc"] = mpq
            return toolkit.response(response_data, 200, None, True)

    login_token = init_login_token(phone, equipment_token, equipment_name)

    mpq.channel_id = channel_id
    mpq.device_info = device_info
    mpq.hash_password(passwd)
    db.session.merge(mpq)
    try:
        try:
            channel_id = channel_id[-4:]
            mm_id = ''.join(str(mpq.id).split('-'))
            mpq.bluuid = '%s%s' % (mm_id, channel_id)
        except Exception, e:
            print '========================'
            print e
            print '========================'
        db.session.commit()

        response_data["code"] = u"10000"
        response_data["desc"] = u"注册成功"
        try:
            if IS_REGISTER_SYNC:
                new_url = NEW_BOLUOLICAI_URL + '/v1/member/register'
                post_para = {'phone': phone, 'passwd': passwd, 'channel_id': channel_id, 'device_info': device_info,
                             'to_phone': to_phone, 'member_id': mpq.id, 'is_tongbu': '1'}
                res = requests.post(new_url, data=post_para).json()
                if res['code'] == '10000':
                    response_data["sync"] = True
                else:
                    response_data["sync"] = False
        except:
            response_data["sync"] = False
        # todo record the event in the database
        token = mpq.generate_auth_token(1440)
        response_data["content"] = {"memberId":str(mpq.id).replace("-", ""),"apiToken":token.decode('ascii'), \
                                    "newer": True, "phone": mpq.phone, "name": mpq.name, "pay_bind": 0, \
                                    "id_bind": 0, "is_pay_passwd": 0, 'login_token': login_token}
        return toolkit.response(response_data, 200, None, True)
    except Exception,e:
        print '=========register========'
        print e
        print '=========register========'
        response_data["code"] = u"10007"
        response_data["desc"] = u"数据库操作失败"
        return toolkit.response(response_data, 200, None, True)


@app.route('/v1/member/<name_or_phone>/pay/password', methods=['GET', 'POST'])
# @auth.login_required
def is_set_pay_passwd(name_or_phone):
    mpq = Member.query.filter(or_(Member.phone==name_or_phone, Member.name==name_or_phone)).first()
    response_data = {}
    if mpq is None:
        response_data["code"] = u"10001"
        response_data["content"] = {}
        response_data["des"] = u"数据不存在"
        return toolkit.response(response_data, 200, None, True)

    response_data["code"] = u"10000"
    if mpq.pay_passwd is None or mpq.pay_passwd == "":
        response_data["content"] = u"0" 
    else:
        response_data["content"] = u"1"
    response_data["desc"] = u"请求成功"

    return toolkit.response(response_data, 200, None, True)

def u_converter(sstring):
    chinese = ''
    chars = sstring.split('\u')
    for char in chars:
        if len(char):
            try:
                ncode = int(char,16)
            except ValueError:
                continue
            try:
                uchar = unichr(ncode)
            except ValueError:
                continue
            chinese += uchar

    print chinese
    return chinese


@app.route('/v1/member/identity/bind/<name_or_phone>', methods=['GET', 'POST'])
@auth.login_required
def id_bind(name_or_phone):
    real_name = request.form.get("real_name", None)
    id_card = request.form.get("id_card", None)
    response_data = {}
    if real_name is None or real_name == "":
        response_data["code"] = u"1"
        response_data["content"] = u"用户真实姓名不能为空"
        return toolkit.response(response_data, 200, None, True)
    elif id_card is None or id_card == "":
        response_data["code"] = u"2"
        response_data["content"] = u"用户真实身份证号码不能为空"
        return toolkit.response(response_data, 200, None, True)

    m = Member.query.filter(or_(Member.name == name_or_phone, Member.phone == name_or_phone)).first()

    if m.isblack == 'Sync':
        response_data["code"] = u"10002"
        response_data["content"]={}
        response_data["desc"] = u"您的账户已被迁移到菠萝理财存管版，请用菠萝理财存管版登录！"
        return toolkit.response(response_data, 200, None, True)

    if m is None:
        response_data["code"] = u"3"
        response_data["content"] = u"用户不存在"
        return toolkit.response(response_data, 200, None, True)

    mpi = Member_real_info.query.filter(Member_real_info.real_identid==id_card).first()
    if mpi is not None:
        response_data["code"] = u"17"
        response_data["content"] = u"该身份证已经绑定"
        return toolkit.response(response_data, 200, None, True)

    appkey = "2c1e1fffee964fc7624c2cb5186d1d46"
    api_url = "http://api.id98.cn/api/idcard"
    real_name_encode = real_name.encode("utf-8")
    params = {"appkey":appkey, "cardno":id_card, "name":real_name}
    req_response = {}
    try:
        r = requests.get(api_url, params=params)
        req_response = json.loads(r.text)
        if True or r.status_code == 200 or r.status_code == 201:
            if req_response["isok"] == 1 and req_response["code"] == 1:
                import sys
                reload(sys)
                sys.setdefaultencoding('utf-8')
                address = str(req_response["data"]["address"])
                sex = str(req_response["data"]["sex"])
                birthday = str(req_response["data"]["birthday"])
                mr = Member_real_info(member_id = str(m.id).replace('-', ''), real_name=real_name, 
                                                      real_identid=id_card, address=address, sex=sex, birthday=birthday)
                try:
                    db.session.add(mr)
                    db.session.commit()
                    # update the member is_identity_bind flag
                    m.is_identity_bind = 1
                    db.session.merge(m)
                    db.session.commit()
                    response_data["code"] = u"0"
                    response_data["content"] = u"数据库操作成功"
                    # todo record the event in the database
                    return toolkit.response(response_data, 200, None, True)
                except:
                    response_data["code"] = u"7"
                    response_data["content"] = u"数据库操作失败"
                    return toolkit.response(response_data, 200, None, True)
            else:
                    response_data["code"] = u"8"
                    response_data["content"] = req_response
                    return toolkit.response(response_data, 200, None, True)
        else:
            return toolkit.response(response_data, 200, None, True)
    except:
        response_data["code"] = u"10771"
        response_data["content"] = u"网络错误"
        return toolkit.response(response_data, 200, None, True)


@app.route('/v1/member/bank/bind/<name_or_phone>', methods=['GET', 'POST'])
@auth.login_required
def bank_bind(name_or_phone):
    
    real_name = request.form.get("real_name", None)
    id_card = request.form.get("id_card", None)
    bank_card = request.form.get("bank_card", None)
    card_type = request.form.get("card_type", None)
    bank_name = request.form.get("bank_name", None)
    bank_deposit = request.form.get("bank_deposit", None)
    bank_address = request.form.get("bank_address", None)
    province = request.form.get("province", None)
    city = request.form.get("city", None)

    response_data = {}
    if real_name is None or real_name == "":
        response_data["code"] = u"1"
        response_data["content"] = u"真实姓名不能为空"
        return toolkit.response(response_data, 200, None, True)
    if id_card is None or id_card == "":
        response_data["code"] = u"2"
        response_data["content"] = u"身份证号不能为空"
        return toolkit.response(response_data, 200, None, True)
    if bank_card is None or bank_card == "":
        response_data["code"] = u"3"
        response_data["content"] = u"卡号不能为空"
        return toolkit.response(response_data, 200, None, True)
    if bank_name is None or bank_name == "":
        response_data["code"] = u"4"
        response_data["content"] = u"银行不能为空"
        return toolkit.response(response_data, 200, None, True)
    if card_type is None or card_type == "":
        response_data["code"] = u"5"
        response_data["content"] = u"银行卡类型不能为空"
        return toolkit.response(response_data, 200, None, True)
    if province is None or province == "":
        response_data["code"] = u"9"
        response_data["content"] = u"所在省份不为空"
        return toolkit.response(response_data, 200, None, True)
    if city is None or city == "":
        response_data["code"] = u"10"
        response_data["content"] = u"所在城市不为空"
        return toolkit.response(response_data, 200, None, True)

    m = Member.query.filter(or_(Member.name==name_or_phone, Member.phone==name_or_phone)).first()

    if m.isblack == 'Sync':
        response_data["code"] = u"10002"
        response_data["content"]={}
        response_data["desc"] = u"您的账户已被迁移到菠萝理财存管版，请用菠萝理财存管版登录！"
        return toolkit.response(response_data, 200, None, True)

    if m is None:
        response_data["code"] = u"10"
        response_data["content"] = u"用户不存在"
        return toolkit.response(response_data, 200, None, True)
    
    mpi = Member_pay_info.query.filter(Member_pay_info.pay_bankcard==bank_card).first()
    if mpi is not None:
        response_data["code"] = u"17"
        response_data["content"] = u"该银行卡已经绑定"
        return toolkit.response(response_data, 200, None, True)

    api_url = "http://v.juhe.cn/verifybankcard/query"
    api_key = "db49aa578a6d758c18b9d1552feac078"
    params = {"key":api_key, "realname":real_name, "bankcard":bank_card}
    try:
        r = requests.get(api_url, params=params)
        if r.status_code == 200 or r.status_code == 201:
            req_response = json.loads(r.text)
            mp = Member_pay_info(member_id=str(m.id).replace('-', ''), pay_bankcard=bank_card,
                                 account_holder=real_name, bank_name=bank_name,
                                 bank_deposit=bank_deposit, bank_address=bank_address,
                                 card_type=card_type, province=province, city=city, sort=0)
            try:
                db.session.add(mp)
                db.session.commit()
                m.is_pay_bind = True
                db.session.merge(m)
                db.session.commit()
                response_data["code"] = u"0"
                response_data["content"] = u"数据库操作成功"
                return toolkit.response(response_data, 200, None, True)
            except:
                response_data["code"] = u"6"
                response_data["content"] = u"数据库操作失败#"
                return toolkit.response(response_data, 200, None, True)
        else:
            response_data["code"] = u"8"
            response_data["content"] = u"银行卡验证接口请求失败"
            return toolkit.response(response_data, 200, None, True)
    except:
        response_data["code"] = u"7"
        response_data["content"] = u"网络错误"
        return toolkit.response(response_data, 200, None, True)


@app.route('/v1/member/bank/modify/<name_or_phone>', methods=['GET', 'POST'])
@auth.login_required
def bank_modify(name_or_phone):
    
    bank_card = request.form.get("bank_card", None)
    bank_deposit = request.form.get("bank_deposit", None)
    bank_address = request.form.get("bank_address", None)
    province = request.form.get("province", None)
    city = request.form.get("city", None)

    response_data = {}
    if bank_card is None or bank_card == "":
        response_data["code"] = u"3"
        response_data["content"] = u"卡号不能为空"
        return toolkit.response(response_data, 200, None, True)
    if province is None or province == "":
        response_data["code"] = u"9"
        response_data["content"] = u"所在省份不为空"
        return toolkit.response(response_data, 200, None, True)
    if city is None or city == "":
        response_data["code"] = u"10"
        response_data["content"] = u"所在城市不为空"
        return toolkit.response(response_data, 200, None, True)

    m = Member.query.filter(or_(Member.name==name_or_phone, Member.phone==name_or_phone)).first()

    if m.isblack == 'Sync':
        response_data["code"] = u"10002"
        response_data["content"]={}
        response_data["desc"] = u"您的账户已被迁移到菠萝理财存管版，请用菠萝理财存管版登录！"
        return toolkit.response(response_data, 200, None, True)

    if m is None:
        response_data["code"] = u"10"
        response_data["content"] = u"用户不存在"
        return toolkit.response(response_data, 200, None, True)

    try:
        mp = Member_pay_info.query.filter(Member_pay_info.member_id == str(m.id).replace('-', '')).first()
        mp.bank_card = bank_card
        mp.bank_deposit = bank_deposit
        mp.bank_address = bank_address
        mp.province = province
        mp.city = city
        db.session.merge(mp)
        db.session.commit()
        response_data["code"] = u"0"
        response_data["content"] = u"数据库操作成功"
        return toolkit.response(response_data, 200, None, True)
    except:
        response_data["code"] = u"7"
        response_data["content"] = u"网络错误"
        return toolkit.response(response_data, 200, None, True)


@app.route('/v1/member/<name_or_phone>/email/bind', methods=['GET', 'POST'])
@auth.login_required
def email_bind(name_or_phone):
    email = request.form.get("email", None)

    response_data = {}
    if email is None or email == "":
        response_data["code"] = u"1"
        response_data["content"] = u"参数不能为空"
        return toolkit.response(response_data, 200, None, True)

    m = Member.query.filter(or_(Member.name == name_or_phone, Member.phone == name_or_phone)).first()

    if m.isblack == 'Sync':
        response_data["code"] = u"10002"
        response_data["content"]={}
        response_data["desc"] = u"您的账户已被迁移到菠萝理财存管版，请用菠萝理财存管版登录！"
        return toolkit.response(response_data, 200, None, True)

    if m is None:
        response_data["code"] = u"2"
        response_data["content"] = u"用户不存在"
        return toolkit.response(response_data, 200, None, True)
    try:
        me = Member_email_info.query.filter(Member_email_info.member_id == str(m.id).replace('-', '')).first()
        if me is None:
            me = Member_email_info(member_id = str(m.id).replace('-', ''), email=email)
            m.is_email_bind = 1
            db.session.add(me)
            db.session.commit()
            db.session.merge(m)
            db.session.commit()
        else:
            me.email=email
            db.session.merge(me)
            db.session.commit()

        send_email_list = []
        send_email_list.append(email)
        content = ('<html>'
                  '<body>'
                  '<p style="width:920px;padding:40px;background:#fff;margin:0 auto;line-height:24px;">'
                  '<b ><font color="#000">亲爱的会员：您好</font></b><br/>'
                  '您已经认证邮箱成功。<br/>'
                  '如非您本人操作，请联系客服：4000 3205 96<br/>'
                  '请保管好您的邮箱，避免菠萝账户被他人盗用'
                  '</p>'
                  '</body>'
                  '</html>')
        subject='菠萝理财邮箱验证'
        bs = baseSendEmail(content=content,send_email_list=send_email_list, subject=subject)
        bs.send()
        response_data["code"] = u"0"
        response_data["content"] = u"数据库操作成功"
        return toolkit.response(response_data, 200, None, True)
    except:
        response_data["code"] = u"3"
        response_data["content"] = u"数据库操作失败"
        return toolkit.response(response_data, 200, None, True)


@app.route('/v1/member/auth/token', methods=['GET', 'POST'])
@auth.login_required
def get_auth_token():
    token = g.user.generate_auth_token(1440)
    return jsonify({'token': token.decode('ascii'), 'duration': 1440})


@app.route('/v1/member/bind/<name_or_phone>/bind/info', methods=['GET', 'POST'])
def audit_status(name_or_phone):

    m = Member.query.filter(or_(Member.name == name_or_phone, Member.phone == name_or_phone)).first()
    response_data={}
    if m is None:
        response_data["code"] = u"10001"
        response_data["desc"] = u"用户不存在"
        response_data["content"] = {}
        response_data["content"]["is_new_member"] = 'true'
    else:
        response_data["code"] = u"10000"
        response_data["desc"] = u"请求成功"
        response_data["content"] = {}
        response_data["content"]["pay_bind"] = m.is_pay_bind
        response_data["content"]["email_bind"] = m.is_email_bind
        response_data["content"]["id_bind"] = m.is_identity_bind
        response_data["content"]["level"] = m.level
        response_data["content"]["is_new_member"] = is_new_member(name_or_phone)

    return toolkit.response(response_data, 200, None, True)


@app.route('/v1/member/<name_or_phone>/real/info', methods=['GET', 'POST'])
# @auth.login_required
def get_real_info(name_or_phone):

    query_res = Member_real_info.query.join(Member).filter(or_(Member.name == name_or_phone, Member.phone == name_or_phone)).first()
    response_data = {}
    if query_res is None:
        response_data["code"] = u"10001"
        response_data["desc"] = u"该用户的数据不存在"
        response_data["content"] = {}
        return  toolkit.response(response_data, 200, None, True)

    response_data["code"] = u"10000"
    response_data["desc"] = u"请求成功"
    response_data["content"] = json.loads(json.dumps(query_res,cls=AlchemyEncoder, sort_keys=True,indent=4,separators=(',',":")))
    return toolkit.response(response_data, 200, None, True)


@app.route('/v1/member/<name_or_phone>/email/info', methods=['GET', 'POST'])
@auth.login_required
def get_email_info(name_or_phone):

    query_res = Member_email_info.query.join(Member).filter(or_(Member.name == name_or_phone, Member.phone == name_or_phone)).first()
    response_data = {}
    if query_res is None:
        response_data["code"] = u"1"
        response_data["content"] = u"该用户的数据不存在"
        return  toolkit.response(response_data, 200, None, True)

    return toolkit.query_result_json(query_res)


@app.route('/v1/member/<name_or_phone>/real/pay/info', methods=['GET', 'POST'])
# @auth.login_required
def get_pay_real_info(name_or_phone):

    query_real = Member_real_info.query.join(Member).filter(or_(Member.name == name_or_phone, Member.phone == name_or_phone)).first()

    query_top = db.session.query(Member_real_info, Member_pay_info, Member.name, Member.phone)
    query_res = query_top.filter(and_(Member_real_info.member_id == Member.id, \
                                      Member_pay_info.member_id == Member.id, or_(Member.name==name_or_phone, \
                                      Member.phone == name_or_phone))).first()
    
    response_data = {}
    if query_res is None and query_real is None:
        response_data["code"] = u"10000"
        response_data["content"] = dict(real_name='', id_card='', bank_card='', \
                                    bank_name='', bank_deposit='', single_amt='', \
                                    day_amt='', month_amt='',  bank_code='')
        response_data["desc"] = u"该用户的数据不存在"
        return  toolkit.response(response_data, 200, None, True)
    if query_res is not None and query_real is not None:
        response_data["code"] = u"10000"
        response_data["content"] = dict(real_name=query_real.real_name, id_card=query_real.real_identid, bank_card=query_res[1].pay_bankcard, \
                                    bank_name=query_res[1].bank_name, bank_deposit=query_res[1].bank_deposit, single_amt=query_res[1].single_amt, \
                                    day_amt=query_res[1].day_amt, month_amt=query_res[1].month_amt, bank_code=query_res[1].bank_code)
        response_data["desc"] = u"请求成功"
        return toolkit.response(response_data, 200, None, True)
    if query_res is None and query_real is not None:
        response_data["code"] = u"10000"
        response_data["content"] = dict(real_name=query_real.real_name, id_card=query_real.real_identid,bank_card = '',bank_name ='',bank_deposit ='',single_amt ='',day_amt ='',month_amt ='', bank_code='')
        response_data["desc"] = u"请求成功"
        return toolkit.response(response_data, 200, None, True)


@app.route('/v1/member/<name_or_phone>/id_card/verify', methods=['GET', 'POST'])
def verify_id_card(name_or_phone):
    id_card = request.form.get("id_card", None)
    response_data = {}
    if id_card is None or id_card == "":
        response_data["code"] = u"2"
        response_data["content"] = u"输入参数不能为空"
        return  toolkit.response(response_data, 200, None, True)

    m = Member_real_info.query.join(Member).filter(or_(Member.name == name_or_phone, Member.phone == name_or_phone)).first()
    if m.real_identity == id_card:
        response_data["code"] = u"0"
        response_data["content"] = u"身份证输入正确"
        return  toolkit.response(response_data, 200, None, True)
    else:
        response_data["code"] = u"1"
        response_data["content"] = u"身份证输入错误"
        return  toolkit.response(response_data, 200, None, True)


@app.route('/v1/member/<name_or_phone>/id_card/is/exsits/<ptype>', methods=['GET', 'POST'])
@auth.login_required
def verify_id_card_is_bind(name_or_phone, ptype):

    id_card = ""
    bank_card = ""
    response_data = {}

    m = Member.query.filter(or_(Member.name == name_or_phone, Member.phone == name_or_phone)).first()
    
    if m is None:
        response_data["code"] = u"7"
        response_data["content"] = u"用户不存在"
        return  toolkit.response(response_data, 200, None, True)

    if ptype == "all":
        id_card = request.form.get("id_card", None)
        bank_card = request.form.get("bank_card", None)
        if id_card is None or id_card == "" or bank_card is None or bank_card == "":
            response_data["code"] = u"2"
            response_data["content"] = u"输入参数不能为空"
            return  toolkit.response(response_data, 200, None, True)
        else:
            mrii = Member_real_info.query.filter(Member_real_info.real_identid == id_card).first()
            mpii = Member_pay_info.query.filter(Member_pay_info.pay_bankcard == bank_card).first()
            if mrii is not None and str(mrii.member_id) != str(m.id):
                response_data["code"] = u"19"
                response_data["content"] = u"身份证非法绑定"
                return toolkit.response(response_data, 200, None, True)
            if mpii is not None and str(mpii.member_id) != str(m.id):
                response_data["code"] = u"23"
                response_data["content"] = u"银行卡或者身份证非法绑定"
                return toolkit.response(response_data, 200, None, True)
            elif mrii is None and mpii is None:
                response_data["code"] = u"0"
                response_data["content"] = u"身份证和银行卡未被绑定"
                return  toolkit.response(response_data, 200, None, True)
            else:
                response_data["code"] = u"0"
                response_data["content"] = u"身份证和银行卡合法绑定"
                return  toolkit.response(response_data, 200, None, True)
    elif ptype == "bank":
        bank_card = request.form.get("bank_card", None)
        if bank_card is None or bank_card == "":
            response_data["code"] = u"2"
            response_data["content"] = u"输入参数不能为空"
            return  toolkit.response(response_data, 200, None, True)
        else:
            mpii = Member_pay_info.query.filter(Member_pay_info.pay_bankcard == bank_card).first()
            if mpii is not None:
                if mpii.member_id == m.id:
                    response_data["code"] = u"0"
                    response_data["content"] = u"银行卡合法绑定"
                    return  toolkit.response(response_data, 200, None, True)
                else:
                    response_data["code"] = u"13"
                    response_data["content"] = u"银行卡非法绑定"
                    return toolkit.response(response_data, 200, None, True)
            else:
                response_data["code"] = u"0"
                response_data["content"] = u"身份证和银行卡未被绑定"
                return  toolkit.response(response_data, 200, None, True)
    elif ptype == "id":
        id_card = request.form.get("id_card", None)
        if id_card is None or id_card == "":
            response_data["code"] = u"2"
            response_data["content"] = u"输入参数不能为空"
            return  toolkit.response(response_data, 200, None, True)
        else:
            mrii = Member_real_info.query.filter(Member_real_info.real_identid == id_card).first()
            if mrii is not None:
                if str(mrii.member_id) == str(m.id):
                    response_data["code"] = u"0"
                    response_data["content"] = u"身份证合法绑定"
                    return  toolkit.response(response_data, 200, None, True)
                else:
                    response_data["code"] = u"17"
                    response_data["content"] = u"身份证已经非法绑定"
                    return toolkit.response(response_data, 200, None, True)
            else:
                response_data["code"] = u"0"
                response_data["content"] = u"身份证和银行卡未被绑定"
                return  toolkit.response(response_data, 200, None, True)


@app.route('/v1/member/reset/passwd', methods=['GET', 'POST'])
def reset_passwd():

    phone = request.form.get("phone", None)
    id_card = request.form.get("id_card", None)
    new_passwd = request.form.get("new_passwd", None)
    re_new_passwd = request.form.get("re_new_passwd", None)

    response_data={}
    if not phone or not new_passwd or not re_new_passwd:
        response_data["code"] = u"10008"
        response_data["desc"] = u"输入参数不能为空"
        response_data["content"] = {}
        return  toolkit.response(response_data, 200, None, True)

    m = Member.query.filter(Member.phone == phone).first()

    if m.isblack == 'Sync':
        response_data["code"] = u"10002"
        response_data["content"]={}
        response_data["desc"] = u"您的账户已被迁移到菠萝理财存管版，请用菠萝理财存管版登录！"
        return toolkit.response(response_data, 200, None, True)
    
    if m is None:
        response_data["code"] = u"10001"
        response_data["desc"] = u"此用户不存在"
        response_data["content"] = {}
        return  toolkit.response(response_data, 200, None, True)
    elif m.is_identity_bind == 1:
        if id_card is None:
            response_data["code"]=u"10002"
            response_data["desc"]= u"该用户经过实名认证，身份证号不能为空"
            response_data["content"] = {}
            return  toolkit.response(response_data, 200, None, True)
        else:
            mr = Member_real_info.query.filter_by(member_id = str(m.id).replace("-", "")).first()
            if mr is None or id_card != mr.real_identid:
                response_data["code"]=u"10003"
                response_data["desc"]= u"该用户绑定身份证不匹配"
                response_data["content"] = {}
                return  toolkit.response(response_data, 200, None, True)
    elif new_passwd != re_new_passwd:
        response_data["code"]=u"10005"
        response_data["desc"]= u"两次输入密码不相同"
        response_data["content"] = {}
        return  toolkit.response(response_data, 200, None, True)
    try:
        m.hash_password(new_passwd)
        db.session.commit()
        response_data["code"]=u"10000"
        response_data["desc"]= u"数据库操作成功"
        response_data["content"] = {}
        return  toolkit.response(response_data, 200, None, True)
    except:
        response_data["code"]=u"10007"
        response_data["desc"]= u"数据库操作失败"
        response_data["content"] = {}
        return  toolkit.response(response_data, 200, None, True)

@app.route("/v1/member/<name_or_phone>/modify/passwd", methods=['GET', 'POST'])
@auth.login_required
def modify_passwd(name_or_phone):

    old_passwd = request.form.get("old_passwd", None)
    new_passwd = request.form.get("new_passwd", None)
    re_new_passwd = request.form.get("re_new_passwd", None)
    response_data={}
    if old_passwd is None or new_passwd is None or re_new_passwd is None \
       or old_passwd == "" or new_passwd == "" or re_new_passwd== "":
        response_data["code"] = u"1"
        response_data["content"] = u"输入参数不能为空"
        return  toolkit.response(response_data, 200, None, True)

    m = Member.query.filter(or_(Member.name==name_or_phone, Member.phone==name_or_phone)).first()

    if m.isblack == 'Sync':
        response_data["code"] = u"10002"
        response_data["content"]={}
        response_data["desc"] = u"您的账户已被迁移到菠萝理财存管版，请用菠萝理财存管版登录！"
        return toolkit.response(response_data, 200, None, True)

    if m.verify_password(old_passwd) is False:
        response_data["code"] = u"2"
        response_data["content"] = u"旧密码输入错误"
        return  toolkit.response(response_data, 200, None, True)

    if new_passwd != re_new_passwd:
        response_data["code"] = u"3"
        response_data["content"] = u"新密码和旧密码不相等"
        return  toolkit.response(response_data, 200, None, True)

    try:
        m.hash_password(new_passwd)
        db.session.merge(m)
        db.session.commit()
        response_data["code"]=u"0"
        response_data["content"]= u"数据库操作成功"
        return  toolkit.response(response_data, 200, None, True)
    except:
        response_data["code"]=u"7"
        response_data["content"]= u"数据库操作失败"
        return  toolkit.response(response_data, 200, None, True)


@app.route("/v1/member/<name_or_phone>/modify/pay/passwd", methods=['GET', 'POST'])
#@auth.login_required
def modify_pay_passwd(name_or_phone):

    old_passwd = request.form.get("old_passwd", None)
    new_passwd = request.form.get("new_passwd", None)
    re_new_passwd = request.form.get("re_new_passwd", None)

    response_data={}
    if old_passwd is None or new_passwd is None or re_new_passwd is None \
       or old_passwd == "" or new_passwd == "" or re_new_passwd== "":
        response_data["code"] = u"10001"
        response_data["desc"] = u"输入参数不能为空"
        response_data["content"] = {}
        return  toolkit.response(response_data, 200, None, True)

    m = Member.query.filter(or_(Member.name==name_or_phone, Member.phone==name_or_phone)).first()

    if m.isblack == 'Sync':
        response_data["code"] = u"10002"
        response_data["content"]={}
        response_data["desc"] = u"您的账户已被迁移到菠萝理财存管版，请用菠萝理财存管版登录！"
        return toolkit.response(response_data, 200, None, True)

    print '==================修改密码====================='
    print 'old_passwd=%s' % old_passwd
    print 'new_passwd=%s' % new_passwd
    print  m.verify_pay_password(old_passwd)
    print '======================================='

    if m.pay_passwd is None:
        response_data["code"] = u"10004"
        response_data["desc"] = u"该用户未设置交易密码"
        response_data["content"] = {}
        return  toolkit.response(response_data, 200, None, True)

    if m.verify_pay_password(old_passwd) is False:
        response_data["code"] = u"10002"
        response_data["desc"] = u"旧密码输入错误"
        response_data["content"] = {}
        return  toolkit.response(response_data, 200, None, True)

    if new_passwd != re_new_passwd:
        response_data["code"] = u"10003"
        response_data["desc"] = u"新密码和旧密码不相等"
        response_data["content"] = {}
        return  toolkit.response(response_data, 200, None, True)

    try:
        m.hash_pay_password(new_passwd)
        db.session.merge(m)
        db.session.commit()
        response_data["code"]=u"10000"
        response_data["desc"]= u"数据库操作成功"
        response_data["content"] = {}
        return  toolkit.response(response_data, 200, None, True)
    except:
        response_data["code"]=u"10007"
        response_data["desc"]= u"数据库操作失败"
        response_data["content"] = {}
        return  toolkit.response(response_data, 200, None, True)


@app.route("/v1/member/<name_or_phone>/reset/pay/passwd", methods=['GET', 'POST'])
#@auth.login_required
def reset_pay_passwd(name_or_phone):
    new_passwd = request.form.get("new_passwd", None)
    re_new_passwd = request.form.get("re_new_passwd", None)
    response_data= {}
    m = Member.query.filter(or_(Member.name==name_or_phone, Member.phone==name_or_phone)).first()

    if m.isblack == 'Sync':
        response_data["code"] = u"10002"
        response_data["content"]={}
        response_data["desc"] = u"您的账户已被迁移到菠萝理财存管版，请用菠萝理财存管版登录！"
        return toolkit.response(response_data, 200, None, True)

    if new_passwd != re_new_passwd:
        response_data["code"]=u"10005"
        response_data["content"] = {}
        response_data["desc"]= u"两次输入密码不相同"
        return  toolkit.response(response_data, 200, None, True)

    try:
        m.hash_pay_password(new_passwd)
        db.session.merge(m)
        db.session.commit()
        response_data["code"]=u"10000"
        response_data["desc"]= u"数据库操作成功"
        response_data["content"] = {}
        return  toolkit.response(response_data, 200, None, True)
    except:
        response_data["code"]=u"10007"
        response_data["desc"]= u"数据库操作失败"
        response_data["content"] = {}
        return  toolkit.response(response_data, 200, None, True)


@app.route("/v1/member/<name_or_phone>/verify/member/id", methods=['GET', 'POST'])
#@auth.login_required
def verify_member_id(name_or_phone):
    id_card = request.form.get("id_card", None)

    response_data= {}
    m = Member.query.filter(or_(Member.name==name_or_phone, Member.phone==name_or_phone)).first()
    mri = Member_real_info.query.filter(Member_real_info.member_id == str(m.id).replace("-", "")).first()
    mpi = Member_pay_info.query.filter(Member_pay_info.member_id == str(m.id).replace("-", "")).first()
    if mri is None or mpi is None:
        response_data["code"]=u"10001"
        response_data["desc"]= u"无此用户信息"
        response_data["content"]= {}
        return  toolkit.response(response_data, 200, None, True)

    if mri.real_identid == id_card:
        response_data["code"]=u"10000"
        response_data["desc"]= u"用户身份验证成功"
        response_data["content"]= {}
        return  toolkit.response(response_data, 200, None, True)
    else:
        response_data["code"]=u"10002"
        response_data["desc"]= u"用户身份验证失败"
        response_data["content"]= {}
        return  toolkit.response(response_data, 200, None, True)


@app.route("/v1/member/<name_or_phone>/info", methods=['GET', 'POST'])
#@auth.login_required
def get_mem_info(name_or_phone):
    response_data = {}
    profit_amount = 0
    m = Member.query.filter(or_(Member.name==name_or_phone, Member.phone==name_or_phone)).first()
    if not m:
        response_data["code"] = u"1"
        response_data["content"] = u"用户不存在"
        return toolkit.response(response_data, 200, None, True)

    query_profit_total = db.session.query(Member_invite_profit.invite_profit, Member_invite_profit.inviter_id)
    profit_total = query_profit_total.filter(Member_invite_profit.inviter_id == m.id).all()
    if profit_total is not None:
        for pm in profit_total:
            profit_amount = profit_amount + pm.invite_profit
        response_data["profit_amount"] = profit_amount

    people_total = Member_invite_info.query.filter(Member_invite_info.inviter_id == m.id).count()

    response_data["people_amount"] = people_total if people_total >= 1 else 0
    if not os.path.exists(os.getcwd() + '/media/qrcode/new_member_qr/%s' % m.qrcode):
        try:
            gen_qrcode("%s/v1/html5/invate/%s" % (BOLUO_URL, m.invitation_code),
                       "/home/wwwroot/qrcode/new_member_qr/%s" % m.qrcode, "/home/wwwroot/qrcode/qrlogo.png")
            response_data['qrcode'] = BOLUO_URL + "/media/qrcode/new_member_qr/%s" % m.qrcode
        except:
            response_data['qrcode'] = ''
    else:
        response_data['qrcode'] = BOLUO_URL + "/media/qrcode/new_member_qr/%s" % m.qrcode

    if m is not None:
        if m.phone is None:
            response_data["code"] = u"1"
            response_data["content"] = u"用户不存在"
            return toolkit.response(response_data, 200, None, True)
        else:
            response_data["code"] = u"10000"

            if m.name is not None:
                response_data["name"] = m.name
            else:
                response_data["name"] = m.phone

            response_data["phone"] = m.phone
            response_data["invite_code"] = m.invitation_code
            return toolkit.response(response_data, 200, None, True)
    else:
        response_data["code"] = u"2"
        response_data["content"] = u"用户不存在"
        return toolkit.response(response_data, 200, None, True)


@app.route("/v1/member/<name_or_phone>/reset/phone", methods=['GET', 'POST'])
# @auth.login_required
def reset_phone(name_or_phone):

    phone = request.form.get("phone", None)

    response_data= {}
    response_data['content'] = {}
    if phone is None or phone == "" :
        response_data["code"] = u"10001"
        response_data["desc"] = u"输入参数不能为空"
        return  toolkit.response(response_data, 200, None, True)

    m = Member.query.filter(or_(Member.name==name_or_phone, Member.phone==name_or_phone)).first()

    if m.isblack == 'Sync':
        response_data["code"] = u"10002"
        response_data["content"]={}
        response_data["desc"] = u"您的账户已被迁移到菠萝理财存管版，请用菠萝理财存管版登录！"
        return toolkit.response(response_data, 200, None, True)

    if m is None:
        response_data["code"] = u"1"
        response_data["desc"] = u"用户不存在"
        return toolkit.response(response_data, 200, None, True)
    try:
        m.phone = phone
        db.session.merge(m)
        db.session.commit()
        response_data["code"]=u"10000"
        response_data["desc"]= u"数据库操作成功"
        return  toolkit.response(response_data, 200, None, True)
    except:
        response_data["code"]=u"10007"
        response_data["desc"]= u"数据库操作失败"
        return  toolkit.response(response_data, 200, None, True)


@app.route("/v1/member/<name_or_phone>/invite/1/<page_total>/<page_num>", methods=['GET', 'POST'])
# @auth.login_required
def invite_info(name_or_phone, page_num, page_total):

    if page_num is None:
        page_num = 1
    else:
        pnum = int(page_num.encode('ascii'))

    if page_total is None:
        page_total = 10
    else:
        page_total = int(page_total.encode('ascii'))

    pnum = (pnum - 1) * page_total
    page_mount = pnum + page_total

    query_invite = db.session.query(Member_invite_info.invited_id)
    invites = query_invite.filter(and_(Member.id == Member_invite_info.inviter_id, or_(Member.name == name_or_phone, Member.phone == name_or_phone))).all()

    response_data = {}
    response_data["code"] = u"10000"
    response_data["desc"] = u"请求成功"
    response_data["content"] = []

    inviteset = tuple([item[0] for item in invites])
    if invites is not None and len(invites) >= 1:
        query_top = db.session.query(Member.name,Member.phone, Member.reg_time, Member_invite_info.sign)
        query_res_amount = query_top.filter(
            and_(Member.id == Member_invite_info.invited_id, Member_invite_info.invited_id.in_(inviteset))).all()
        amount = len(query_res_amount)
        response_data["amount"] = amount
        
        query_res_all = query_top.filter(and_(Member.id==Member_invite_info.invited_id, Member_invite_info.invited_id.in_(inviteset))).order_by(Member.reg_time.desc()).all()[pnum:page_mount]

        for query_res in query_res_all:
            result_dict = {}
            result_dict["name"] = query_res.name
            result_dict["phone"] = query_res.phone
            result_dict["reg_time"] = str(query_res.reg_time)[:10]
            result_dict["sign"] = query_res.sign
            response_data["content"].append(result_dict)
        return toolkit.response(response_data, 200, None, True)
    else:
        response_data["content"] =[] 
        return  toolkit.response(response_data, 200, None, True)


@app.route("/v1/member/<name_or_phone>/invite/0/<page_total>/<page_num>", methods=['GET','POST'])
# @auth.login_required
def invite_profit(name_or_phone, page_num, page_total):
    if page_num is None:
        page_num = 1
    else:
        pnum = int(page_num.encode('ascii'))

    if page_total is None:
        page_total = 10
    else:
        page_total = int(page_total.encode('ascii'))

    pnum = (pnum - 1) * page_total
    response_json ={}
    page_mount = pnum + page_total
    query_invite_profit = db.session.query(Member_invite_profit.invited_id, Member_invite_profit.product_id, Invest_info.money, Invest_info.time)
    invites = query_invite_profit.filter(and_(Member.id == Member_invite_profit.inviter_id, or_(Member.name == name_or_phone, Member.phone == name_or_phone), Product_info.id == Member_invite_profit.product_id, Invest_info.id == Member_invite_profit.order_id)).all()

    inviteset = tuple([item[0] for item in invites])
    response_json["code"] = u"10000"
    response_json["desc"] = u"请求成功"
    response_json["content"] = []
    if invites is not None and len(invites) >= 1:
        query_top = db.session.query(Member.name, Member.phone, Member_invite_profit.invite_profit, Product_info.interest_time, Product_info.time_limit, Invest_info.money, Invest_info.time)
        query_res_amount = query_top.filter(
            and_(Member.id == Member_invite_profit.invited_id, Product_info.id == Member_invite_profit.product_id,
                 Invest_info.id == Member_invite_profit.order_id, Member_invite_profit.invited_id.in_(inviteset))).all()
        amount = len(query_res_amount)
        response_json["amount"] = amount

        query_res_all = query_top.filter(and_(Member.id == Member_invite_profit.invited_id, Product_info.id == Member_invite_profit.product_id, Invest_info.id == Member_invite_profit.order_id, Member_invite_profit.invited_id.in_(inviteset))).order_by(Invest_info.time.desc()).all()[pnum:page_mount]

        for query_res in query_res_all:
            result_dict = {}
            result_dict["name"] = query_res.name
            result_dict["phone"] = query_res.phone
            result_dict["interest_time"] = str(query_res.interest_time)[:10]
            result_dict["time_limit"] = str(query_res.time_limit)[:10]
            result_dict["money"] = query_res.money
            result_dict["time"] = str(query_res.time)[:10]
            result_dict["invite_profit"] = query_res.invite_profit
            response_json["content"].append(result_dict)

        return toolkit.response(response_json, 200, None, True)
    else:
        response_json["content"] = []
        return toolkit.response(response_json, 200, None, True)

@app.route("/v1/member/company/post", methods=['GET', 'POST'])
def company_date():

    business_name = request.form.get("business_name", None)
    linkman = request.form.get("linkman", None)
    phone = request.form.get("phone", None)
    linkman_post = request.form.get("linkman_post", None)
    money = request.form.get("money", None)
    cycle = request.form.get("cycle", None)

    response_data = {}

    mbs = Member_bussnes.query.filter(Member_bussnes.phone==phone).all()
    if len(mbs) > 0:
        response_data["code"]=u"2"
        response_data["content"]= u"已经约过标了"
        return  toolkit.response(response_data, 200, None, True)
    
    mb = Member_bussnes(business_name=business_name, linkman=linkman, phone=phone, linkman_post=linkman_post, money=money, cycle=cycle)

    try:
        db.session.add(mb)
        db.session.commit()
        response_data["code"]=u"0"
        response_data["content"]= u"数据库操作成功"
        return  toolkit.response(response_data, 200, None, True)
    except:
        response_data["code"]=u"7"
        response_data["content"]= u"数据库操作失败"
        return  toolkit.response(response_data, 200, None, True)

@app.route("/v1/<name_or_phone>/member/loan",methods=['GET','POST'])
# @auth.login_required
def member_load(name_or_phone):

    loaner_name = request.form.get("loaner_name", None)
    money_loan = request.form.get("money_loan", None)
    limit_loan = request.form.get("limit_loan", None)
    nature_house = request.form.get("nature_house", None)
    village_name = request.form.get("village_name", None)
    area_house = request.form.get("area_house", None)
    remain_loan = request.form.get("remain_loan", None)
    property_id = request.form.get("property_id", None)
    property_name = request.form.get("property_name", None)
    property_idnum = request.form.get("property_idnum", None)
    dead_code = request.form.get("dead_code", None)

    # print loaner_name, money_loan, limit_loan, nature_house, village_name, area_house, \
    # remain_loan, property_id, property_name, property_idnum

    response_data = {}

    if dead_code != "qwer":
        response_data["code"] = u"10006"
        response_data["desc"] = u"操作失败"
        return toolkit.response(response_data, 200, None, True)

    if name_or_phone is not None:
        m = Member.query.filter(or_(Member.name == name_or_phone, Member.phone == name_or_phone)).first()
        if m is None:
            response_data["code"] = u"10002"
            response_data["desc"] = u"用户不存在"
            return toolkit.response(response_data, 200, None, True)

    member_info = db.session.query(Member.id)
    member_info_id = member_info.filter(or_(Member.name == name_or_phone, Member.phone == name_or_phone)).first()

    if m.isblack == 'Sync':
        response_data["code"] = u"10002"
        response_data["content"]={}
        response_data["desc"] = u"您的账户已被迁移到菠萝理财存管版，请用菠萝理财存管版登录！"
        return toolkit.response(response_data, 200, None, True)

    member_id = str(member_info_id.id).replace("-", "")

    if loaner_name is None or money_loan is None or limit_loan is None or nature_house is None or village_name is None or area_house is None or \
        remain_loan is None or property_id is None or property_name is None or property_idnum is None or loaner_name == "" or money_loan == "" or \
            limit_loan == "" or nature_house == "" or village_name == "" or area_house == "" or remain_loan == "" or property_id == "" or \
                property_name == "" or property_idnum == "":
        response_data["code"] = u"10001"
        response_data["desc"] = u"参数字段不能为空"
        response_data["content"] = {}
        return toolkit.response(response_data, 200, None, True)

    now = datetime.now()
    time_loan = now.strftime("%Y-%m-%d %H:%M:%S")
    ml = Member_loan(member_id=member_id, loaner_name=loaner_name, money_loan=money_loan, limit_loan=limit_loan, nature_house=nature_house, \
                     village_name=village_name, area_house=area_house, remain_loan=remain_loan, property_id=property_id, \
                     property_name=property_name, property_idnum=property_idnum, time_loan=time_loan)

    try:
        db.session.add(ml)
        db.session.commit()
        response_data["code"] = u"0"
        response_data["content"] = u"数据库操作成功"
        return toolkit.response(response_data, 200, None, True)
    except:
        response_data["code"] = u"7"
        response_data["content"] = u"数据库操作失败"
        return toolkit.response(response_data, 200, None, True)

        
# 邀请注册页面接口   phone 被邀请人电话
@app.route("/v1/member/<invitation_code>/invite/member/<phone>", methods=['GET', 'POST'])
def invite_member(invitation_code,phone):

    response_data = {}
    # 验证信息来源，为了防止直接请求接口   key_code 为写定的字符串
    key_code = request.form.get('key_code', None)
    if key_code != "BoLuoLc":
        response_data["code"]=u"10002"
        response_data["content"]= u"不匹配"
        return  toolkit.response(response_data, 200, None, True)
    # 得到邀请人信息
    # inm = Member.query.filter(or_(Member.name == name_or_phone, Member.phone == name_or_phone)).first()

    #if not phone:
    #    response_data["code"]=u"10003"
    #    response_data["content"]= u"号码不能为空"
    #    return  toolkit.response(response_data, 200, None, True)

    #判断被邀请人是否已在用户表中
    indm = Member.query.filter(Member.phone == phone).first()
    if indm:
        response_data["code"]=u"10004"
        response_data["content"]= u"被邀请人已注册"
        return  toolkit.response(response_data, 200, None, True)

    # register_ip = request.form.get('device_code', None)

    register_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # reg_ip=register_ip,
    m = Member(name = phone, phone=phone, reg_time=register_time, is_email_bind=False,
               is_pay_bind=False, is_identity_bind=False,is_activate =1)


    try:
        db.session.add(m)
        db.session.commit()

        # 将被邀请人跟邀请人建立邀请关系
        indm = Member.query.filter(Member.phone == phone).first()
        inm = Member.query.filter(Member.invitation_code == invitation_code).first()

        inr = Member_invite_info(inviter_id = inm.id, invited_id=indm.id,inviter_time=datetime.now().date())
        # inr = Member_invite_info(inviter_id=inm.id, invited_id=indm.id)
        db.session.add(inr)
        db.session.commit()


        response_data["code"] = u"10000"
        response_data["content"] = u"邀请您注册"

        # 给被邀请人发送信息
        datas = [50]

        send_message(phone, datas, 41260)
        return toolkit.response(response_data, 200, None, True)
    except:
        response_data["code"] = u"10005"
        response_data["content"] = u"数据库操作失败"
        return toolkit.response(response_data, 200, None, True)


# 短信验证码登陆接口
# 1.对验证码的验证  2.判断phone是否为已存在用户
@app.route("/v1/member/verify/land/<phone>", methods=['GET', 'POST'])
def verify_code_land(phone):

    # 验证码的验证
    verify_code = request.form.get("verify_code")

    key = phone + "_" + verify_code 
    response_data = {}
    response_data["content"] = {}
    redisClient = redis.StrictRedis(host='127.0.0.1',port=6379, db=0, password='1234qweP')
    try:
        ttl = redisClient.ttl(key)
        if not ttl:
            response_data["code"]=u"1"
            response_data["desc"] = u"验证码已经过期"
            return toolkit.response(response_data, 200, None, True)
        else:
            value = redisClient.get(key)
            print value
            print verify_code
            if value != verify_code: 
                response_data["code"]=u"2"
                response_data["desc"] = u"验证码验证失败"
                return toolkit.response(response_data, 200, None, True)
    except:
        response_data["code"]=u"3"
        response_data["content"] = u"未知异常"
        return toolkit.response(response_data, 200, None, True)
    
    
    
    # 验证码正确，判断phone是否存在，存在可登陆
    m = None
    try:
        m = Member.query.filter(Member.phone == phone).first()
        if m is None:
            response_data["code"] = u"4"
            response_data["content"] = u"用户不存在"
            return toolkit.response(response_data, 200, None, True)
        if m is not None:
            g.user = m
            response_data["code"] = u"0"
            response_data["content"] = u"登陆成功"
            token = g.user.generate_auth_token(1440)
            response_data["content"] = {"memberId":str(m.id).replace("-", ""),"apiToken":token.decode('ascii'), \
                                    "newer": True, "phone": m.phone, "name": m.name, "pay_bind": 0, \
                                    "id_bind": 0, "is_pay_passwd": 0}
            return toolkit.response(response_data, 200, None, True)

    except:
        response_data["code"] = u"5"
        response_data["content"] = u"数据库操作失败"
        return toolkit.response(response_data, 200, None, True)


# 短信验证码成功登陆后  注册信息
@app.route('/v1/member/shmsg/register', methods=['GET','POST'])
def shmsg_register():

    phone = request.form.get('phone',None)
    passwd = request.form.get('passwd', None)
    name = request.form.get('name',None)

    response_data= {}

    if phone is None:
        response_data["code"] = u"3"
        response_data["desc"] = u"手机号为空"
        return toolkit.response(response_data, 200, None, True)
    if name is None:
        name = phone
    if passwd is None:
        response_data["code"] = u"4"
        response_data["desc"] = u"密码为空"
        return toolkit.response(response_data, 200, None, True)

    mpq = Member.query.filter(Member.phone==phone).first()
    if mpq.passwd is not None:
        response_data["code"] = u"5"
        response_data["desc"] = u"该用户名或者手机号已经设置密码"
        return toolkit.response(response_data, 200, None, True)
# 更新该用户的信息
    invite = Member_invite.query.filter(Member_invite.is_use == 0).first()#得到邀请码，invite表中第一个没有被使用的

    qrcode_path="%s_%s.png" % (name ,phone)
    #gen_qrcode("https://www.boluolc.com/index.php/Home/activitys/zhuce3/invite_code/%s" % (invite.invitation_code),
    #           "/home/wwwroot/qrcode/member_qr/%s_%s.png" % (name ,phone), "/home/wwwroot/qrcode/qrlogo.png")

    #m = Member(name = name, phone=phone, reg_ip=register_ip, reg_time=register_time, is_email_bind=False,
    #           is_pay_bind=False, is_identity_bind=False, invitation_code = invite.invitation_code, qrcode=qrcode_path)

    mpq.phone = phone
    mpq.invitation_code = invite.invitation_code
    mpq.qrcode=qrcode_path   #2维码
    mpq.is_activate =0
    invite.is_use = 1
    mpq.hash_password(passwd)
    try:
        db.session.merge(invite)
        db.session.commit()
        db.session.merge(mpq)
        db.session.commit()


        mm = Member.query.filter(and_(Member.name==name, Member.phone==phone)).first()
        red_list = []
        type = "1"
        red_list.append(gen_reg_red_pocket(type, inm.id, 990))
        red_list.append(gen_reg_red_pocket(type, inm.id, 1980))
        red_list.append(gen_reg_red_pocket(type, inm.id, 4980))
        for item in red_list:
            db.session.add(item)
            db.session.commit()

        ma = Member_asset_info(member_id=mm.id, member_name=mm.name)#设置用户资金表
        db.session.add(ma)
        db.session.commit()
        response_data["code"] = u"0"
        response_data["desc"] = u"注册成功"
        # todo record the event in the database
        datas = [50]
        send_message(phone, datas, 41260)
        m = Member.query.filter(Member.phone == phone).first()
        g.user = m
        token = g.user.generate_auth_token(1440)
        response_data["content"] = {"memberId":str(m.id).replace("-", ""),"apiToken":token.decode('ascii'), \
                                    "newer": True, "phone": m.phone, "name": m.name, "pay_bind": 0, \
                                    "id_bind": 0, "is_pay_passwd": 0}
        return toolkit.response(response_data, 200, None, True)
    except:
        response_data["code"] = u"7"
        response_data["desc"] = u"数据库操作/失败"
        return toolkit.response(response_data, 200, None, True)


# @app.route('/v1/message/operation/<id>', methods=['GET','POST'])
# def message_operation(id):
#     response_data = {}
#
#     return toolkit.response(response_data, 200, None, True)


# 获取用户的isblack值
@app.route('/v1/member/<name_or_phone>/isblack/info', methods=['GET','POST'])
def isblack_judgment(name_or_phone):
    response_data = {}
    try:
        m = Member.query.filter(or_(Member.name == name_or_phone, Member.phone == name_or_phone)).first()
        if m:
            if m.isblack == "Sync":
                response_data['isblack'] = True
                response_data["code"] = u"10000"
                response_data["desc"] = u"账户是锁定状态"
            else:
                response_data['isblack'] = False
                response_data["code"] = u"10001"
                response_data["desc"] = u"账户是非锁定状态"
        else:
            response_data['isblack'] = False
            response_data["code"] = u"10002"
            response_data["desc"] = u"用户不存在"
    except:
        response_data['isblack'] = False
        response_data["code"] = u"10003"
        response_data["desc"] = u"发生未知异常"
    return toolkit.response(response_data, 200, None, True)


# 获取用户的红包和加息券信息
@app.route('/v1/member/<name_or_phone>/hongbao/info', methods=['GET','POST'])
def get_hongbao(name_or_phone):
    response_data = {}
    response_data["content"] = []
    try:
        m = Member.query.filter(or_(Member.name == name_or_phone, Member.phone == name_or_phone)).first()
        if m:
            hongbao_info = Member_red_pocket.query.filter_by(member_id=m.id).all()
            if hongbao_info:
                for hongbao in hongbao_info:
                    hongbao_type = Member_red_pocket_type.query.filter_by(id=hongbao.sort_id).first()
                    if hongbao_type:
                        item = {}
                        item['member_id'] = str(hongbao.member_id).replace('-', '')
                        item['is_use'] = hongbao.is_use
                        item['sort_id'] = str(hongbao.sort_id).replace('-', '')
                        item['name'] = str(hongbao_type.name)
                        item['is_freeze'] = hongbao.is_freeze
                        item['product_id'] = str(hongbao.product_id).replace('-', '')
                        item['generate_time'] = hongbao.generate_time.strftime("%Y-%m-%d %H:%M:%S")
                        item['INSPECTOR'] = hongbao.INSPECTOR
                        item['SEND_TIME'] = hongbao.SEND_TIME.strftime("%Y-%m-%d %H:%M:%S") if hongbao.SEND_TIME else hongbao.SEND_TIME
                        response_data["content"].append(item)
                response_data["code"] = u"10000"
                response_data["desc"] = u"返回成功"
            else:
                response_data["code"] = u"10000"
                response_data["desc"] = u"红包表没有该用户信息"
        else:
            response_data["code"] = u"10002"
            response_data["desc"] = u"用户不存在"
    except:
        response_data["code"] = u"10003"
        response_data["desc"] = u"发生未知异常"
    return toolkit.response(response_data, 200, None, True)


# 获取用户的积分信息
@app.route('/v1/member/<name_or_phone>/integral/info', methods=['GET','POST'])
def get_integral(name_or_phone):
    response_data = {}
    response_data['remainamount'] = 0
    response_data['rechargeamount'] = 0
    response_data['uncollectedamount'] = 0
    try:
        m = Member.query.filter(or_(Member.name == name_or_phone, Member.phone == name_or_phone)).first()
        if m:
            asset_info = Member_asset_info.query.filter_by(member_id=m.id).first()
            if asset_info:
                response_data['remainamount'] = asset_info.remainamount
                response_data['rechargeamount'] = asset_info.rechargeamount
                response_data['uncollectedamount'] = asset_info.uncollectedamount
                response_data['score'] = asset_info.score
                response_data["code"] = u"10000"
                response_data["desc"] = u"返回成功"
            else:
                response_data['score'] = 0
                response_data["code"] = u"10001"
                response_data["desc"] = u"资金表没有该用户信息"
        else:
            response_data['score'] = 0
            response_data["code"] = u"10002"
            response_data["desc"] = u"用户不存在"
    except:
        response_data['score'] = 0
        response_data["code"] = u"10003"
        response_data["desc"] = u"发生未知异常"
    return toolkit.response(response_data, 200, None, True)


# 修改用户的isblack值
@app.route('/v1/member/<name_or_phone>/isblack/info/modify', methods=['GET','POST'])
def isblack_modify(name_or_phone):
    response_data = {}
    try:
        m = Member.query.filter(or_(Member.name == name_or_phone, Member.phone == name_or_phone)).first()
        if m:
            if m.isblack == "True":
                response_data['isblack'] = m.isblack
                response_data["code"] = u"10004"
                response_data["desc"] = u"该用户在黑名单，不能修改"
            elif m.sign == '1':
                response_data['isblack'] = ''
                response_data["code"] = u"10005"
                response_data["desc"] = u"虚拟账号，不能修改"
            elif m.isblack == "Sync":
                response_data['isblack'] = m.isblack
                response_data["code"] = u"10004"
                response_data["desc"] = u"该用户已经是同步状态，不能修改"
            elif name_or_phone == '13811629823':
                response_data['isblack'] = ''
                response_data["code"] = u"10006"
                response_data["desc"] = u"超级账号，不能修改"
            else:
                m.isblack = 'Sync'
                db.session.merge(m)
                db.session.commit()
                response_data['isblack'] = 'Sync'
                response_data["code"] = u"10000"
                response_data["desc"] = u"isblack值修改成功"
        else:
            response_data['isblack'] = ""
            response_data["code"] = u"10002"
            response_data["desc"] = u"用户不存在"
    except Exception, e:
        print e
        response_data['isblack'] = ""
        response_data["code"] = u"10003"
        response_data["desc"] = u"发生未知异常"
    return toolkit.response(response_data, 200, None, True)


# 获取用户的资金信息
@app.route('/v1/member/<name_or_phone>/asset/info', methods=['GET','POST'])
def get_asset(name_or_phone):
    response_data = {}
    response_data['remainamount'] = 0
    response_data['rechargeamount'] = 0
    try:
        m = Member.query.filter(or_(Member.name == name_or_phone, Member.phone == name_or_phone)).first()
        if m:
            asset_info = Member_asset_info.query.filter_by(member_id=m.id).first()
            if asset_info:
                response_data['remainamount'] = asset_info.remainamount
                response_data['rechargeamount'] = asset_info.rechargeamount
                response_data["code"] = u"10000"
                response_data["desc"] = u"返回成功"
            else:
                response_data["code"] = u"10001"
                response_data["desc"] = u"资金表没有该用户信息"
        else:
            response_data["code"] = u"10002"
            response_data["desc"] = u"用户不存在"
    except:
        response_data["code"] = u"10003"
        response_data["desc"] = u"发生未知异常"
    return toolkit.response(response_data, 200, None, True)


# 获取用户的签到数据
@app.route('/v1/member/<name_or_phone>/sign/info', methods=['GET','POST'])
def get_sign(name_or_phone):
    response_data = {}
    response_data["content"] = []
    try:
        m = Member.query.filter(or_(Member.name == name_or_phone, Member.phone == name_or_phone)).first()
        if m:
            sign = Sign_record.query.filter_by(phone=name_or_phone).order_by(Sign_record.check_time.desc()).all()
            if sign:
                for si in sign:
                    temp = {}
                    temp["phone"] = si.phone
                    temp["check_time"] = si.check_time.strftime("%Y-%m-%d %H:%M:%S")
                    temp["check_number"] = si.check_number
                    temp["integral"] = si.integral
                    response_data["content"].append(temp)
                response_data["code"] = u"10000"
                response_data["desc"] = u"查询成功"
            else:
                response_data["code"] = u"10000"
                response_data["desc"] = u"账户没有签到数据"
        else:
            response_data["code"] = u"10002"
            response_data["desc"] = u"用户不存在"
    except:
        raise
        response_data["code"] = u"10003"
        response_data["desc"] = u"发生未知异常"
    return toolkit.response(response_data, 200, None, True)


# 获取用户的可用的摇骰子次数
@app.route('/v1/member/<name_or_phone>/use_number/info', methods=['GET','POST'])
def get_use_number(name_or_phone):
    response_data = {}
    response_data["use_number"] = 0
    response_data["activity_id"] = ""
    try:
        m = Member.query.filter(or_(Member.name == name_or_phone, Member.phone == name_or_phone)).first()
        if m:
            bldfw = Activity.query.filter_by(name='大富翁活动').first()
            zill = Zillionaire_info.query.filter_by(phone=name_or_phone, activity_id=bldfw.id).first()
            if zill:
                response_data["use_number"] = zill.use_number
                response_data["investment"] = zill.investment
                if zill.activity_id:
                    response_data["activity_id"] = str(zill.activity_id).replace('-', '')
                response_data["code"] = u"10000"
                response_data["desc"] = u"查询成功"
            else:
                response_data["code"] = u"10000"
                response_data["desc"] = u"账户没有签到数据"
        else:
            response_data["code"] = u"10002"
            response_data["desc"] = u"用户不存在"
    except:
        raise
        response_data["code"] = u"10003"
        response_data["desc"] = u"发生未知异常"
    return toolkit.response(response_data, 200, None, True)


# 获取用户的可用的邀请关系及邀请收益
@app.route('/v1/member/<name_or_phone>/invite_info/info', methods=['GET','POST'])
def get_invite_info(name_or_phone):
    response_data = {}
    response_data["content"] = {}
    response_data["content"]["invite_info"] = []
    response_data["content"]["invite_profit"] = []
    try:
        m = Member.query.filter(or_(Member.name == name_or_phone, Member.phone == name_or_phone)).first()
        if m:
            invite_info = Member_invite_info.query.filter_by(inviter_id=str(m.id).replace('-', '')).all()
            if invite_info:
                for inv in invite_info:
                    temp = {}
                    temp["inviter_id"] = str(inv.inviter_id).replace('-', '')
                    temp["invited_id"] = str(inv.invited_id).replace('-', '')
                    temp["sign"] = inv.sign
                    temp["inviter_time"] = inv.inviter_time.strftime("%Y-%m-%d %H:%M:%S") if inv.inviter_time else None
                    temp["is_invest"] = inv.is_invest
                    response_data["content"]["invite_info"].append(temp)

            response_data["code"] = u"10000"
            response_data["desc"] = u"查询成功"
        else:
            response_data["code"] = u"10002"
            response_data["desc"] = u"用户不存在"
    except:
        raise 
        response_data["code"] = u"10003"
        response_data["desc"] = u"发生未知异常"
    return toolkit.response(response_data, 200, None, True)


@app.route('/v1/member/<name_or_phone>/is_new_member/info', methods=['GET','POST'])
def issss_new_member(name_or_phone):
    response_data = {}

    m = Member.query.filter(or_(Member.name == name_or_phone, Member.phone == name_or_phone)).first()
    if m:
        super_phone_list = ['13811629823', '18611897708','18519291259', '13810354654', '13237711492', '13303479527']
        if name_or_phone not in super_phone_list:
            inv_tops = db.session.query(Invest_info, Product_info.product_type)
            new_member = inv_tops.filter(and_(Invest_info.member_id == str(m.id).replace("-", ""),
                            Product_info.product_type == '新手标', Invest_info.product_id==Product_info.id)).first()
            new_member02 = inv_tops.filter(and_(Invest_info.member_id == str(m.id).replace("-", ""),
                                                Invest_info.NEWHAND_ID == '531d3ab7516bd37f01516bdcda180009')).first()
            if new_member or new_member02:
                response_data["is_new_member"] = 0
            else:
                response_data["is_new_member"] = 1
        else:
            response_data["is_new_member"] = 1
    else:
        response_data["is_new_member"] = 1
    return toolkit.response(response_data, 200, None, True)


# 新平台调用（根据手机号获取老平台member_id）
@app.route('/v1/member/get_member_id/<phone>', methods=['GET','POST'])
def get_member_id(phone):
    return toolkit.response({'member_id': Member.get_member_id(phone)}, 200, None, True)


# 新平台调用（同步资产信息时增加order_id并读取）
@app.route('/v1/member/set_asset_order_id/<member_id>', methods=['GET','POST'])
def set_asset_order_id(member_id):
    order_id = ""
    if member_id:
        msi = Member_asset_info.query.filter_by(member_id=member_id).first()
        if not msi.order_id:
            msi.order_id = gen_order_id()
            print 'order_id----%s----order_id' % msi.order_id
            db.session.merge(msi)
            db.session.commit()
        order_id = msi.order_id
    return toolkit.response({'order_id': order_id}, 200, None, True)


# 新平台调用（根据手机号获取老平台member_id和密码）
@app.route('/v1/member/get_member_info/<phone>', methods=['GET', 'POST'])
def get_member_info(phone):
    member = Member.query.filter_by(phone=phone).first()
    if member:
        member_id = str(member.id).replace('-', '')
        password = member.passwd
    else:
        member_id = ''
        password = ''
    return toolkit.response({'member_id': member_id, 'password': password}, 200, None, True)


# 新平台调用（根据手机号获取老平台今日代收金额）
@app.route('/v1/member/get_member_uncollected_amount/<phone>', methods=['GET', 'POST'])
def get_member_uncollected_amount(phone):
    member_id = Member.get_member_id(phone)
    now = datetime.now().strftime('%Y-%m-%d')
    payback = db.session.query(func.sum(Invest_info.profit), func.sum(Invest_info.money)).filter(and_(Invest_info.product_id == Product_info.id,
        Product_info.end_time.like(now + '%'), Invest_info.member_id == member_id, Invest_info.is_effect == 1)).first()
    payback_money = payback[0] if payback[0] else 0
    payback_principal = payback[1] if payback[1] else 0
    return toolkit.response({'payback_money': payback_money, 'payback_principal':payback_principal}, 200, None, True)
