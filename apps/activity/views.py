# -*- coding: UTF-8 -*-

import random
from functools import wraps
from datetime import date, timedelta
from datetime import datetime
import json

from flask import render_template, redirect, url_for, request, g
from sqlalchemy import and_, or_, func, distinct
from apps import app
from apps.utils.code_message import code_date_to_dict
from config import BIG_AWARDS_NUM

from apps.dbinstance import db
from apps.member.models import Member, Member_login, Member_invite_info
from apps.activity.models import Zillionaire_info, Sign_record, Points_change, \
    Prize_order, Prize_image, Integral_record, Activity_status, Lottery_record
from apps.rewards.models import Activity, PrizeType, Prize
from apps.asset.models import Member_asset_info, Member_red_pocket, Order_dict, Member_income_statement, Member_red_pocket_type, Member_income_statement, Member_recharge_info
from apps.utils import toolkit
from apps.product.models import Invest_info, Product_info
from apps.activity.utils import xj_red_pocket, lc_red_pocket, add_integral_record, phone_to_member_id, school_starts_information
from apps.html5.utils import hide_some_fields


def check_activity(activity_name='大富翁活动'):
    def middle_deco(decorated_func):
        @wraps(decorated_func)
        def _deco():
            phone = request.args.get('phone')
            token = request.args.get('token')
            isnotauth = None
            if not phone or not token:
                isnotauth = True
                g.isnotauth = isnotauth
            if phone and token:
                t = Member_login.query.filter_by(member_name=phone, login_token=token).first()
                if t is None:
                    return redirect(url_for('h5_login'))
                elif t.over_time < datetime.now():
                    return redirect(url_for('h5_login'))
                g.phone = phone
                g.token = token
                g.isnotauth = isnotauth

                activity = Activity.query.filter_by(name=activity_name).first()
                activity_info = Zillionaire_info.query.filter_by(phone=phone, activity_id=activity.id).first()

                if activity_info is None:
                    act = Zillionaire_info(phone=phone, activity_id=activity.id)
                    db.session.add(act)
                    db.session.commit()

            return decorated_func()
        return _deco
    return middle_deco


def check_phone_and_token_ajax():
    def middle_deco(decorated_func):
        @wraps(decorated_func)
        def _deco():
            phone = request.args.get('phone')
            token = request.args.get('token')
            if not phone or not token:
                return toolkit.response(code_date_to_dict("10001"), 200, None, True)
            if phone and token:
                t = Member_login.query.filter_by(member_name=phone, login_token=token).first()
                if t is None:
                    return toolkit.response(code_date_to_dict("10002"), 200, None, True)
                elif t.over_time < datetime.now():
                    return toolkit.response(code_date_to_dict("10003"), 200, None, True)
            return decorated_func()
        return _deco
    return middle_deco


def check_ajax(func):
    @wraps(func)
    def _deco(phone, **kwargs):
        member = Member.query.filter_by(phone=phone).first()
        if member is None:
            return redirect(url_for('index'))
        token = kwargs.get('token')
        if token:
            t = Member_login.query.filter_by(member_name=phone, login_token=token).first()
            if t is None:
                return redirect(url_for('index'))
            elif t.over_time < datetime.now():
                return redirect(url_for('index'))

        activity = Activity.query.filter_by(name='大富翁活动').first()
        activity_info = Zillionaire_info.query.filter_by(phone=phone, activity_id=activity.id).first()

        if activity_info is None:
            act = Zillionaire_info(phone=phone, activity_id=activity.id)
            db.session.add(act)
            db.session.commit()
        return func(phone, **kwargs)
    return _deco


# 往资金表里加积分
def integralCalculator(phone, score, isAdd):
    member = Member.query.filter_by(phone=phone).first()
    asset = Member_asset_info.query.filter_by(member_id=member.id).first()
    activity = Activity.query.filter_by(name='大富翁活动').first()
    zill_info = Zillionaire_info.query.filter_by(phone=phone, activity_id=activity.id).first()
    if isAdd is True:
        asset.score += score
    else:
        asset.score -= score
    db.session.merge(asset)
    db.session.merge(zill_info)


# 签到页面接口
@app.route('/v1/activity/sign')
@check_activity(activity_name='大富翁活动')
def activityIndex():
    phone = g.phone
    token = g.token
    renderData = {'phone': phone, 'token': token}
    sign = Sign_record.query.filter_by(phone=phone).order_by(Sign_record.check_time.desc()).first()
    if sign is None:
        renderData['days'] = 0
        renderData['dateArray'] = []
        renderData['isSigned'] = False
        renderData['tomorrow'] = 1
    else:
        renderData['days'] = sign.check_number
        renderData['dateArray'] = thisMouthSignUpDay(phone)
        today = Sign_record.query.filter_by(check_time=date.today(), phone=phone).first()
        if today is None:
            renderData['isSigned'] = False
        else:
            renderData['isSigned'] = True
        renderData['tomorrow'] = pineappleNum(sign.check_number + 1)
    # ----------------积分商城逻辑---------------------
    images = []
    prizes = []
    member = Member.query.filter_by(phone=phone).first()
    asset = Member_asset_info.query.filter_by(member_id=member.id).first()
    prize_image_top = db.session.query(Prize_image)
    prize_image_ques = prize_image_top.all()
    prize_ques = []

    ids = creatPrizesidsList()
    for iid in ids:
        pri = PrizeType.query.filter_by(id=iid).first()
        if pri and pri.status == 1:
            prize_ques.append(pri)

    for pi in prize_image_ques:
        images.append((pi.prize_id, pi.image))

    for p in prize_ques:
        di = {'id': str(p.id).replace('-', ''), 'name': p.name, 'status': p.status, 'deadline': p.deadline,
              'input_time': p.input_time,
              'score': p.score, 'description': p.description, 'images': []}
        prizes.append(di)
    for prize_id, img in images:
        for p in prizes:
            if str(p['id']).replace('-', '') == str(prize_id):
                p['images'].append(img)
    renderData['score'] = asset.score
    renderData['prize_list'] = prizes[0:6]

    # --------------------------------------------
    return render_template('/activity/sign.html', renderData=renderData)


# 签到ajax接口
@app.route('/v1/activity/signrecord/<phone>/<token>')
@check_ajax
def signrecord(phone, token):
    today = date.today()
    response_data = {}
    m = Member.query.filter(or_(Member.name == phone, Member.phone == phone)).first()
    if m.isblack == 'Sync':
        response_data["code"] = u"10002"
        response_data["content"]={}
        response_data["desc"] = u"您的账户已被迁移到菠萝理财存管版，请用菠萝理财存管版登录！"
        return toolkit.response(response_data, 200, None, True)

    t = Sign_record.query.filter_by(check_time=today, phone=phone).first()
    activity = Activity.query.filter_by(name='大富翁活动').first()
    response_data = {'token': token}
    if t is not None:
        response_data['days'] = t.check_number
    else:
        y = Sign_record.query.filter_by(check_time=today - timedelta(days=1), phone=phone).first()
        if y is not None:
            checkNumber = y.check_number + 1
            activity_info = Zillionaire_info.query.filter_by(phone=phone, activity_id=activity.id).first()
            sign_description = '签到'
            add_zill = 0
            if (checkNumber >= 5) and ((checkNumber - 5) % 5) == 0:
                activity_info.sign_number += 1
                activity_info.use_number_max += 1

            if activity_info.investment >= activity_info.use_number_max * 2000:
                if activity_info.sign_number > 0:
                    activity_info.use_number += activity_info.sign_number
                    add_zill = activity_info.sign_number
                    activity_info.sign_number = 0

            elif activity_info.investment <= activity_info.use_number_max * 2000:
                snm = int(activity_info.investment / 2000) - (activity_info.use_number_max - activity_info.sign_number)
                if snm > 0:
                    activity_info.sign_number -= snm
                    activity_info.use_number += snm
                    add_zill = snm

            db.session.merge(activity_info)
            db.session.commit()

            newact = Sign_record(check_number=checkNumber, integral=pineappleNum(checkNumber), phone=phone,
                                 check_time=today)
            integralCalculator(phone, pineappleNum(checkNumber), True)
            change = Points_change(phone=phone, time=datetime.now(), score=pineappleNum(checkNumber),
                                   description=sign_description, num=add_zill)

            db.session.add(change)
            db.session.add(newact)
            db.session.commit()
            response_data['days'] = checkNumber
        else:
            newact = Sign_record(phone=phone, check_time=today)
            integralCalculator(phone, 1, True)
            change = Points_change(phone=phone, time=datetime.now(), score=1, description='签到')

            db.session.add(change)
            db.session.add(newact)
            db.session.commit()
            response_data['days'] = 1


    return toolkit.response(response_data, 200, None, True)


