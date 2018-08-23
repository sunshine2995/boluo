#!/use/bin/env python
# -*- coding: UTF-8 -*-

import os
import qrcode
from datetime import datetime, timedelta
from PIL import Image
from apps.dbinstance import db
from apps.asset.models import Member_red_pocket, Member_red_pocket_type, Member_asset_info, Province_city
from models import Member, Member_invite,Member_login
from sqlalchemy import and_, or_
from config import BOLUO_URL
from random import randint


def gen_reg_red_pocket(type, member_id, start_money):

    mrt = Member_red_pocket_type.query.filter(and_(Member_red_pocket_type.type == type,
                                                   Member_red_pocket_type.start_money==start_money)).first()
    now_time = datetime.now()
    gen_time = datetime.strftime((now_time  + timedelta(int(mrt.validtime))), '%Y-%m-%d %H:%M:%S')
    mr = Member_red_pocket(member_id=member_id,sort_id=mrt.id, generate_time=gen_time)
    return mr


def do_register(phone, member_id=None):
    try:
        # 判断被邀请人是否已在用户表中
        if phonecheck(phone) == False:
            return (False, '手机号不合法')
        indm = Member.query.filter(Member.phone == phone).first()
        if indm:
            return (False, '用户名已注册')
        register_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        invite = Member_invite.query.filter(Member_invite.is_use == 0).first()
        invite.is_use = 1
        db.session.merge(invite)
        
        qrcode_path = "%s_%s.png" % (phone, phone)

        try:
            gen_qrcode("%s/v1/html5/invate/%s" % (BOLUO_URL, invite.invitation_code),
                       "/home/wwwroot/qrcode/new_member_qr/%s" % qrcode_path, "/home/wwwroot/qrcode/qrlogo.png")
        except:
            pass
        m = Member(name=phone, phone=phone, reg_time=register_time, is_email_bind=False,
                   is_pay_bind=False, is_identity_bind=False,invitation_code = invite.invitation_code, qrcode=qrcode_path)
        if member_id:
            exist_member = Member.query.filter(Member.id == member_id).first()
            if exist_member:
                pass
            else:
                m.id = member_id
        db.session.add(m)
        db.session.commit()
        ma = Member_asset_info(member_id=m.id, member_name=phone)
        db.session.add(ma)

        red_list = []
        type = "1"
        red_list.append(gen_reg_red_pocket(type, m.id, 990))
        red_list.append(gen_reg_red_pocket(type, m.id, 1980))
        red_list.append(gen_reg_red_pocket(type, m.id, 4980))
        red_list.append(gen_reg_red_pocket(type, m.id, 9900))
        for item in red_list:
            db.session.add(item)
        db.session.commit()
    except Exception,e:
        print '==============='
        print e
        print '==============='
        return (False, '数据库操作失败')
    return (True, m)


def phonecheck(s):
    # 号码前缀，如果运营商启用新的号段，只需要在此列表将新的号段加上即可。
    # phoneprefix = ['130', '131', '132', '133', '134', '135', '136', '137', '138', '139', '150', '151', '152', '153',
    #                '156', '158', '159', '170', '183', '182', '185', '186', '187', '188', '189', '180']
    # 检测号码是否长度是否合法。
    if len(s) != 11:
        return False
    else:
        # 检测输入的号码是否全部是数字。
        if s.isdigit():
            # 检测前缀是否是正确。
            # if s[:3] in phoneprefix:
            #     return True
            # else:
            #     return False
            return True
        else:
            return False


def init_login_token(phone, equipment_token, equipment_name):
    m = Member.query.filter(Member.phone==phone).first()
    try:
        import socket
        ip = socket.gethostbyname(socket.gethostname())
    except:
        ip = ''
    try:
        last_time = datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M:%S')
        mlogin = Member_login.query.filter(and_(Member_login.member_name==phone)).order_by(Member_login.over_time.desc()).first()
        over_time = datetime.now() + timedelta(days=365)
        login_token = '%s-%s' % (datetime.strftime(datetime.now(), '%Y-%m-%d'), randint(1000000000, 10000000000))

        print mlogin, '123'

        if mlogin:
            mlogin.last_time = last_time
            mlogin.login_token = login_token
            mlogin.over_time = over_time
            mlogin.last_ip = ip
            mlogin.equipment_token = equipment_token
            mlogin.equipment_name = equipment_name
            db.session.merge(mlogin)
            db.session.commit()
        else:
            ml = Member_login(member_id=m.id, member_name=phone, last_time=last_time, login_token=login_token,
                              equipment_name=equipment_name, equipment_token=equipment_token, over_time=over_time, last_ip=ip)
            login_token = ml.login_token
            db.session.add(ml)
            db.session.commit()
    except Exception, e:
        print 'login_token====error'
        print e
        print 'login_token===='
        login_token = None

    return login_token


def gen_qrcode(string, path, logo):
    qr = qrcode.QRCode(version=2,error_correction=qrcode.constants.ERROR_CORRECT_H,
                       box_size=9, border=1)
    qr.add_data(string)
    qr.make(fit=True)
    img = qr.make_image()
    img = img.convert("RGBA")
    if logo and os.path.exists(logo):
        icon = Image.open(logo)
        img_w, img_h = img.size
        factor = 4
        size_w = int(img_w / factor)
        size_h = int(img_h / factor)
        icon_w, icon_h = icon.size
        if icon_w > size_w:
            icon_w = size_w
        if icon_h > size_h:
            icon_h = size_h
        icon = icon.resize((icon_w, icon_h), Image.ANTIALIAS)
        w = int((img_w - icon_w) / 2)
        h = int((img_h - icon_h) / 2)
        icon = icon.convert("RGBA")
        img.paste(icon, (w, h), icon)
    img.save(path)

