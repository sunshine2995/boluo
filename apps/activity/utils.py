# -*- coding: UTF-8 -*-

from datetime import datetime, timedelta
from sqlalchemy import and_, func, or_
from sqlalchemy.sql.functions import coalesce
from apps.dbinstance import db
from apps.product.models import Invest_info, DoLine
from apps.asset.models import Member_asset_info, Member_red_pocket, \
                              Member_red_pocket_type, Member_recharge_info, Order_dict, Member_income_statement
from apps.member.models import Member
from apps.activity.models import Zillionaire_info, Prize_order, \
            Points_change, Prize_product, Prize_product_invest, Integral_record, Activity_status
from apps.rewards.models import Activity, Prize
from apps.product.models import Product_info


# 大富翁活动
def xj_red_pocket(member_id, total_fee, czren='大富翁活动'):
    m = Member.query.filter_by(id=member_id).first()
    doline = DoLine(member_id=member_id, member_name=m.name, money=total_fee, time=datetime.now(), inspector=czren)
    db.session.add(doline)
    db.session.commit()

    mr = Member_recharge_info(member_id=member_id, is_effect=1, money=total_fee, time=datetime.now(), type=3, bluuid=m.bluuid)
    db.session.add(mr)
    db.session.commit()

    asset = Member_asset_info.query.filter_by(member_id=member_id).first()
    asset.remainamount += total_fee
    db.session.merge(asset)
    db.session.commit()


def lc_red_pocket(member_id, red_type_id, generate_time=None):
    now_time = datetime.now()
    member_red = Member_red_pocket_type.query.filter_by(id=red_type_id).first()
    gen_time = datetime.strftime((now_time + timedelta(int(member_red.validtime))), '%Y-%m-%d %H:%M:%S')
    if generate_time:
        gen_time = generate_time
    ydmr = Member_red_pocket(member_id=member_id, sort_id=member_red.id, generate_time=gen_time, SEND_TIME=now_time)
    db.session.add(ydmr)
    db.session.commit()


# 赠送活动红包
def zengsong_hb(member_id):
    activity = Activity.query.filter_by(name='一月活动').first()  # 获取活动
    activity_start_time = activity.start_time  # 活动开始时间
    activity_end_time = activity.end_time    # 活动结束时间
    now = datetime.now()
    today_start = '%s-%s-%s 00:00:00' % (now.year, now.month, now.day)                 # 今天开始时间
    today_end = '%s-%s-%s 23:59:59' % (now.year, now.month, now.day)                   # 今天结束时间
    generate_time = datetime.strptime(today_end, '%Y-%m-%d %H:%M:%S')
    member = Member.query.filter_by(id=member_id).first()
    if activity and activity_start_time <= now <= activity_end_time  and member.isblack != 'Sync':  # 存在活动、现在在活动时间内且用户未迁移
        hb01 = Member_red_pocket_type.query.filter_by(name='双旦活动0.8%加息劵').first()
        hb02 = Member_red_pocket_type.query.filter_by(name='双旦活动1%加息劵').first()
        if hb01:  #有此类型红包
            mrp01 = db.session.query(Member_red_pocket).filter(and_(Member_red_pocket.sort_id == hb01.id,
                Member_red_pocket.member_id == member.id, Member_red_pocket.SEND_TIME.between(today_start, today_end))).first()
            if not mrp01:  # 用户今天没有收到过该红包，给用户发一个
                lc_red_pocket(member_id, hb01.id, generate_time=generate_time)
        if hb02:  #有此类型红包
            mrp02 = db.session.query(Member_red_pocket).filter(and_(Member_red_pocket.sort_id == hb02.id,
                Member_red_pocket.member_id == member.id, Member_red_pocket.SEND_TIME.between(today_start, today_end))).first()
            if not mrp02:  # 用户今天没有收到过该红包，给用户发一个
                lc_red_pocket(member_id, hb02.id, generate_time=generate_time)