# 新版本大富翁接口
@app.route('/v1/activity/zill/index', methods=['GET', 'POST'])
@check_activity(activity_name='大富翁活动')
def index():
    if g.isnotauth is None:
        phone = g.phone
        token = g.token
        # 活动管理表,根据名称查询活动,id 主键 name(活动名称) end_time 结束时间 start_time 开始时间 prize_ids 奖品ID串 default 默认抽奖次数
        activity = Activity.query.filter_by(name='大富翁活动').first()

        # 根据活动的id,用户的电话查询用户对应大富翁活动信息,id主键 activity_id 活动id phone会员电话 use_number可用摇奖次数
        zill_info = Zillionaire_info.query.filter_by(phone=phone, activity_id=activity.id).first()

        #根据用户电话查询会员信息
        member = Member.query.filter_by(phone=phone).first()
        #根据会员查询会员资金信息
        asset = Member_asset_info.query.filter_by(member_id=member.id).first()
        #asset.score:会员积分
        renderData = {'use_number': 0, 'phone': phone, 'score': asset.score, 'token': token}
        # user.number:可用摇奖次数
        if zill_info.use_number > 0:
            response_data = {}
            if member.isblack == 'Sync':
                return "请在新平台参加大富翁活动"

            result = random_pick()
            # 新建活动表更新商品id
            prizesids = creatPrizesidsList()
            prize = None
            for prizeid in prizesids:
                p = PrizeType.query.filter_by(id=prizeid).first()
                if p.dice == result:
                    prize = p
            if prize is None:
                zill_info.prize_id = '0'
            else:
                zill_info.prize_id = str(prize.id).replace('-', '')
            db.session.merge(zill_info)
            db.session.commit()
            renderData['use_number'] = zill_info.use_number
            renderData['rollResult'] = str(result)
            renderData['prize_id'] = zill_info.prize_id
            renderData['enabled'] = True
        else:
            renderData['enabled'] = False
        renderData['login_in'] = 'True'

        personal_top = db.session.query(Prize, PrizeType)
        personal_list = personal_top.filter(and_(PrizeType.id == Prize.prize_id, Prize.phone == phone)).order_by(
            Prize.time.desc()).all()
        renderData['PersonalList'] = []
        for item in personal_list:
            renderData['PersonalList'].append((item[0].time, item[1].name))

        memberPrizeInfoList = []
        prizeType_top = db.session.query(PrizeType, Prize, Activity, PrizeType.name, Prize.phone)
        prizeTypes = prizeType_top.filter(
            and_(PrizeType.id == Prize.prize_id, Activity.id == Prize.activity_id, Activity.name == '大富翁活动'
                 )).order_by(Prize.time.desc()).limit(4).all()
        for m in prizeTypes:
            memberPrizeInfoList.append((convertPhone(m.phone), m.name))
            renderData['memberPrizeInfoList'] = memberPrizeInfoList
    else:
        renderData = {'use_number': 0, 'score': 0}
        memberPrizeInfoList = []
        prizeType_top = db.session.query(PrizeType, Prize, Activity, PrizeType.name, Prize.phone)
        prizeTypes = prizeType_top.filter(
            and_(PrizeType.id == Prize.prize_id, Activity.id == Prize.activity_id, Activity.name == '大富翁活动'
                 )).order_by(Prize.time.desc()).limit(4).all()
        for m in prizeTypes:
            memberPrizeInfoList.append((convertPhone(m.phone), m.name))
            renderData['memberPrizeInfoList'] = memberPrizeInfoList
    return render_template('/activity/Xinnian.html', renderData=renderData)


# 摇色子ajax
@app.route('/v1/activity/zill/ajax/<phone>/<token>')
@check_ajax
def zillajax(phone, token):
    response_data = {'token': token}
    prize_id = request.args.get('prize_id')
    member = Member.query.filter_by(phone=phone).first()

    if member.isblack == 'Sync':
        response_data["code"] = u"10002"
        response_data["content"]={}
        response_data["desc"] = u"您的账户已被迁移到菠萝理财存管版，请用菠萝理财存管版登录！"
        return toolkit.response(response_data, 200, None, True)

    asset = Member_asset_info.query.filter_by(member_id=member.id).first()
    activity = Activity.query.filter_by(name='大富翁活动').first()

    zill_info = Zillionaire_info.query.filter_by(phone=phone, activity_id=activity.id).first()
    memberInfo = Member.query.filter_by(phone=phone).first()
    now_time = datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M:%S')

    if zill_info.use_number > 0 and prize_id==zill_info.prize_id:
        zill_info.use_number -= 1
        db.session.merge(zill_info)
        # 向用户中奖表里添加商品
        prize = Prize(prize_id=zill_info.prize_id, phone=phone, time=datetime.now(), is_grant=0,
                      activity_id=str(zill_info.activity_id).replace('-', ''))
        type = PrizeType.query.filter_by(id=str(zill_info.prize_id).replace('-', '')).first()

        if type.ptype == '菠萝币':
            integralCalculator(phone, type.score, True)
            change = Points_change(phone=phone, time=datetime.now(), score=type.score, description='摇骰子')

            db.session.add(change)
        elif type.ptype == '实物':
            prizeorder = Prize_order(phone=phone, prize_id=str(type.id).replace('-', ''), \
                                     prize_name=type.name, score=type.score, money=type.money, status=0, \
                                     time=datetime.now(), activity_id=str(activity.id).replace('-',''), channel_num=1)
            db.session.add(prizeorder)
            pass
        elif type.ptype == '现金':
            xj_red_pocket(str(memberInfo.id).replace('-', ''), type.money)
            order = Order_dict.query.filter_by(is_use=False).first()
            order.is_use = True
            income = Member_income_statement(member_id=str(member.id).replace('-', ''), type='到账红包', money=type.money, \
                                    balance=asset.rechargeamount + asset.remainamount, time=now_time, info='大富翁现金红包', order_id=order.order_id, \
                                     phone=phone)
            db.session.merge(order)
            db.session.add(income)
            db.session.commit()
        elif type.ptype == '红包':

            lc_red_pocket(str(memberInfo.id).replace('-', ''), type.hongbao_id)
        response_data['data'] = 'success'
        db.session.add(prize)
        db.session.commit()
        response_data['use_number'] = zill_info.use_number
        response_data['score'] = asset.score
        response_data['dice_num'] = type.dice
    return toolkit.response(response_data, 200, None, True)


