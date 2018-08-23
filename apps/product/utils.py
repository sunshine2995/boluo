#!/use/bin/env python
# -*- coding: UTF-8 -*-

from sqlalchemy import and_, or_
from apps.product.models import Product_info, Invest_info
from apps.member.models import Member
from apps.dbinstance import db


def is_new_member(name_or_phone):
    m = Member.query.filter(or_(Member.name == name_or_phone, Member.phone == name_or_phone)).first()
    super_phone_list = ['13811629823', '18611897708','18519291259', '13810354654', '13237711492', '13303479527']
    if name_or_phone not in super_phone_list:
        inv_tops = db.session.query(Invest_info, Product_info.product_type)
        new_member = inv_tops.filter(and_(Invest_info.member_id == str(m.id).replace("-", ""),
                        Product_info.product_type == '新手标', Invest_info.product_id==Product_info.id)).first()
        new_member02 = inv_tops.filter(and_(Invest_info.member_id == str(m.id).replace("-", ""),
                                            Invest_info.NEWHAND_ID == '531d3ab7516bd37f01516bdcda180009')).first()
        if new_member or new_member02:
            is_new_member = 'false'
        else:
            is_new_member = 'true'
    else:
        is_new_member = 'true'
    return is_new_member

def cncurrency(value, capital=True, prefix=False, classical=None):
    '''
    人民币数字转汉字表示
    作者: qianjin(AT)ustc.edu
    版权声明:
        只要保留本代码最初作者的电子邮件即可，随便用。用得爽的话，不反对请
    作者吃一顿。

    参数:
    capital:    True   大写汉字金额
                False  一般汉字金额
    classical:  True   圆
                False  元
    prefix:     True   以'人民币'开头
                False, 无开头
    '''

    # 默认大写金额用圆，一般汉字金额用元
    if classical is None:
        classical = True if capital else False

    # 汉字金额前缀
    if prefix is True:
        prefix = '人民币'
    else:
        prefix = ''

    # 汉字金额字符定义
    dunit = ('角', '分')
    if capital:
        num = ('零', '壹', '贰', '叁', '肆', '伍', '陆', '柒', '捌', '玖')
        iunit = [None, '拾', '佰', '仟', '万', '拾', '佰', '仟', '亿',
                       '拾', '佰', '仟', '万', '拾', '佰', '仟']
    else:
        num = ('〇', '一', '二', '三', '四', '五', '六', '七', '八', '九')
        iunit = [None, '十', '百', '千', '万', '十', '百', '千', '亿',
                       '十', '百', '千', '万', '十', '百', '千']

    if classical:
        iunit[0] = '圆' if classical else '元'

    # 截断并转换为字符串
    s = '%0.2f' % value
    sf = float(s)
    if s.startswith('-') and sf != 0:   # 处理负数，并避免出现“负零圆”
        prefix += '负'                  # 输出前缀加“负”
        s = s[1:]                       # 去掉负号，无须过多考虑正负数的舍入问题
                                        # 无论怎么舍入 -a + a == 0
    istr, dstr = s.split('.')           # 小数部分和整数部分分别处理
    istr = istr[::-1]                   # 翻转整数部分字符串

    so = []     # 用于记录转换结果

    # 零
    if sf == 0:
        return prefix + num[0] + iunit[0]

    haszero = False     # 用于标记零的使用
    if dstr == '00':
        haszero = True  # 如果无小数部分，则标记加过零，避免出现“圆零整”

    # 处理小数部分
    # 分
    if dstr[1] != '0':
        so.append(dunit[1])
        so.append(num[int(dstr[1])])
    else:
        so.append('整')         # 无分，则加“整”
    # 角
    if dstr[0] != '0':
        so.append(dunit[0])
        so.append(num[int(dstr[0])])
    elif dstr[1] != '0':
        so.append(num[0])       # 无角有分，添加“零”
        haszero = True          # 标记加过零了

    # 无整数部分
    if istr == '0':
        if haszero:             # 既然无整数部分，那么去掉角位置上的零
            so.pop()
        so.append(prefix)       # 加前缀
        so.reverse()            # 翻转
        return ''.join(so)

    # 处理整数部分
    for i, n in enumerate(istr):
        n = int(n)
        if i % 4 == 0:          # 在圆、万、亿等位上，即使是零，也必须有单位
            so.append(iunit[i])
            if n == 0:                          # 处理这些位上为零的情况
                if not haszero:                 # 如果以前没有加过零
                    so.insert(-1, num[0])       # 则在单位后面加零
                    haszero = True              # 标记加过零了
            else:                               # 处理不为零的情况
                so.append(num[n])
                haszero = False                 # 重新开始标记加零的情况
        else:                                   # 在其他位置上
            if n != 0:                          # 不为零的情况
                so.append(iunit[i])
                so.append(num[n])
                haszero = False                 # 重现开始标记加零的情况
            else:                               # 处理为零的情况
                if not haszero:                 # 如过以前没有加过零
                    so.append(num[0])
                    haszero = True

    # 最终结果
    so.append(prefix)
    so.reverse()
    return ''.join(so)

def check_idcard(str):
    if len(str) == 18:
        return str[0:4] + '**********' + str[-4:]
    else:
        return str


def check_rate(member,rate):
    if member.level != 0:
        rate += 1.0
    return rate