# 增加x次摇骰子机会
def increaseTheDice(phone, num):
    bldfw = Activity.query.filter_by(name='大富翁活动').first()
    zill = Zillionaire_info.query.filter_by(phone=phone, activity_id=bldfw.id).first()
    if zill:
        zill.use_number += num
        db.session.merge(zill)
        db.session.commit()


# 手机号隐藏
def convertPhone(phone):
    return phone[:2] + '****' + phone[7:11]


# 当前用户在该活动范围内的投资金额
def caculator_userinvest(phone):
    activity = Activity.query.filter_by(name='大富翁活动').first()
    investmoney = db.session.query(func.sum(Invest_info.money)) \
        .filter(and_(Member.phone == phone,Invest_info.member_id == Member.id,
                     Invest_info.time >= activity.start_time,Invest_info.time <= activity.end_time)).scalar()
    return round(float(investmoney), 6)




# 接收一个层数,返回对应的红包id
def layer_to_redpocket(layer,UUID=False):
    pocket = Member_red_pocket_type.query.filter_by(type=8).order_by(Member_red_pocket_type.money).all()
    key = ['1','2','3','4','5','6','7','8','9']
    t = zip(key,pocket)
    result = {}
    for k,v in t:
        if UUID == True:
            result[k] = v.id
        else:
            result[k] = str(v.id).replace('-', '')
    return result[layer]


# 创建商品标
def create_product():
    prizes_array = []
    percentage_array = []
    prizes = Prize_product.query.filter(Prize_product.type == 0).order_by(Prize_product.location.asc()).all()
    for i in prizes:
        prizes_array.append(i)
        percentage = (1 - round(float(i.remain) / float(i.total),2)) * 100
        percentage_array.append(percentage)
    return zip(prizes_array,percentage_array)


# 我的奖号
def create_myprizenumber(phone):
    onlinenumber =  db.session.query(Prize_product_invest,Prize_product)\
                    .filter(and_(Prize_product.type == 0,Prize_product_invest.phone == phone,Prize_product_invest.prize == Prize_product.issue))\
                    .order_by(Prize_product_invest.create_time.desc()).order_by(Prize_product_invest.number.asc()).all()
    offlinenumber = db.session.query(Prize_product_invest,Prize_product)\
                    .filter(and_(Prize_product.type == 1,Prize_product_invest.phone == phone,Prize_product_invest.prize == Prize_product.issue)) \
                    .order_by(Prize_product_invest.is_lucky.desc()).order_by(Prize_product_invest.create_time.desc()).order_by(Prize_product_invest.number.asc()).all()
    result_array = []
    for i in onlinenumber:
        prizenumber = i[1].issue + '0%02d' % i[0].number
        name = i[1].name
        islucky = '2'
        result_array.append((prizenumber,name,islucky))
    for i in offlinenumber:
        prizenumber = i[1].issue + '0%02d' % i[0].number
        name = i[1].name
        islucky = str(i[0].is_lucky)
        result_array.append((prizenumber,name,islucky))
    return result_array


def productToSingle(productstr):
    product = Prize_product.query.filter_by(issue=productstr).first()
    single = product.total / 20
    return single


today = datetime.now()
t_start = datetime(today.year, today.month, today.day)
t_end = t_start + timedelta(days=1)


#合规再升级
def do_send_hegui(member_id):
    def theDayOfInvest(member_id):
        # mem_id = str(Member.query.filter_by(phone=phone).first().id).replace('-','')
        inv_of_day = db.session.query(func.sum(Invest_info.money),Product_info.product_type) \
            .filter(and_(Invest_info.member_id == member_id,
                         Invest_info.time.between(t_start, t_end),Product_info.id == Invest_info.product_id,Product_info.product_type != '新手标')).scalar()
        return inv_of_day

    def _isnot_send(member_id,red_pocket_id):
        info = db.session.query(Member_red_pocket).filter(and_(Member_red_pocket.member_id==member_id,Member_red_pocket.sort_id==red_pocket_id)).first()
        return False if info else True

    invest = theDayOfInvest(member_id)
    if 10000 <= invest < 20000:
        if _isnot_send(member_id,'8a9bbef95ced95a4015cf6cc681b11fa'):
            lc_red_pocket(member_id,'8a9bbef95ced95a4015cf6cc681b11fa')
    elif 20000 <= invest < 50000:
        if _isnot_send(member_id,'8a9bbef95ced95a4015cf6cf773b11fc'):
            lc_red_pocket(member_id,'8a9bbef95ced95a4015cf6cf773b11fc')
    elif invest >= 50000:
        if _isnot_send(member_id,'8a9bbef95ced95a4015cf6cf783b11fc'):
            lc_red_pocket(member_id,'8a9bbef95ced95a4015cf6cf783b11fc')
    else:
        pass