# 新版大转盘  http://0.0.0.0:8000/v1/activity/dzp?phone=18636747623&token=2017-06-15-2362957679
@app.route('/v1/activity/dzp', methods=['GET', 'POST'])
@check_activity(activity_name='大富翁活动')
def dzp():
    memberPrizeInfoList = []
    renderData = {'use_number': 0}
    activity = Activity.query.filter_by(name='大富翁活动').first()
    activity_dzp = Activity.query.filter_by(name='大转盘活动').first()
    #已登陆
    if g.isnotauth is None:
        phone = g.phone
        token = g.token
        zill_info = Zillionaire_info.query.filter_by(phone=phone, activity_id=activity.id).first()

        # 会员管理,详细的客户信息
        member = Member.query.filter_by(phone=phone).first()
        member_id = str(member.id).replace('-','')
        # 会员资金表,返回客户资金情况
        asset = Member_asset_info.query.filter_by(member_id=member.id).first()
        renderData = {'phone': phone, 'score': asset.score, 'token': token}
        # 已登陆已邦卡
        if member.is_pay_bind == 1:
            renderData['is_paybind'] = True
            if zill_info.use_number02 > 0:
                renderData['use_number'] = zill_info.use_number02
                renderData['enabled'] = True
            else:
                renderData['use_number'] = 0
                renderData['enabled'] = False
        else:
            renderData['is_paybind'] = False

        renderData['login_in'] = 'True'


        personal_top = db.session.query(Prize, PrizeType)
        personal_list = personal_top.filter(and_(PrizeType.id == Prize.prize_id, Prize.phone == phone,Prize.activity_id==str(activity_dzp.id).replace('-',''))).order_by(
            Prize.time.desc()).all()
        renderData['PersonalList'] = []
        for item in personal_list:
            renderData['PersonalList'].append((item[0].time, item[1].name))

        activity_begin = '%s-%s-%s 00:00:00' % (2017, 8 , 4)
        activity_end = '%s-%s-%s 00:00:00' % (2017, 8 , 19)


        invest_30 = db.session.query(func.sum(Invest_info.money + Invest_info.hongbao))\
            .filter(and_(Invest_info.member_id==member_id,
            Invest_info.product_id == Product_info.id,Product_info.time_limit=='30', Product_info.product_type != '新手标', Invest_info.time.between(activity_begin,activity_end))).scalar()
        invest_90 = db.session.query(func.sum(Invest_info.money + Invest_info.hongbao)).filter(and_(Invest_info.member_id == member_id,
                         Invest_info.product_id == Product_info.id, Product_info.time_limit == '90',
                         Invest_info.time.between(activity_begin, activity_end))).scalar()
        invest_180 = db.session.query(func.sum(Invest_info.money + Invest_info.hongbao)).filter(and_(Invest_info.member_id == member_id,
                                                                              Invest_info.product_id == Product_info.id,
                                                                              Product_info.time_limit == '180',
                                                                              Invest_info.time.between(activity_begin,
                                                                                                       activity_end))).scalar()
        total = (invest_30 or 0)  / 2 + (invest_90 or 0) + (invest_180 or 0) * 2
        realtotal = total or 0
        renderData['activity_invest'] = round(realtotal,2)


    prizeType_top = db.session.query(PrizeType, Prize, PrizeType.name, Prize.phone)
    prizeTypes = prizeType_top.filter(
        and_(PrizeType.id == Prize.prize_id, Prize.activity_id==str(activity_dzp.id).replace('-', ''),
             )).order_by(Prize.time.desc()).limit(8).all()
    for m in prizeTypes:
        memberPrizeInfoList.append((convertPhone(m.phone), m.name))
    renderData['memberPrizeInfoList'] = memberPrizeInfoList
    return render_template('activity/august.html', renderData=renderData)


# 大转盘摇奖ajax  http://0.0.0.0:8000/v1/activity/dzp/ajax/18636747623/2017-06-15-2362957679
@app.route('/v1/activity/dzp/ajax/<phone>/<token>')
@check_ajax
def dzpajax(phone, token):
    # dzp_log('收到信息')
    response_data = {'token': token}
    #活动管理,找出奖品的id串 活动id   -->外键：tjtyy_activity 中奖关系管理表,指向的是活动管理表中id相同的那条记录
    activity = Activity.query.filter_by(name='大富翁活动').first()
    activity_dzp = Activity.query.filter_by(name='大转盘活动').first()
    #根据用户手机号,活动id查询大富翁或去哦带那个信息
    zill_info = Zillionaire_info.query.filter_by(phone=phone, activity_id=activity.id).first()
    #会员管理,详细的客户信息
    member = Member.query.filter_by(phone=phone).first()

    if member.isblack == 'Sync':
        response_data["code"] = u"10002"
        response_data["content"]={}
        response_data["desc"] = u"您的账户已被迁移到菠萝理财存管版，请用菠萝理财存管版登录！"
        return toolkit.response(response_data, 200, None, True)

    member_id = str(member.id).replace('-', '')
    #会员资金表,返回客户资金情况
    asset = Member_asset_info.query.filter_by(member_id=member_id).first()
    result = random_pick02()

    # 新建活动表更新商品id,从奖品管理表找到--
    # pt = PrizeType.query.filter(PrizeType.dice02==result).first()
    #查询大转盘活动点数为2的奖品-
    pt = PrizeType.query.filter(PrizeType.dice02 == result).first()
    # zillionaire/prize_id  == prize/id
    #当返回的result的值跟数据库中转盘奖品点数相同,说明中奖.

    zill_info.prize_id = str(pt.id).replace('-', '')
    if zill_info.use_number02 > 0:
        #每摇一次奖,可用数减一

        #更新当前抽奖用户的信息活动次数减少,直接修改数据库

        # 向用户中奖表里添加商品
        if zill_info.prize_id != '0':
            #向会员中奖礼物表中添加记录
            prize = Prize(prize_id=zill_info.prize_id, phone=phone, time=datetime.now(), is_grant=0,
                          activity_id=str(activity_dzp.id).replace('-',''))
            db.session.add(prize)
            zill_info.use_number02 -= 1
            db.session.merge(zill_info)
            if pt.ptype == '菠萝币':
                integralCalculator(phone, pt.score, True)
                change = Points_change(phone=phone, time=datetime.now(), score=pt.score, description='大转盘')
                db.session.add(change)
                db.session.commit()
            elif pt.ptype == '现金':
                xj_red_pocket(member_id, pt.money)
                order = Order_dict.query.filter_by(is_use=False).first()
                income = Member_income_statement(member_id=member_id, type='到账红包',
                                                 money=pt.money, \
                                                 balance=asset.rechargeamount + asset.remainamount, time=datetime.now(),
                                                 info='大转盘现金红包', order_id=order.order_id, \
                                                 phone=phone)
                order.is_use = True
                db.session.merge(order)
                db.session.add(income)
                db.session.commit()
            elif pt.ptype == '红包' or pt.ptype == '加息劵':
                lc_red_pocket(member_id, pt.hongbao_id)


        db.session.commit()
        response_data['use_number'] = zill_info.use_number02
        response_data['score'] = asset.score
        response_data['result'] = result

    return toolkit.response(response_data, 200, None, True)

#father's day activity, select the prize randomly
def fathersday_random_pick(some_list,probabilities):
    x=random.uniform(0,1)
    cumulative_probability=0.0
    for item,item_probability in zip(some_list,probabilities):
        cumulative_probability +=item_probability
        if x<cumulative_probability:
            break
    return item


