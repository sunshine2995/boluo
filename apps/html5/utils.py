# -*- coding: UTF-8 -*-

from datetime import datetime
from apps.member.models import Member
from apps.product.models import Invest_info
from apps.dbinstance import db
from apps.activity.utils import convertPhone
from apps.asset.models import Member_asset_info
from apps.activity.views import Points_change
from apps.rewards.models import Activity


#快速排序
def quicksort(sep):
    if sep == []:
        return  []
    middle = sep[0]
    lessthan = quicksort([x for x in sep[1:] if int(x[0]) < int(middle[0])])
    greatthan = quicksort([x for x in sep[1:] if int(x[0]) >= int(middle[0])])
    return  greatthan + [middle] + lessthan


def htsort(dic):
    if dic == []:
        return  []
    middle = dic[0]
    lessthan = htsort([x for x in dic[1:] if int(x['name'][-1]) < int(middle['name'][-1])])
    greatthan = htsort([x for x in dic[1:] if int(x['name'][-1]) >= int(middle['name'][-1])])
    return  lessthan + [middle] + greatthan


def creat_rank_list(month_ago=0):

    ttt = datetime.now()
    # ttt = Activity.query.filter_by(id='d0593465c3cd4a4b86ac7a68a782bb39').first().start_time
    year01 = ttt.year
    year02 = ttt.year
    month01 = ttt.month - month_ago
    month02 = ttt.month + 1 - month_ago
    if month02 == 13:
        year02 = ttt.year + 1
        month02 = 1
    elif month01 == 0:
        year01 = ttt.year - 1
        month01 = 12

    t01 = '%s-%s-%s 00:00:00' % (year01, month01, 1)  # 当月
    t02 = '%s-%s-%s 00:00:00' % (year02, month02, 1)  # 下月

    members_ques = db.session.query(Member.phone, Invest_info.money)
    members = members_ques.filter(Invest_info.time.between(t01, t02)).filter(
        Member.id == Invest_info.member_id).all()
    array = []
    array_dict = {}
    not_convert_array = []
    for m in list(members):
        phone = m.phone
        if not array_dict.has_key(phone):
            array_dict[phone] = 0
        array_dict[phone] += m.money
    for i, y in array_dict.items():
        array.append((y, convertPhone(i)))
        not_convert_array.append((y, i))

    array = quicksort(array)
    not_convert_array = quicksort(not_convert_array)[:10]
    return (array,not_convert_array)


def find_userasserts(phone):
    member = Member.query.filter_by(phone=phone).first()
    asserts = Member_asset_info.query.filter_by(member_id=str(member.id).replace('-','')).first()
    return asserts


def create_format(month_ago=0):
    today = datetime.now()
    # today = Activity.query.filter_by(id='d0593465c3cd4a4b86ac7a68a782bb39').first().start_time
    theformat = '{}-{}'.format(today.year if today.month >= 1 + month_ago else today.year - ((month_ago - today.month) / 12) - 1,
                today.month - month_ago if today.month >= 1 + month_ago else 12-(month_ago - today.month) % 12)
    return theformat


#根据排名发放菠萝奖励
def send_pinapple(value):
    if not isinstance(value,list):
        return
    pineapple_increase_tuple = map(lambda x:float(x)/100,tuple(range(15,15-len(value),-1)))
    total = zip(value,pineapple_increase_tuple)
    for i in total:
        try:
            pinapple = i[0].money / 10
            pinapple_increase = pinapple * i[1]
            asserts = find_userasserts(i[0].phone)
            asserts.score += pinapple_increase
            accord = Points_change(phone=i[0].phone, time=datetime.now(), score=pinapple_increase,
                                       description='每月排名奖励', type=1)
            db.session.merge(asserts)
            db.session.add(accord)
        except:
            pass
    db.session.commit()


# 使用*号隐藏一个字符串中的部分字段
def hide_some_fields(str, type='', before=0, back=0):
    if str is None:
        str = ''
    if type == 'before':
        if len(str) > before:
            return str[0:before] + '*' * (len(str) - before)
        else:
            return str
    if type == 'back':
        if len(str) > back:
            return '*' * (len(str) - back) + str[(0-back):]
        else:
            return str
    if type == 'both':
        if len(str) > (before + back):
            return str[0:before] + '*' * (len(str) - before - back) + str[(0-back):]
        else:
            return str
    else:
        return str