def creat_dayofmoney_group():
    x = db.session.query(Invest_info.member_id,(func.sum(Invest_info.money) + func.sum(Invest_info.hongbao)).label('sum'),Product_info.product_type)\
        .filter(and_(Invest_info.time.between(t_start,t_end),Product_info.borrow_id == Invest_info.product_id,Product_info.product_type!='新手标'))\
        .group_by(Invest_info.member_id).subquery()
    # x1 = db.session.query(Invest_info.money)
    result =  db.session.query(x.c.member_id).filter(coalesce(x.c.sum, 0) >= 10000).all()
    return result


def phone_to_member_id(phone):
    member = Member.query.filter(or_(Member.phone==phone,Member.name==phone)).first()
    return str(member.id).replace('-','')


def add_integral_record(events,member_id,integral,activity_id):
    if events == '邀请':
        invate_count = Integral_record.query.filter(and_(Integral_record.member_id==member_id,Integral_record.events=='邀请')).count()
        if invate_count >=5:
            pass
        else:
            inte = Integral_record(member_id=member_id, events=events, time=datetime.now(), integral=integral,activity_id=activity_id)
            db.session.add(inte)
            db.session.commit()
    else:
        inte = Integral_record(member_id=member_id, events=events, time=datetime.now(), integral=integral,activity_id=activity_id)
        db.session.add(inte)
        db.session.commit()


def update_activity_status(member_id,money,product_limit):
    product_limito_events = {'30': 'invest30', '90': 'invest90', '180': 'invest180'}
    product_limito_integral = {'30': 1, '90': 1, '180': 1}
    product_limito_invest = {'30': 3000, '90': 1500, '180': 1000}
    the_events = product_limito_events[product_limit]
    single = product_limito_invest[product_limit]

    activity = Activity.query.filter_by(name='国庆节活动').first()

    def _add_status(member_id,money,product_limit):
        if money >= single:
            integral = int(money) / single * product_limito_integral[product_limit]
            remain_money = money % (int(money) / single * single)
            add_integral_record(events=the_events,member_id=member_id,integral=integral,activity_id=str(activity.id).replace('-',''))
        else:
            integral = 0
            remain_money = money
        activity_status = Activity_status(member_id=member_id, events=the_events,
                                          score=integral, remain=remain_money,activity_id=str(activity.id).replace('-',''))
        db.session.add(activity_status)
        db.session.commit()
    def _update_status(record,money):

        total_money = record.remain + money
        if total_money >= single:
            integral = int(total_money) / single * product_limito_integral[product_limit]
            remain_money = total_money % (int(total_money) / single * single)
            add_integral_record(events=the_events, member_id=member_id, integral=integral,activity_id=str(activity.id).replace('-',''))
            record.remain = remain_money
            record.score += integral
            db.session.merge(record)
            db.session.commit()

        else:
            record.remain += money
            db.session.merge(record)
            db.session.commit()

    old_status = Activity_status.query.filter(and_(Activity_status.member_id==member_id,
                                              Activity_status.events==the_events,Activity_status.activity_id==str(activity.id).replace('-',''))).first()
    if not old_status:
        _add_status(member_id,money,product_limit)
    else:
        _update_status(old_status,money)