#father's day activity, prize_id,prize_identor,prize_name
def fathersday_prize(type,argu):
    prize_id=['fc0ff616ccd7418ca4181badba7d1985',
                      '6711a1fab6c0445d883d471bd223a7d9',
                      'b6ff237161b34a6694062b3983f0f002',
                      '9aedb15884044cd49ce4e657e772ce3f',
                      '703ff01aa4e54e65b53569b8773c763c',
                      '140bfb9b0f4e4963aba3be7729c40408',
                      '1a5d165883af4592a1d81b895f6fca9a',
                      'c02f5df4897d47759d2dd48a5e7d6f30',
                      'e7a60390764a49908361e29397480212',
                      '62aff94b256940b0bc776cb7ae3e2210',
                      '1404295174af4b15b926d2fe9bad5e5b']
    prize_name=['38元理财红包','20元理财红包','88元理财红包',
                '1%加息券','0.6%加息券','58元理财红包','18菠萝币',
                '88菠萝币','68菠萝币','288菠萝币','剃须刀']
    prize_identor=['boluo_b','boluo_a','boluo_h',
                   'boluo_r','boluo_c','boluo_g','boluo_e',
                   'boluo_f','boluo_j','boluo_k','boluo_d']
    if type==1:
        return prize_name[prize_id.index(argu)]
    if type==0:
        return prize_id[prize_identor.index(argu)]


#查找理财红包奖品对应的id,从而寻找hongbao_id
def fathersday_prize_hongbaoid(prize_type):
    prize_id =['fc0ff616ccd7418ca4181badba7d1985','6711a1fab6c0445d883d471bd223a7d9','b6ff237161b34a6694062b3983f0f002','140bfb9b0f4e4963aba3be7729c40408',
               '9aedb15884044cd49ce4e657e772ce3f','703ff01aa4e54e65b53569b8773c763c']
    prize_identor =['boluo_b','boluo_a','boluo_h','boluo_g',
                    'boluo_r', 'boluo_c']
    prize_index =prize_identor.index(prize_type)
    result =db.session.query(PrizeType.hongbao_id).filter_by(id =prize_id[prize_index]).first()
    return str(result[0]).replace('-','')


#返回抽奖后菠萝数目
def fathersday_pineapple_num(prize_type):
    prize_identor=['boluo_e','boluo_f','boluo_j','boluo_k']
    prize_index=prize_identor.index(prize_type)
    if prize_index==0:
        return 18
    elif prize_index==1:
        return 88
    elif prize_index==2:
        return 68
    elif prize_index==3:
        return 288

# 摇色子随机
def random_pick():
    somelist = [x for x in range(3, 19)]
    new_probabilities = PrizeType.query.filter(PrizeType.dice > 0).all()
    proArray = []
    for i in quicksort(new_probabilities):
        proArray.append(i.probability)
    probabilities = proArray
    x = random.uniform(0, 1)
    cumulative_probability = 0.0
    for item, item_probability in zip(somelist, probabilities):
        cumulative_probability += item_probability
        if x < cumulative_probability: break
    return str(item)

#大转盘随机
def random_pick02():
    somelist = [x for x in range(1, 11)]
    new_probabilities = PrizeType.query.filter(PrizeType.dice02 > 0).all()
    proArray = []
    for i in quicksort02(new_probabilities):
        proArray.append(i.probability)
    probabilities = proArray
    x = random.uniform(0, 1)
    cumulative_probability = 0.0
    for item, item_probability in zip(somelist, probabilities):
        cumulative_probability += item_probability
        if x < cumulative_probability: break
    return str(item)


#摇奖机随机
def random_pick03():
    somelist = [x for x in range(1, 7)]
    somelist = sorted(somelist,reverse=True)
    new_probabilities = [0.004,0.008,0.068,0.16,0.36,0.4]
    x = random.uniform(0, 1)
    cumulative_probability = 0.0
    for item, item_probability in zip(somelist, new_probabilities):
        cumulative_probability += item_probability
        if x < cumulative_probability: break
    return str(item)


# 这个月的签到天数
def thisMouthSignUpDay(phone):
    alldate = Sign_record.query.filter_by(phone=phone).all()
    dateArray = []
    for d in alldate:
        if d.check_time.month == date.today().month:
            dateArray.append(int(d.check_time.strftime('%d')) - 1)
    return dateArray


# 双十二抽奖随机
def random_pick_04(activity_id):
    new_probabilities = PrizeType.query.filter_by(activity_id=str(activity_id).replace('-', '')).all()
    proArray = []
    for i in new_probabilities:
        proArray.append((i.act_dice, i.probability))
    x = random.uniform(0, 1)
    cumulative_probability = 0.0
    for item, item_probability in proArray:
        cumulative_probability += item_probability
        if x < cumulative_probability: break
    return str(item)


# 菠萝
def pineappleNum(checkNum):
    if checkNum <= 7:
        l = [1, 3, 10, 10, 10, 10, 10]
        return l[checkNum - 1]
    else:
        return 10


# 手机号隐藏
def convertPhone(phone):
    return phone[0:2] + '****' + phone[7:12]


# 创建当前活动的商品id列表
def creatPrizesidsList(activity_name='大富翁活动'):
    theActivity = Activity.query.filter_by(name=activity_name).first()
    prizesids = theActivity.prize_ids.split(',')
    prizeidList = []
    for prizeid in prizesids:
        prizeidList.append(prizeid.strip())

    return prizeidList


# 快速排序
def quicksort(sep):
    if sep == []:
        return []
    middle = sep[0]
    lessthan = quicksort([x for x in sep[1:] if int(x.dice) < int(middle.dice)])
    greatthan = quicksort([x for x in sep[1:] if int(x.dice) >= int(middle.dice)])
    return lessthan + [middle] + greatthan


def quicksort02(sep):
    if sep == []:
        return []
    middle = sep[0]
    lessthan = quicksort02([x for x in sep[1:] if int(x.dice02) < int(middle.dice02)])
    greatthan = quicksort02([x for x in sep[1:] if int(x.dice02) >= int(middle.dice02)])
    return lessthan + [middle] + greatthan


# 收入记录
@app.route('/v1/activity/prize/order/<phone>/<token>', methods=['GET', 'POST'])
@check_ajax
def prize_order(phone, token):
    renderData = {'token': token}
    chakanjiangp = request.args.get('chakanjiangp', None)
    renderData['chakanjiangp'] = chakanjiangp
    renderData['phone'] = phone
    prize_image_top = db.session.query(Prize_order, Prize_image.image)
    prize_order_list = prize_image_top.filter(and_(Prize_order.prize_id == Prize_image.prize_id,
                                                   Prize_order.phone == phone, Prize_order.channel_num == 0)).order_by(Prize_order.time.desc()).all()

    renderData['prize_order_list'] = prize_order_list
    points = db.session.query(Points_change)
    points_list = points.filter(Points_change.phone == phone).order_by(Points_change.time.desc()).all()
    shouru_list = []
    for p in points_list:
        if p.type == 0 or p.type == 1:
            shouru_list.append(p)
    renderData['shouru_list'] = shouru_list
    return render_template('/activity/prize_order.html', renderData=renderData)


@app.route('/v1/activity/prize/order/zill/<phone>/<token>', methods=['GET', 'POST'])
@check_ajax
def prize_order_zill(phone, token):
    renderData = {'token': token, 'phone': phone}
    zill_list = db.session.query(Points_change).filter(Points_change.phone == phone, Points_change.num > 0).order_by(
        Points_change.time.desc()).all()
    renderData['zill_list'] = zill_list
    return render_template('/activity/dice_info.html', renderData=renderData)


