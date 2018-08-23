#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from datetime import datetime, timedelta
from sqlalchemy import and_, or_
from flask import request

from apps import app
from models import Prize, PrizeType, PrizeShare, Activity

from apps.member.models import Member
from apps.asset.models import Member_red_pocket, Member_red_pocket_type
from apps.utils import toolkit
from apps.dbinstance import db


def gen_reg_red_pocket(red_pocket_id, member_id):

    mrt = Member_red_pocket_type.query.filter(Member_red_pocket_type.id == red_pocket_id).first()
    now_time = datetime.now()
    gen_time = datetime.strftime((now_time  + timedelta(int(mrt.validtime))), '%Y-%m-%d %H:%M:%S')
    mr = Member_red_pocket(member_id=member_id, sort_id=mrt.id, generate_time=gen_time)
    return mr

@app.route("/v1/prize/<phone>", methods=['GET','POST'])
def post_prize_result(phone):

    prize_id = request.form.get("prize_id", None)
    activity_id = request.form.get("activity_id", None)
    response_data = {}
    if prize_id is None:
        response_data["code"] = u"10001"
        response_data["desc"] = u"参数为空"
        response_data["content"] = {}
        return toolkit.response(response_data, 200, None, True)

    m = Member.query.filter(Member.phone == phone).first()

    if m.isblack == 'Sync':
        response_data["code"] = u"10002"
        response_data["content"]={}
        response_data["desc"] = u"您的账户已被迁移到菠萝理财存管版，请用菠萝理财存管版登录！"
        return toolkit.response(response_data, 200, None, True)

    if m is None:
        response_data["code"] = u"10002"
        response_data["desc"] = u"用户不存在"
        response_data["content"] = {}
        return toolkit.response(response_data, 200, None, True)

    p = PrizeType.query.filter(or_(PrizeType.id == prize_id, PrizeType.hongbao_id == prize_id)).first()
    if p is None:
        response_data["code"] = u"10007"
        response_data["desc"] = u"奖品不存在"
        response_data["content"] = {}
        return toolkit.response(response_data, 200, None, True)

    pr = Prize.query.filter(Prize.phone == phone, Prize.activity_id == activity_id).all()
    ps = PrizeShare.query.filter(PrizeShare.phone == phone, PrizeShare.activity_id == activity_id).first()
    if ps is None:
        response_data["code"] = u"10009"
        response_data["desc"] = u"尚未注册手机号"
        response_data["content"] = {}
        return toolkit.response(response_data, 200, None, True)

    if len(pr) >= ps.total_num:
        response_data["code"] = u"10003"
        response_data["desc"] = u"抽奖次数已用尽"
        response_data["content"] = {}
        return toolkit.response(response_data, 200, None, True)

    if len(pr) < ps.total_num:
        now_time = datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M:%S')
        try:
            pp = Prize(phone=m.phone, prize_id=prize_id, time=now_time, activity_id=activity_id)
            if prize_id == "36dc6dd45146b629015146b77be30004" or \
               prize_id == "36dc6dd45146b629015146b7ad080006" or \
               prize_id == "40288007518b44c901518b5007bd0001" or \
               prize_id == "8a2db3e852a0744f0152a0860865000d" or \
               prize_id == "8a2db3e852a0744f0152a08651e0000f" or \
               prize_id == "8a2db3e852a0744f0152a0867e220011" or \
               prize_id == "8a2db3e852a0744f0152a086efad0013":
                mr = gen_reg_red_pocket(p.hongbao_id, str(m.id).replace("-", ""))
                db.session.add(mr)
                db.session.commit()
                pp.is_grant = 1

            db.session.add(pp)    
            db.session.commit()
            response_data["code"] = u"10000"
            response_data["desc"] = u"抽奖成功"
            response_data["content"] = {}

            return toolkit.response(response_data, 200, None, True)
        except:
            response_data["code"] = u"10004"
            response_data["desc"] = u"抽奖出现网络错误"
            response_data["content"] = {}
            return toolkit.response(response_data, 200, None, True)
    else:
        response_data["code"] = u"10003"
        response_data["desc"] = u"抽奖次数已用尽"
        response_data["content"] = {}
        return toolkit.response(response_data, 200, None, True)