def already_receive(phone):
    # 接收一个红包id,返回对应的层数
    kxj_activityid = str(Activity.query.filter_by(name='开学季活动').first().id).replace('-', '')
    prize_order = Prize.query.filter_by(phone=str(phone), activity_id=kxj_activityid).all()

    prizes_layer = []
    prizes = []
    for i in prize_order:
        p = str(i.prize_id)
        prizes_layer.append(prize_to_layer(p))
        prizes.append(p)
    return prizes_layer,prizes



def prize_to_layer(prize_id):
    t = [('1','c44cb9e28b9741c380f614b4b43cfee8'), ('2','d704fbc348cf4a75bbcae96bc8c4894d'),
         ('3','b86cf39ec4684d11aac7560a81223495'), ('4','daeee4a12cb4497290a1da976aa636a4'),
         ('5','b63ba4542dd241c98bdc6f10da1e3d93'), ('6','a39095a0f1a74d9db50cfc184b3ebcf5'),
         ('7','d9f8f8eae1a64d58af6c09d8413becb8'), ('8','472a74ebcdd54a71a260299c291387a7')]
    result = {}
    for k, v in t:
        result[v] = int(k)
    return result[prize_id]


def sendprize(phone,prize_id):
    kxj_activityid = str(Activity.query.filter_by(name='开学季活动').first().id).replace('-', '')

    member_id = phone_to_member_id(phone)
    sign_store = Integral_record.query \
        .filter(and_(Integral_record.member_id == member_id, Integral_record.events == '签到')).count()
    invate_store = Integral_record.query \
                       .filter(and_(Integral_record.member_id == member_id, Integral_record.events == '邀请')).count() * 2
    invest30 = Activity_status.query.filter(
        and_(Activity_status.member_id == member_id, Activity_status.events == 'invest30')).first()
    invest_30 = invest30.score if invest30 else 0
    invest180 = Activity_status.query.filter(
        and_(Activity_status.member_id == member_id, Activity_status.events == 'invest180')).first()
    invest_180 = invest180.score if invest180 else 0
    invest90 = Activity_status.query.filter(
        and_(Activity_status.member_id == member_id, Activity_status.events == 'invest90')).first()
    invest_90 = invest90.score if invest90 else 0
    invest_total = invest_30 + invest_90 + invest_180
    total_score = sign_store + invate_store + invest_30 + invest_90 + invest_180


    already = already_receive(phone)[1]
    member_id = phone_to_member_id(phone)

    if prize_id in already:
        return False
    else:
        if prize_to_layer(prize_id) <= caculator_layernum(total_score):
            if prize_id != 'b63ba4542dd241c98bdc6f10da1e3d93':
                hongbao = db.session.query(Member_red_pocket_type.id).filter(
                    and_(PrizeType.id == prize_id, PrizeType.hongbao_id == Member_red_pocket_type.id)).first()
                lc_red_pocket(member_id, str(hongbao.id).replace('-', ''))
            else:
                xj_red_pocket(member_id, 18,czren='开学季活动')
                order = Order_dict.query.filter_by(is_use=False).first()
                order.is_use = True
                income = Member_income_statement(member_id=member_id, type='到账红包',
                                                 money=18, time=datetime.now(),
                                                 info='开学季现金红包', order_id=order.order_id, \
                                                 phone=phone)
                db.session.merge(order)
                db.session.add(income)
                db.session.commit()
            prize_order = Prize(prize_id=prize_id, phone=phone, time=datetime.now(), is_grant=0,
                      activity_id=kxj_activityid)
            db.session.add(prize_order)
            db.session.commit()
            return True
        else:
            return False



# 第几层
def caculator_layernum(store):
    array = [30, 60, 80, 100, 150, 230, 300, 400, 450]
    for x, y in enumerate(array):
        if store < y:
            return x
    return 9