@app.route('/v1/activity/store', methods=['GET', 'POST'])
@check_activity(activity_name='大富翁活动')
def store():
    images = []
    prizes = []
    phone = g.phone
    token = g.token
    renderData = {'phone':phone,'token':token}
    member = Member.query.filter_by(phone=phone).first()
    asset = Member_asset_info.query.filter_by(member_id=member.id).first()
    prize_image_ques = db.session.query(Prize_image).all()
    prize_ques = []
    # ---------------------------------
    # 根据活动的ids取出的商品
    ids = creatPrizesidsList()
    pri_list = PrizeType.query.filter(and_(PrizeType.id.in_(ids),~PrizeType.name.in_(('20元话费','50元话费','100元话费')))).order_by(PrizeType.score).all()
    xiangou = PrizeType.query.filter(and_(PrizeType.id.in_(ids),PrizeType.name.in_(('20元话费','50元话费','100元话费')),PrizeType.status == 1 )).order_by(PrizeType.score.asc()).all()
    for pri in pri_list:
        if pri.status == 1:
            prize_ques.append(pri)

    for pi in prize_image_ques:
        images.append((pi.prize_id, pi.image))

    for p in prize_ques:
        di = {'id': str(p.id).replace('-', ''), 'name': p.name, 'status': p.status, 'deadline': p.deadline,
              'input_time': p.input_time,
              'score': p.score, 'description': p.description, 'images': []}
        prizes.append(di)


    for prize_id, img in images:
        for p in prizes:
            if str(p['id']).replace('-', '') == str(prize_id):
                p['images'].append(img)
        for i in xiangou:
            if str(i.id).replace('-', '') == str(prize_id):
                # xiangou_images.append(img)
                i.images = img

    renderData['phone'] = phone
    renderData['score'] = asset.score
    renderData['prize_list'] = prizes
    renderData['xiangou_list'] = xiangou
    return render_template('/activity/store.html', renderData=renderData)


# 商品详情 /v1/activity/store/detail/18519291259/99f8afda72f347eaa69a3c3d5b62c370/2017-08-14-6380661978
@app.route('/v1/activity/store/detail/<phone>/<prize_id>/<token>')
@check_ajax
def detail(phone, prize_id, token):
    renderData = {'token': token, 'prize_id': prize_id}

    prize = PrizeType.query.filter_by(id=prize_id).first()
    pr_img = Prize_image.query.filter_by(prize_id=prize_id).first()
    renderData['introduce'] = prize.introduce
    renderData['exchange_process'] = prize.exchange_process
    renderData['score'] = prize.score
    renderData['prize_id'] = prize_id
    renderData['phone'] = phone
    if pr_img:
        renderData['image'] = pr_img.image
    if prize.name in ('20元话费','50元话费','100元话费'):
        renderData['is_xiangou'] = 'True'
        renderData['stock'] = prize.stock
    else:
        renderData['is_xiangou'] = 'False'
    return render_template('/activity/detail.html', renderData=renderData)


# 兑换ajax
@app.route('/v1/activity/store/exchange/<phone>/<prize_id>/<token>')
@check_ajax
def exchange(phone, prize_id, token):
    response_data = {
        'code': '10003',
        'desc': '积分商城暂停兑换',
        'content': ''
    }
    return toolkit.response(response_data, 200, None, True)
    response_data = {'token': token}
    member = Member.query.filter_by(phone=phone).first()
    asset = Member_asset_info.query.filter_by(member_id=member.id).first()
    memberInfo = Member.query.filter_by(phone=phone).first()

    if member.isblack == 'Sync':
        response_data["code"] = u"10002"
        response_data["content"]={}
        response_data["desc"] = u"您的账户已被迁移到菠萝理财存管版，请用菠萝理财存管版登录！"
        return toolkit.response(response_data, 200, None, True)

    p = PrizeType.query.filter_by(id=prize_id).first()
    activity = Activity.query.filter_by(name='大富翁活动').first()
    isgrant = 0
    isremain = 'True' # 限购有木有剩余
    if p.name in ('20元话费','50元话费','100元话费'):
        if p.stock <= 0:
            isremain = 'False'
            response_data['is_remain'] = isremain
            response_data['enabled'] = 'False'
            return toolkit.response(response_data, 200, None, True)
        else:
            if asset.score >= p.score:
                p.stock -= 1
                db.session.merge(p)
                db.session.commit()
    if asset.score >= p.score:
        asset.score -= p.score
        if p.ptype == '现金':
            xj_red_pocket(str(memberInfo.id).replace('-', ''), p.money)
            isgrant = 1
        elif p.ptype == '红包':
            lc_red_pocket(str(memberInfo.id).replace('-', ''), p.hongbao_id)
            isgrant = 1

        order = Prize_order(phone=phone, prize_id=prize_id, prize_name=p.name, score=p.score, \
                            money=p.money, status=isgrant, time=datetime.now(),
                            activity_id=str(activity.id).replace('-', ''), channel_num=0)

        db.session.add(order)
        db.session.merge(asset)
        db.session.merge(p)
        db.session.commit()
        response_data['is_remain'] = isremain
        response_data['enabled'] = 'True'

    else:
        response_data['enabled'] = 'False'
    response_data['score'] = p.score
    response_data['stock'] = p.stock
    return toolkit.response(response_data, 200, None, True)


# 未登录时红包注册页面
@app.route('/v1/activity/huodong/0')
def hongbao_for_zhuce():
    renderData = {}
    return render_template('/activity/hongbao_for_zhuce.html', renderData=renderData)


# 分享大富翁活动页面
@app.route('/v1/activity/share/friend/<phone>/<type>', methods=['GET', 'POST'])
@check_ajax
def share_for_friend(phone, type):
    if type == '1':
        if phone:
            m = Member.query.filter_by(phone=phone).first()
            activity = Activity.query.filter_by(name='大富翁活动').first()
            zill = Zillionaire_info.query.filter_by(phone=m.phone, activity_id=activity.id).first()
            if zill.has_friends == 0 and zill.investment >= 10000:
                zill.has_friends = 1
                zill.use_number += 1
                db.session.merge(zill)
                db.session.commit()
        return redirect(url_for('index', phone=phone))
    return None


@app.route('/v1/activity/bank/jiebang/rules')
def blank_jiebang_rules():
    renderData = {}
    return render_template('/activity/blank_jiebang_rules.html', renderData=renderData)


# 签到规则
@app.route('/v1/activity/sign_rule')
def sign_rule():
    renderData = {}
    return render_template('/activity/sign_rule.html', renderData=renderData)


# 活动中心列表
@app.route('/v1/activity/new/list')
@check_activity(activity_name='大富翁活动')
def activity_new_list():
    renderData = {}
    renderData['phone'] = g.phone
    renderData['token'] = g.token
    yiyuehuodong = Activity.query.filter_by(name='一月活动').first()
    if yiyuehuodong and g.phone:
        zill = Zillionaire_info.query.filter_by(phone=g.phone, activity_id=yiyuehuodong.id).first()
        if not zill:
            zill_info = Zillionaire_info(phone=g.phone, activity_id=yiyuehuodong.id)
            db.session.add(zill_info)
            db.session.commit()
    renderData['show'] = '0'
    if yiyuehuodong.start_time <= datetime.now():
        renderData['show'] = '1'
    return render_template('/activity/activity_new_list.html', renderData=renderData)