@app.route("/v1/prize/share/<phone>", methods=['GET','POST'])
def post_prize_share(phone):

    response_data = {}
    activity_id = request.form.get("activity_id", None)
    m = Member.query.filter(Member.phone == phone).first()

    if m.isblack == 'Sync':
        response_data["code"] = u"10002"
        response_data["content"]={}
        response_data["desc"] = u"您的账户已被迁移到菠萝理财存管版，请用菠萝理财存管版登录！"
        return toolkit.response(response_data, 200, None, True)

    if m is None:
        response_data["code"] = u"10002"
        response_data["desc"] = u"用户不存在"
        response_data["content"] = {}
        return toolkit.response(response_data, 200, None, True)

    ps = PrizeShare.query.filter(PrizeShare.phone == phone, PrizeShare.activity_id == activity_id).first()
    if ps is None:
        response_data["code"] = u"10003"
        response_data["desc"] = u"用户基础数据不存在"
        response_data["content"] = {}
        return toolkit.response(response_data, 200, None, True)
    try:
        ps.is_share=1
        ps.total_num += 1
        db.session.merge(ps)
        db.session.commit()
        response_data["code"] = u"10000"
        response_data["desc"] = u"抽奖次数增加成功"
        response_data["content"] = {}
        return toolkit.response(response_data, 200, None, True)
    except:
        response_data["code"] = u"10004"                                
        response_data["desc"] = u"抽奖出现网络错误"
        response_data["content"] = {}
        return toolkit.response(response_data, 200, None, True)


@app.route("/v1/prize/records/share/<phone>", methods=['GET','POST'])
def post_prize_records_share(phone):
   
    activity_id = request.form.get("activity_id", None) 
    response_data = {}
    m = Member.query.filter(Member.phone == phone).first()

    if m.isblack == 'Sync':
        response_data["code"] = u"10002"
        response_data["content"]={}
        response_data["desc"] = u"您的账户已被迁移到菠萝理财存管版，请用菠萝理财存管版登录！"
        return toolkit.response(response_data, 200, None, True)

    ac = Activity.query.filter(Activity.id == activity_id).first()
    if ac is None:
        response_data["code"] = u"10007"
        response_data["desc"] = u"活动不存在"
        response_data["content"] = {}
        return toolkit.response(response_data, 200, None, True)
    ps = PrizeShare.query.filter(PrizeShare.phone == phone, PrizeShare.activity_id == activity_id).first()
    if ps is None:
        try:
            ps = PrizeShare(phone=phone, is_share=0, activity_id=activity_id, total_num=ac.default_num)
            db.session.add(ps)
            db.session.commit()
            response_data["code"] = u"10000"
            response_data["desc"] = u"抽奖数据初始化成功"
            response_data["content"] = {}
            return toolkit.response(response_data, 200, None, True)
        except:
            response_data["code"] = u"10004"                                
            response_data["desc"] = u"抽奖出现网络错误"
            response_data["content"] = {}
            return toolkit.response(response_data, 200, None, True)
    else:
        response_data["code"] = u"10005"                        
        response_data["desc"] = u"抽奖数据已存在"
        response_data["content"] = {}
        return toolkit.response(response_data, 200, None, True)


@app.route("/v1/prize/counts/<phone>", methods=['GET','POST'])
def post_prize_count(phone):
    
    response_data = {}
    activity_id = request.form.get("activity_id", None)
    m = Member.query.filter(Member.phone == phone).first()
    if m is None:
        response_data["code"] = u"10002"
        response_data["desc"] = u"用户不存在"
        response_data["content"] = {}
        return toolkit.response(response_data, 200, None, True)
    pr = Prize.query.join(Activity).filter(Prize.phone == phone, Prize.activity_id == activity_id).all()
    ps = PrizeShare.query.filter(PrizeShare.phone == phone, PrizeShare.activity_id == activity_id).first()
    response_data["code"] = u"10000"
    response_data["desc"] = u"数据请求成功"
    response_data["content"] = {"count": len(pr), "total_count": ps.total_num}
    return toolkit.response(response_data, 200, None, True)

@app.route("/v1/prize/list", methods=['GET','POST'])
def get_prize_count():
    
    response_data = {}
    activity_id = request.form.get("activity_id", None)
    m = Activity.query.filter(Activity.id == activity_id).first()
    if m is None:
        response_data["code"] = u"10002"
        response_data["desc"] = u"活动不存在"
        response_data["content"] = {}
        return toolkit.response(response_data, 200, None, True)
    query_top = db.session.query(Prize, PrizeType)
    pr = query_top.filter(and_(Prize.prize_id == PrizeType.id , Prize.activity_id == activity_id)).all()
    response_data["code"] = u"10000"
    response_data["desc"] = u"数据请求成功"
    response_data["content"] = []
    for item in pr:
        response_data["content"].append(dict(phone=item[0].phone, time=str(item[0].time), name=item[1].name))
    return toolkit.response(response_data, 200, None, True)