def school_starts_information(phone):

    member_id = phone_to_member_id(phone)
    sign_store = Integral_record.query\
            .filter(and_(Integral_record.member_id==member_id,Integral_record.events=='签到')).count()
    invate_store = Integral_record.query\
            .filter(and_(Integral_record.member_id==member_id,Integral_record.events=='邀请')).count() * 2
    invest30 = Activity_status.query.filter(and_(Activity_status.member_id==member_id,Activity_status.events=='invest30')).first()
    invest_30 = invest30.score if invest30 else 0
    invest180 = Activity_status.query.filter(
        and_(Activity_status.member_id == member_id, Activity_status.events == 'invest180')).first()
    invest_180 = invest180.score if invest180 else 0
    invest90 = Activity_status.query.filter(
        and_(Activity_status.member_id == member_id, Activity_status.events == 'invest90')).first()
    invest_90 = invest90.score if invest90 else 0
    invest_total = invest_30 + invest_90 + invest_180
    total_score = sign_store + invate_store + invest_30 + invest_90 + invest_180


    def creat_dict(phone):
        status = {'1':('c44cb9e28b9741c380f614b4b43cfee8',),'2':('d704fbc348cf4a75bbcae96bc8c4894d',),'3':('b86cf39ec4684d11aac7560a81223495',),'4':('daeee4a12cb4497290a1da976aa636a4',),
                  '5':('b63ba4542dd241c98bdc6f10da1e3d93',),'6':('a39095a0f1a74d9db50cfc184b3ebcf5',),'7':('d9f8f8eae1a64d58af6c09d8413becb8',),'8':('472a74ebcdd54a71a260299c291387a7',)}

        array = already_receive(phone)[0]
        tian = caculator_layernum(total_score)
        for key in status:
            if int(key) > int(tian):
                status[key] += ('2',)
            else:
                if int(key) in array:
                    status[key] += ('1',)
                else:
                    status[key] += ('0',)
        rlist = []
        for i in range(1, 9):
            rlist.append(('hongb' + str(i), status[str(i)]))

        return (rlist[:4],rlist[4:])

    return dict(sign_store=sign_store,invate_store=invate_store,invest_30=invest_30,invest_total=invest_total,
                invest_90=invest_90,invest_180=invest_180,total_score=total_score,leftstatus=creat_dict(phone)[0],rightstatus=creat_dict(phone)[1],layer=caculator_layernum(total_score))


# 获取用户在该活动的积分
def get_invest_intergral(phone, activity_name, is_new_product):
    member = Member.query.filter_by(phone=phone).first()                # 用户
    member_id = str(member.id).replace('-', '')                         # 用户ID
    activity = Activity.query.filter_by(name=activity_name).first()     # 活动
    start_time = activity.start_time                                    # 活动开始时间
    end_time = activity.end_time                                        # 活动结束时间
    member_invest_info = db.session.query(Invest_info).filter(and_(Invest_info.member_id == member_id,
        Invest_info.is_effect == 1, Invest_info.time.between(start_time, end_time))).all()  #用户在活动期间所有投资记录
    integral = 0
    for invest_info in member_invest_info:
        if not is_new_product:
            product_info = Product_info.query.filter_by(id=invest_info.product_id).first()
            integral += float(invest_info.money + invest_info.hongbao) * float(product_info.time_limit) / 180
    return round(integral, 2)