@app.route('/v1/activity/labour/invate', methods=['GET', 'POST'])
def labour_invate():
    response_data = {}
    response_data["code"] = u"10000"
    return toolkit.response(response_data, 200, None, True)



@app.route('/v1/activity/hegui/h5')
@check_activity(activity_name='大富翁活动')
def hegui_h5():
    response_data = {}
    return render_template('html5/hegui.html',response_data=response_data)


@app.before_request
def requests_began():
    g.time = datetime.now()


@app.after_request
def requests_end(p):
    url = request.url
    print '  URL====>  ' + url[21:] + ' || time====>' + str(datetime.now() - g.time)
    return p


@app.route('/v1/activity/qixi/h5')
@check_activity(activity_name='大富翁活动')
def qixi_h5():
    response_data = {}
    return render_template('html5/qixi.html',response_data=response_data)


@app.route('/v1/activity/mdkshj')
def mdkshj():
    response_data = {}
    return render_template('html5/mdkshj.html', response_data=response_data)


@app.route('/v1/activity/yure')
def yure():
    response_data = {}
    return render_template('html5/yure.html', response_data=response_data)


@app.route('/v1/activity/meeting')
def meeting():
    response_data = {}
    return render_template('assets/meeting.html', response_data=response_data)


@app.route('/v1/activity/winners_sj')
def winners_sj():
    return render_template('assets/winners_sj.html')


# @app.route('/v1/activity/xianjin/send')
# def xianjin_send():
#     response_data = {}
#     member = Member.query.filter_by(phone='18911358061').first()
#     member02 = Member.query.filter_by(phone='13503311617').first()
#     xj_red_pocket(str(member.id).replace('-',''),1316)
#     order = Order_dict.query.filter_by(is_use=False).first()
#     income = Member_income_statement(member_id=str(member.id).replace('-',''), type='到账红包',
#                                      money=1316, time=datetime.now(),
#                                      info='现金红包', order_id=order.order_id, \
#                                      phone='18911358061')
#     order.is_use = True
#     db.session.merge(order)
#     db.session.add(income)
#     db.session.commit()
#
#
#
#     xj_red_pocket(str(member02.id).replace('-', ''), 188)
#     order = Order_dict.query.filter_by(is_use=False).first()
#     income = Member_income_statement(member_id=str(member02.id).replace('-', ''), type='到账红包',
#                                      money=188, time=datetime.now(),
#                                      info='现金红包', order_id=order.order_id, \
#                                      phone='13503311617')
#     order.is_use = True
#     db.session.merge(order)
#     db.session.add(income)
#     db.session.commit()
#
#
#     response_data['code'] = '10000'
#     response_data['desc'] = '成功'
#     response_data['content'] = {}
#
#
#     return toolkit.response(response_data, 200, None, True)

@app.route('/v1/activity/schoolstarts')
@check_activity(activity_name='大富翁活动')
def the_school_starts():
    response_data = {}
    if g.isnotauth is not None:
        response_data['is_login'] = 'False'
        response_data['my_score'] = dict(sign_store=0,invate_store=0,invest_30=0,invest_total=0,
                invest_90=0,invest_180=0,total_score=0,leftstatus=[],rightstatus=[],layer=0)
    else:
        response_data['phone'] = g.phone
        response_data['token'] = g.token
        response_data['my_score'] = school_starts_information(g.phone)
        response_data['is_login'] = 'True'


    today = datetime.now()
    activity_start = '%s-%s-%s 00:00:00' % (today.year, today.month, 4)
    activity_middle = '%s-%s-%s 00:00:00' % (today.year, today.month, 9)
    activity_middle_second = '%s-%s-%s 00:00:00' % (today.year, today.month, 14)
    activity_end = '%s-%s-%s 00:00:00' % (today.year, today.month, 19)

    rank_list = []
    subq = db.session.query(Integral_record.member_id, func.sum(Integral_record.integral).label('total')).filter(
        Integral_record.time.between(activity_start, activity_end)).group_by(
        Integral_record.member_id).order_by(func.sum(Integral_record.integral).desc()).limit(88).subquery()

    result = db.session.query(Member.phone, subq.c.total).join(subq, Member.id == subq.c.member_id).all()
    for index,i in enumerate(result):
        rank_list.append((convertPhone(i.phone), i.total,str(index+1)))

    response_data['rank'] = rank_list
    return render_template('activity/sept-info.html',response_data=response_data)


# @app.route('/v1/activity/schoolstarts/ajax/<phone>/<prize_id>/<token>')
# @check_ajax
# def the_school_starts_ajax(phone,token,prize_id):
#     response_data = {}
#
#     kxj = Activity.query.filter_by(name='开学季活动').first()
#     if kxj and kxj.start_time < datetime.now() < kxj.end_time:
#         sendprize(phone, prize_id)
#         response_data['success'] = 'True'
#     else:
#         response_data['success'] = 'False'
#     return toolkit.response(response_data, 200, None, True)

@app.route('/v1/activity/nationalday')
@check_activity(activity_name='大富翁活动')
def nationalday():
    response_data = {}
    kxj = Activity.query.filter_by(name='国庆节活动').first()
    if g.isnotauth is not None:
        response_data['enabled'] = 'False'
        response_data['remain'] = 0
        response_data['member_store'] = 0

    else:
        phone = g.phone
        token = g.token
        response_data['phone'] = phone
        response_data['token'] = token

        m = Member.query.filter_by(phone=phone).first()
        activity = Activity.query.filter_by(name='大富翁活动').first()

        zill = Zillionaire_info.query.filter_by(phone=m.phone, activity_id=activity.id).first()
        response_data['remain'] = zill.national_store or 0
        if zill.national_store > 0:
            response_data['enabled'] = 'True'
        else:
            response_data['enabled'] = 'False'

        member_store = db.session.query(func.sum(Integral_record.integral))\
                        .filter(and_(Integral_record.member_id==str(m.id).replace('-',''),Integral_record.activity_id==str(kxj.id).replace('-',''))).scalar()

        response_data['member_store'] = member_store or 0

        personal_top = db.session.query(Prize, PrizeType)
        personal_list = personal_top.filter(and_(PrizeType.id == Prize.prize_id, Prize.phone == phone,
                                                 Prize.activity_id == str(kxj.id).replace('-', ''))).order_by(
            Prize.time.desc()).all()
        response_data['PersonalList'] = []
        for item in personal_list:
            response_data['PersonalList'].append((datetime.strftime(item[0].time, '%Y-%m-%d'), item[1].name))

    memberPrizeInfoList = []
    prizeType_top = db.session.query(PrizeType, Prize, Activity, PrizeType.name, Prize.phone)
    prizeTypes = prizeType_top.filter(
        and_(PrizeType.id == Prize.prize_id, Activity.id == Prize.activity_id, Activity.name == '国庆节活动'
             )).order_by(Prize.time.desc()).limit(40).all()
    for m in prizeTypes:
        memberPrizeInfoList.append((convertPhone(m.phone), m.name))
    virtualphone = random.choice(
        ['139', '188', '185', '136', '158', '151', '186', '137', '181', '182', '183', '138', '188']) + "".join(
        random.choice("0123456789") for i in range(8))

    xuni_index = random.randint(0,len(memberPrizeInfoList) - 1)
    memberPrizeInfoList.insert(xuni_index,(convertPhone(unicode(virtualphone)), u'188元现金红包'))
    response_data['memberPrizeInfoList'] = memberPrizeInfoList

    rank_list = []
    subq = db.session.query(Integral_record.member_id, func.sum(Integral_record.integral).label('total')).filter(Integral_record.activity_id == str(kxj.id).replace('-','')).group_by(Integral_record.member_id) \
        .order_by(func.sum(Integral_record.integral).desc()).limit(58).subquery()

    result = db.session.query(Member.phone, subq.c.total).join(subq, Member.id == subq.c.member_id).all()
    for index, i in enumerate(result):
        rank_list.append((convertPhone(i.phone), i.total, str(index + 1)))
    response_data['rank'] = rank_list
    return render_template('activity/october_info.html',renderData=response_data)