# 下单成功执行的活动
def huodong(is_new_product, total_fee_all, phone, time_limit):
    # 大富翁活动期间送骰子次数
    bldfw = Activity.query.filter_by(name='大富翁活动').first()
    member = Member.query.filter_by(phone=phone).first()
    asset = Member_asset_info.query.filter(Member_asset_info.member_id == str(member.id).replace('-','')).first()
    hscore = int(total_fee_all / 10)


    if bldfw and bldfw.start_time < datetime.now() < bldfw.end_time and not is_new_product:
        change = Points_change(phone=phone, time=datetime.now(), score=hscore, type=0, description='投资', num=int(total_fee_all / 5000))
        db.session.add(change)
        bldfw_zill = Zillionaire_info.query.filter_by(phone=phone, activity_id=bldfw.id).first()
        if bldfw_zill is None:       #用户未参加大富翁活动，增加用户的信息
            bldfw_zill = Zillionaire_info(phone=phone, activity_id=bldfw.id)
            db.session.add(bldfw_zill)
            db.session.commit()
        bldfw_zill.investment += total_fee_all
        if total_fee_all >= 5000:    # 投资总额每满5000 增加一次骰子
            bldfw_zill.use_number += int(total_fee_all / 5000)
        db.session.merge(bldfw_zill)
        asset.score += hscore
        db.session.merge(asset)

    # 一月活动
    january_hd = Activity.query.filter_by(name='一月活动').first()
    if january_hd and january_hd.start_time < datetime.now() < january_hd.end_time and not is_new_product:
        january_member = Zillionaire_info.query.filter_by(phone=phone, activity_id=january_hd.id).first() #查找用户是否在活动记录表
        integral = float(total_fee_all) * float(time_limit) / 180
        if january_member is None:  # 用户在活动期间首次投资
            january_member = Zillionaire_info(phone=phone, activity_id=january_hd.id, national_store=integral)
            db.session.add(january_member)
            db.session.commit()
        else:                       # 用户在活动期间续投
            january_member.national_store += integral
            db.session.merge(january_member)
    db.session.commit()


# 赠送活动红包(夸日有效)
def send_hb(member_id, activity_name, hb_name):
    activity = Activity.query.filter_by(name=activity_name).first()  # 获取活动
    activity_start_time = activity.start_time  # 活动开始时间
    activity_end_time = activity.end_time    # 活动结束时间
    now = datetime.now()
    member = Member.query.filter_by(id=member_id).first()
    if activity and activity_start_time <= now <= activity_end_time:  # 存在活动、现在在活动时间内
        hb = Member_red_pocket_type.query.filter_by(name=hb_name).first()
        if hb:    # 有此类型红包
            if int(now.strftime('%H')) >= 12:
                today_start = '%s-%s-%s 12:00:00' % (now.year, now.month, now.day)  # 今天开始时间
                today_end = '%s-%s-%s 12:00:00' % (now.year, now.month, now.day+1)    # 今天结束时间
            else:
                today_start = '%s-%s-%s 12:00:00' % (now.year, now.month, now.day-1)  # 今天开始时间
                today_end = '%s-%s-%s 12:00:00' % (now.year, now.month, now.day)    # 今天结束时间

            generate_time = datetime.strptime(today_end, '%Y-%m-%d %H:%M:%S')   # 红包过期时间
            mrp = db.session.query(Member_red_pocket).filter(and_(Member_red_pocket.sort_id == hb.id,
                Member_red_pocket.member_id == member.id, Member_red_pocket.SEND_TIME.between(today_start, today_end))).first()
            if not mrp:  # 用户今天没有收到过该红包，给用户发一个
                lc_red_pocket(member_id, hb.id, generate_time=generate_time)


# 赠送活动红包当天有效
def send_hb_today(member_id, activity_name, hb_name):
    activity = Activity.query.filter_by(name=activity_name).first()  # 获取活动
    activity_start_time = activity.start_time  # 活动开始时间
    activity_end_time = activity.end_time      # 活动结束时间
    now = datetime.now()
    today_start = '%s-%s-%s 00:00:00' % (now.year, now.month, now.day)  # 今天开始时间
    today_end = '%s-%s-%s 23:59:59' % (now.year, now.month, now.day)    # 今天结束时间
    member = Member.query.filter_by(id=member_id).first()
    if activity and activity_start_time <= now <= activity_end_time:    # 存在活动、现在在活动时间内
        hb = Member_red_pocket_type.query.filter_by(name=hb_name).first()
        if hb:  #有此类型红包
            mrp = db.session.query(Member_red_pocket).filter(and_(Member_red_pocket.sort_id == hb.id,
                Member_red_pocket.member_id == member.id, Member_red_pocket.SEND_TIME.between(today_start, today_end))).first()
            if not mrp:  # 用户今天没有收到过该红包，给用户发一个
                lc_red_pocket(member_id, hb.id)