@app.route('/v1/activity/nationalday/ajax/<phone>/<token>')
@check_ajax
def nationalday_ajax(phone,token):
    response_data = {}

    kxj = Activity.query.filter_by(name='国庆节活动').first()
    dfw = Activity.query.filter_by(name='大富翁活动').first()
    m = Member.query.filter_by(phone=phone).first()

    if m.isblack == 'Sync':
        response_data["code"] = u"10002"
        response_data["content"]={}
        response_data["desc"] = u"您的账户已被迁移到菠萝理财存管版，请用菠萝理财存管版登录！"
        return toolkit.response(response_data, 200, None, True)

    number_to_money = {'6':188.88,'5':88.88,'4':18.88,'3':8.88,'2':1.88,'1':0.88}
    number_to_prizeid = {'1':'5e04cb8e0ddf42978bcf54ca7971123a','2':'5e04cb8e0ddf42978bcf54ca7971122x','3':'5e04cb8e0ddf42978bcf54ca797112cd','4':'5e04cb8e0ddf42978bcf54ca7971123b','5':'5e04cb8e0ddf42978bcf54ca797112a6','6':'5e04cb8e0ddf42978bcf54ca797112a7'}
    zill_info = Zillionaire_info.query.filter_by(phone=phone, activity_id=dfw.id).first()

    if kxj and kxj.start_time < datetime.now() < kxj.end_time:
        if zill_info.national_store > 0:
            zill_info.national_store -= 1
            db.session.merge(zill_info)
            db.session.commit()

            result = random_pick03()
            resultmoney = float(number_to_money[result])
            if result == '1':
                xj_red_pocket(str(m.id).replace('-',''),resultmoney)
            elif result == '2':
                xj_red_pocket(str(m.id).replace('-', ''), resultmoney)
            elif result == '3':
                xj_red_pocket(str(m.id).replace('-', ''), resultmoney)
            elif result == '4':
                xj_red_pocket(str(m.id).replace('-', ''), resultmoney)
            elif result == '5':
                xj_red_pocket(str(m.id).replace('-', ''), resultmoney)
            elif result == '6':
                xj_red_pocket(str(m.id).replace('-', ''), resultmoney)

            prize = Prize(prize_id=number_to_prizeid[result], phone=phone, time=datetime.now(), is_grant=1,
                          activity_id=str(kxj.id).replace('-',''))

            db.session.add(prize)
            db.session.commit()

            order = Order_dict.query.filter_by(is_use=False).first()
            income = Member_income_statement(member_id=str(m.id).replace('-',''), type='国庆节现金红包',
                                             money=resultmoney,time=datetime.now(),
                                             info='国庆节现金红包', order_id=order.order_id, \
                                             phone=phone)
            order.is_use = True
            db.session.merge(order)
            db.session.add(income)
            db.session.commit()
            response_data['success'] = 'True'
            response_data['result'] = result
    else:
        response_data['success'] = 'False'

    return toolkit.response(response_data, 200, None, True)


# 当天是否签到接口
@app.route('/v1/activity/today/<phone>/sign', methods=['GET', 'POST'])
def today_sign(phone):
    response_data = {}
    response_data["is_sign"] = 0
    today = date.today()
    sign = Sign_record.query.filter_by(phone=phone, check_time=today).first()
    if sign:
        response_data["is_sign"] = 1
    return toolkit.response(response_data, 200, None, True)


# 查询活动抽奖次数
@app.route('/v1/activity/lottery/<phone>/number', methods=['GET', 'POST'])
def lottery_number(phone):
    response_data = {}
    response_data["lottery_num_Available"] = 0
    response_data["invest_sum"] = 0

    now = datetime.now()
    activity = db.session.query(Activity).filter(and_(Activity.name == "双十二活动", Activity.start_time < now, Activity.end_time > now)).first()
    if activity:
        activity_today_begin = datetime.today().strftime("%Y-%m-%d 00:00:00")
        activity_today_end = datetime.today().strftime("%Y-%m-%d 23:59:59")
        m = Member.query.filter(or_(Member.phone == phone)).first()
        if m:
            invest_info_list = db.session.query(Invest_info.money, Invest_info.hongbao, Invest_info.product_id, Product_info.product_type, Product_info.time_limit).\
                filter(and_(Product_info.id == Invest_info.product_id,
                            Invest_info.member_id == str(m.id).replace('-', ''),
                            Product_info.product_type != '新手标',
                            Invest_info.is_effect == 1,
                            Invest_info.time.between(activity_today_begin, activity_today_end))).order_by(Invest_info.time.asc()).all()
            if invest_info_list:
                invest_sum = 0  # 投资累计总金额（今日所有投资总和）
                invest_money_sum = 0  # 投资累计金额（首次累计到5000的投资总和）
                lottery_num = 0  # 总抽奖次数
                is_add = False  # 是否已经累计到5000
                for inv in invest_info_list:
                    invest_sum += inv.money + inv.hongbao
                    if is_add:
                        if inv.money + inv.hongbao >= 5000:
                            multiple = int(inv.money + inv.hongbao) / 5000
                            if inv.time_limit == '30':
                                lottery_num += 1 * multiple
                            elif inv.time_limit == '90':
                                lottery_num += 2 * multiple
                            elif inv.time_limit == '180':
                                lottery_num += 3 * multiple
                    else:
                        invest_money_sum += inv.money + inv.hongbao
                        if invest_money_sum >= 5000:
                            lottery_num += 3
                            is_add = True
                lottery_num_used = db.session.query(Lottery_record).filter(and_(Lottery_record.phone == phone,
                                                                                Lottery_record.activity_id == str(activity.id).replace('-', ''),
                                                                                Lottery_record.lottery_time.between(activity_today_begin, activity_today_end))).all()  # 已使用抽奖次数
                lottery_num_Available = lottery_num - len(lottery_num_used)  # 可用抽奖次数
                response_data["lottery_num_Available"] = lottery_num_Available
                response_data["invest_sum"] = round(invest_sum, 2)
            response_data["code"] = u"10000"
            response_data["desc"] = u"查询成功"
        else:
            response_data["code"] = u"10001"
            response_data["desc"] = u"用户不存在"
    else:
        response_data["code"] = u"10002"
        response_data["desc"] = u"活动不存在"

    return toolkit.response(response_data, 200, None, True)


# 抽奖
@app.route('/v1/activity/lottery/action', methods=['GET', 'POST'])
def lottery_action():
    phone = request.args.get('phone')
    token = request.args.get('token')
    response_data = {}
    authenticate = False
    if not phone or not token:
        response_data["code"] = u"10001"
        response_data["desc"] = u"参数缺少"
        return toolkit.response(response_data, 200, None, True)
    else:
        t = Member_login.query.filter_by(member_name=phone, login_token=token).first()
        if t is None:
            pass
        elif t.over_time < datetime.now():
            pass
        else:
            authenticate = True

    if authenticate:
        activity = db.session.query(Activity).filter(Activity.name == "双十二活动").first()
        activity_id = activity.id
        big_awards_num = BIG_AWARDS_NUM  # 大奖666元中奖最高次数
        temp_num = 5
        response_data["lottery_num_Available"] = 0
        response_data["code"] = u"10001"
        response_data["desc"] = u"开始执行"

        lott_num = json.loads(lottery_number(phone).data)
        response_data["lottery_num_Available"] = lott_num['lottery_num_Available']
        if lott_num['lottery_num_Available'] > 0:
            while temp_num > 0:
                temp_num -= 1
                result = random_pick_04(activity_id)
                # result = "1"
                big_awards_num_got = Lottery_record.query.filter_by(money=666, type=1).all()
                if len(big_awards_num_got) >= big_awards_num:
                    if result == "3":  # 中奖为666现金红包
                        continue
                    else:
                        break
                else:
                    break
            prize = PrizeType.query.filter_by(activity_id=str(activity_id).replace('-', ''), act_dice=result).first()
            if prize:
                red_info = Member_red_pocket_type.query.filter_by(id=prize.hongbao_id).first()
                if red_info:
                    member = Member.query.filter_by(phone=phone).first()
                    now_time = datetime.now()
                    gen_time = '2017-12-18 23:59:59'
                    mr = Member_red_pocket(member_id=str(member.id).replace('-', ''),
                                           sort_id=str(red_info.id).replace('-', ''),
                                           generate_time=gen_time)
                    if red_info.type == "7":  # 现金红包
                        asset_info = Member_asset_info.query.filter_by(member_id=member.id).first()
                        asset_info.remainamount += red_info.money
                        lott = Lottery_record(phone=phone, activity_id=str(activity_id).replace('-', ''),
                                              lottery_result="成功抽到%d元现金红包" % red_info.money,
                                              money=red_info.money, type=1, lottery_time=now_time)
                        mri = Member_recharge_info(member_id=str(member.id).replace('-', ''), member_name=member.name,
                                                  time=now_time, is_effect=1,
                                                  money=red_info.money, type=5)
                        income = Member_income_statement(member_id=str(member.id).replace('-', ''), type='现金红包',
                                                         money=red_info.money,
                                                         balance=asset_info.rechargeamount + asset_info.remainamount,
                                                         time=datetime.now(),
                                                         info='双十二活动现金红包', phone=phone)
                        mr.is_use = 1
                        db.session.merge(asset_info)
                        db.session.add(mri)
                        db.session.add(income)
                        db.session.add(mr)
                        db.session.add(lott)
                        db.session.commit()
                        response_data["money"] = red_info.money
                        response_data["type"] = 1
                        response_data["type_desc"] = "现金红包"
                    elif red_info.type == "5":  # 理财红包
                        lott = Lottery_record(phone=phone, activity_id=str(activity_id).replace('-', ''),
                                              lottery_result="成功抽到%d元理财红包" % red_info.money,
                                              money=red_info.money, type=2, lottery_time=now_time)
                        db.session.add(mr)
                        db.session.add(lott)
                        db.session.commit()
                        response_data["money"] = red_info.money
                        response_data["type"] = 2
                        response_data["type_desc"] = "理财红包"
                response_data["code"] = u"10000"
                response_data["desc"] = u"抽奖成功"
        else:
            response_data["code"] = u"10003"
            response_data["desc"] = u"没有可用抽奖次数"
    else:
        response_data["code"] = u"10002"
        response_data["desc"] = u"token失效，请重新登录"
    return toolkit.response(response_data, 200, None, True)


# 双十二活动现金红包抽奖记录
@app.route('/v1/activity/lottery/record', methods=['GET', 'POST'])
def lottery_record():
    response_data = {}
    response_data["code"] = u"10001"
    response_data["desc"] = u"开始查询"
    response_data["content"] = []

    activity_today_begin = datetime.today().strftime("%Y-%m-%d 00:00:00")
    activity_today_end = datetime.today().strftime("%Y-%m-%d 23:59:59")
    lott_info_list = db.session.query(Lottery_record).filter(and_(Lottery_record.type == 1,
                                                                  Lottery_record.lottery_time.between(activity_today_begin, activity_today_end))).order_by(Lottery_record.lottery_time.asc()).limit(10)
    for lott in lott_info_list:
        temp = {}
        temp['phone'] = hide_some_fields(lott.phone, type='both', before=3, back=4)
        temp['lottery_time'] = lott.lottery_time.strftime("%Y-%m-%d")
        temp['money'] = "%s元" % lott.money
        response_data["content"].append(temp)
    response_data["code"] = u"10000"
    response_data["desc"] = u"查询成功"
    return toolkit.response(response_data, 200, None, True)


# 检查token是否有效
@app.route('/v1/activity/check/token', methods=['GET', 'POST'])
def check_token():
    phone = request.args.get('phone')
    token = request.args.get('token')
    response_data = {}
    if not phone or not token:
        response_data["code"] = u"10001"
        response_data["desc"] = u"参数缺少"
    else:
        t = Member_login.query.filter_by(member_name=phone, login_token=token).first()
        if t is None:
            response_data["code"] = u"10002"
            response_data["desc"] = u"token失效"
        elif t.over_time < datetime.now():
            response_data["code"] = u"10002"
            response_data["desc"] = u"token失效"
        else:
            response_data["code"] = u"10000"
            response_data["desc"] = u"token有效"
    return toolkit.response(response_data, 200, None, True)


# 一月活动排行榜
@app.route('/v1/activity/january_rank_list')
def januaryActivityRankList():
    content = {}
    rank_list = []                  # 排行榜
    january_activity = Activity.query.filter_by(name='一月活动').first()
    activity_member = Zillionaire_info.query.filter_by(activity_id=january_activity.id).order_by(
                                       Zillionaire_info.national_store.desc()).limit(88).all()  #所有参加活动用户（积分倒序）
    for member in activity_member:  # 拼接排行榜的每个用户及积分（倒序）
        try:
            if Member.query.filter_by(phone=member.phone, isblack='Sync').first():
               continue
        except:
            pass
        rank_list.append({'phone': member.phone, 'integral': round(member.national_store, 2)})
    content['rank_list'] = rank_list
    return toolkit.response(code_date_to_dict("10000",content), 200, None, True)


# 一月活动个人数据
@app.route('/v1/activity/january_member')
@check_phone_and_token_ajax()
def januaryActivityMember():
    content = {}
    phone = request.args.get('phone')
    prize_lantern = {'加息券': 1, '现金红包': 2, '小米音响': 3, '旅行箱': 4,
                     '扫地机器人': 5, 'iPad mini': 6, 'iPhone 8': 7, 'iPhone X': 8}
    january_activity = Activity.query.filter_by(name='一月活动').first()
    member_activity_invest = Zillionaire_info.query.filter_by(phone=phone, activity_id=january_activity.id).first()
    if member_activity_invest is None:
        integral = 0
    else:
        integral = round(member_activity_invest.national_store, 2)  # 用户积分
    if integral >= 880000:
        prize = 'iPhone X'
    elif integral >= 600000:
        prize = 'iPhone 8'
    elif integral >= 400000:
        prize = 'iPad mini'
    elif integral >= 200000:
        prize = '扫地机器人'
    elif integral >= 100000:
        prize = '旅行箱'
    elif integral >= 50000:
        prize = '小米音响'
    elif integral >= 10000:
        prize = '现金红包'
    else:
        prize = '加息券'
    latern = prize_lantern[prize]   # 奖品对应灯笼数
    content['integral'] = integral  # 用户积分
    content['prize'] = prize        # 用户奖品
    content['latern'] = latern      # 用户灯笼数
    return toolkit.response(code_date_to_dict("10000",content), 200, None, True)