#!/use/bin/env python
# -*- coding: UTF-8 -*-

import urllib
import requests
from os import getcwd
from datetime import datetime, timedelta
from operator import itemgetter
from random import randint
import calendar
import time
from math import floor

from flask import render_template
from flask import request, g
from flask_httpauth import HTTPBasicAuth
from sqlalchemy import and_, or_, func

from apps import app
from config import BOLUO_URL, AUTO_PRODUCT_URL
from apps.member.models import Member, Member_real_info, Member_login, Member_pay_info, Member_bank_logo, Member_invite_info
from apps.product.models import Product_info, Invest_info, Borrower_info, Product_image, \
                                Contract, Product_new, Feature_info, Account_info
from apps.product.utils import is_new_member
from apps.asset.models import Member_asset_info, Order_dict, Member_income_statement,\
                              Member_red_pocket, Member_red_pocket_type
from apps.news.models import News, Sort
from apps.rewards.models import Activity
from apps.utils import toolkit

from apps.utils.message import send_message
from apps.dbinstance import db
from apps.utils.lock import *
from apps.activity.models import Zillionaire_info, Points_change
from apps.activity.utils import update_activity_status, huodong
from apps.product.utils import cncurrency,check_idcard,check_rate
from apps.message.models import Error_log


auth = HTTPBasicAuth()


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


def calculate_percentage(id):
    percentage = db.session.query(func.sum(Invest_info.money+Invest_info.hongbao))\
                                .filter(Invest_info.product_id == str(id).replace('-', ''),
                                        Invest_info.is_effect == 1).scalar()
    if percentage is None:
        percentage = 0
    return round(float(percentage), 6)


def yd_reg_red_pocket(type, member_id, total_fee):
    start_money = 0
    if float(total_fee) >= 50000:
        start_money = 30000
    elif float(total_fee) >= 30000:
        start_money = 20000
    elif float(total_fee) >= 10000:
        start_money = 10000

    tlist1 = (10000, 20000, 30000)
    mrt_list = Member_red_pocket_type.query.filter(and_(Member_red_pocket_type.type == type,
                                                   Member_red_pocket_type.start_money.in_(tlist1))).all()
    tlist2 = []
    for m in mrt_list:
        print '=========mrt1======='
        print tlist2.append(m.id)

    mr_list= Member_red_pocket.query.filter(and_(Member_red_pocket.sort_id.in_(tlist2), Member_red_pocket.member_id==member_id)).all()

    if not mr_list:
        for mrt in mrt_list:
            if mrt.start_money == start_money:
                now_time = datetime.now()
                gen_time = datetime.strftime((now_time  + timedelta(int(mrt.validtime))), '%Y-%m-%d %H:%M:%S')
                ydmr = Member_red_pocket(member_id=member_id, sort_id=mrt.id, generate_time=gen_time)
                db.session.add(ydmr)
                db.session.commit()
                return ydmr
    return None


@app.route("/v1/mobile/index", methods=['GET', 'POST'])
def get_mobile_index2():
    query_res = News.query.join(Sort, Sort.id == News.sortid).filter(and_(Sort.label == "banner", \
                                Sort.metakeyword == "banner")).order_by(News.posttime.desc()).limit(6).all()
    response_data = {}
    response_data["code"] = u"10000"
    response_data["desc"] = u"请求成功"
    response_data["content"] = {}
    response_data["content"]["banner"] = []
    response_data["content"]["img"] = []
    response_data["content"]["img"].append(dict(img=(BOLUO_URL +'/upload/images/home_new_icon@3x.png'), url=BOLUO_URL+'/v1/html5/hongbaogl'))
    Now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for item in query_res:
        if item.end_time and datetime.now() <= item.end_time:
            continue
        img_url = BOLUO_URL + item.image
        response_data["content"]["banner"].append(dict(img=img_url, url=item.content.strip(), type=item.hits))

    base_url = "https://m.boluolc.com/index.php/news/newdetail/id/"
    query_res = News.query.join(Sort, Sort.id == News.sortid).filter(and_(Sort.label == "notice", \
                                Sort.metakeyword == "announcement")).order_by(News.posttime.desc()).limit(5).all()
    response_data["content"]["notice"] = []
    for item in query_res:
        url = base_url + str(item.id).replace("-", "")
        # url = 'https://m.boluolc.com/home/raiders'
        response_data["content"]["notice"].append(dict(title=item.title, url=url))


    response_data["content"]["newer"] = []

    query_top = db.session.query(Product_info.id, Product_info.product_name, Product_info.product_type, Product_info.feature_id, Product_info.rate, Product_info.sell_time,
                                     Product_info.time_limit, Product_info.product_status, Product_info.raise_limit, Product_info.total_mount, Product_info.limit_mount, Product_info.is_recommend, Product_info.rate_increase)
    products_1 = query_top.filter(and_(Product_info.start_time <= Now,
                                            Product_info.product_status == '2')
                                       ).order_by(Product_info.time_limit, Product_info.sell_time.desc()).limit(20).all()
    products_all = (products_1,)
    query_feature = db.session.query(Feature_info.id, Feature_info.feature_name)

    # 计算每个标的投资进度
    response_data["content"]["tjcp"] = []
    response_data_sort_list = []
    response_data_new_sort_list02 = []
    feature_id_to_name = {  # 产品特色 id -> name
        '531d3ab7507063f00150708d4bcc001b': '房产抵押',
        '531d3ab7507063f00150708d4bcc002b': '加息3%',
        '531d3ab750cc47070150ccd72a3f0023': '供应链',
        '531d3ab750cc47070150ccd77f700025': '本息保障',
        '531d3ab750d71de90150db3c3a150021': '新手专享',
        'ff808081581de407015829d8d9a20445': '活动加息',
        'ff808081581de407015829db133a0447': '爆款'
    }
    for product in products_1:
        percentage = floor((calculate_percentage(product.id)) / (product.total_mount) * 10000) / 100  # 标的投资百分比
        if percentage >= 100.0:
            percentage = 100.0
        result_dict = {}
        result_dict["id"] = str(product.id)
        result_dict["product_name"] = product.product_name
        result_dict["product_type"] = product.product_type
        result_dict["feature_id"] = product.feature_id
        f = product.feature_id
        if f is not None:  # 如果标的产品特色id不为空，则返回一个产品特色name按','分割的字符串
            feature_ids = f.split(",")
            result_dict["feature_name"] = ','.join([feature_id_to_name.get(x) for x in feature_ids])
        result_dict["rate"] = product.rate
        result_dict["time_limit"] = product.time_limit
        result_dict["total_mount"] = product.total_mount
        result_dict["limit_mount"] = product.limit_mount
        result_dict["rate_increase"] = str(product.rate_increase)
        result_dict["percentage"] = percentage
        result_dict["sell_time"] = str(product.sell_time)
        result_dict["raise_limit"] = str(product.raise_limit)
        result_dict["product_status"] = str(product.product_status)
        result_dict["is_recommend"] = product.is_recommend
        result_dict["product_remain"] = round(product.total_mount - calculate_percentage(str(product.id)), 2)
        if product.product_type == '新手标':
            response_data_new_sort_list02.append(result_dict)
            continue
        else:
            result_dict["is_new_product"] = '0'

        response_data_sort_list.append(result_dict)

    # response_data_sort_list = sorted(response_data_sort_list, key=itemgetter(0, 1, 2), reverse=True)

    a = sorted(response_data_sort_list, key = lambda e: e.__getitem__('percentage'), reverse=True)  # 按百分比倒序
    response_data_sort_list = sorted(a, key = lambda e: int(e.__getitem__('time_limit')), reverse=True)  # 按投资期限倒序


    # response_data_new_sort_list02 = sorted(response_data_new_sort_list02, key=itemgetter(0, 1, 2), reverse=True)[:1]

    b = sorted(response_data_new_sort_list02, key=lambda e: e.__getitem__('percentage'), reverse=True)  # 按百分比倒序
    response_data_new_sort_list02 = sorted(b, key=lambda e: int(e.__getitem__('time_limit')), reverse=True)[:1]  # 按投资期限倒序取一个

    response_data["content"]["newer"] = response_data_new_sort_list02

    response_data["content"]["tjcp"] = response_data_sort_list[:6]


    #判断是否是新手
    response_data["is_new_member"] = []
    response_data["newhand_red_pocket_img_url"] = []
    newhand_base_url = 'https://www.boluolc.com'
    newhand_img_url = '/upload/images/xinshouhongbao.png'
    newhand_red_pocket_img_url = newhand_base_url + newhand_img_url
    response_data["newhand_red_pocket_img_url"] = newhand_red_pocket_img_url


#------------------------头条新闻------------------
    heads = News.query.join(Sort, Sort.id == News.sortid).filter(and_(Sort.label == "news",
                                              Sort.metakeyword == "report")).order_by(
                                             News.posttime.desc()).first()
    head_new = {}
    if heads:
        head_new['title'] = heads.title if  heads.title else ""
        head_new['image'] = BOLUO_URL + str(heads.image) if heads.image else ""
    response_data['new'] = head_new
# -----------------------活动起屏区域---------------
    response_data['huodong_0_show'] = '1'
    response_data['huodong_0'] = 'https://www.boluolc.com/upload/images/huodong_0_20170118.png'
    response_data['huodong_0_next'] = '/v1/activity/huodong/0'

    response_data['huodong_1_show'] = '1'
    response_data['huodong_1'] = 'https://www.boluolc.com/upload/images/huodong_1_20170118.png'
    response_data['huodong_1_next'] = '/v1/activity/zill/'

    response_data['huodong_show_ios'] = '0'
# -----------------------活动起屏区域end---------------

    return toolkit.response(response_data, 200, None, True)


@app.route("/v1/member/isnewmember/<name_or_phone>")
def get_new_member(name_or_phone):

    response_data = {}
    response_data["code"] = u"10000"
    response_data["desc"] = u"请求成功"
    if name_or_phone is not None:
        response_data["is_new_member"] = []
        is_new_member = Invest_info.query.join(Member, Member.id == Invest_info.member_id).filter(
            or_(Member.name == name_or_phone, \
                Member.phone == name_or_phone)).first()
        if is_new_member is not None:
            response_data["is_new_member"] = "false"
        else:
            response_data["is_new_member"] = "true"

    return toolkit.response(response_data, 200, None, True)


@app.route("/v1/product/new", methods=['GET', 'POST'])
def get_product_new():

    query_top = db.session.query(Product_new)
    products = query_top.filter(Product_new.product_status =='1').all()
    result_json={}
    result_json["code"] = "10000"
    result_json["content"] = []
    result_json["des"] = u"请求成功"
    for product in products:
        result_dict = {}
        result_dict["id"]=str(product.id)
        result_dict["product_name"] = product.product_name
        result_dict["rate"] = product.rate
        result_dict["time_limit"] = product.time_limit
        result_dict["limit_mount"] = product.limit_mount
        result_dict["product_status"] = str(product.product_status)
        result_dict["product_detail"] = product.product_detail
        result_dict["repay_type"] = product.repay_type
        result_dict["base_url"] = "https://m.boluolc.com/index.php/home/financial/noviceinfo/id/%s" % str(product.id)
        result_json["content"].append(result_dict)

    return toolkit.response(result_json, 200, None, True)


@app.route("/v1/product/top/ten", methods=['GET', 'POST'])
def get_product():

    Now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # 取出前10个散标
    query_top = db.session.query(Product_info.id,Product_info.product_name, Product_info.product_type, Product_info.feature_id,Product_info.rate, Product_info.sell_time,
                                Product_info.time_limit, Product_info.product_status, Product_info.raise_limit, Product_info.total_mount, Product_info.limit_mount,Product_info.is_recommend, Product_info.rate_increase)
    products_1 = query_top.filter(and_(Product_info.start_time <= Now, and_(Product_info.product_status !='1', Product_info.product_status !='6', Product_info.product_status !='7',Product_info.product_type == "定期宝"), Product_info.product_type != "新手标")).order_by(Product_info.start_time.desc()).limit(3).all()
    products_2 = query_top.filter(and_(Product_info.start_time <= Now, and_(Product_info.product_status !='1', Product_info.product_status !='6', Product_info.product_status !='7',Product_info.product_type == "供应链"), Product_info.product_type != "新手标")).order_by(Product_info.start_time.desc()).limit(3).all()
    products_3 = query_top.filter(and_(Product_info.start_time <= Now, and_(Product_info.product_status !='1', Product_info.product_status !='6', Product_info.product_status !='7',Product_info.product_type == "房产抵押"), Product_info.product_type != "新手标")).order_by(Product_info.start_time.desc()).limit(3).all()
    products_all = (products_1, products_2, products_3)
    query_feature = db.session.query(Feature_info.id, Feature_info.feature_name)


    # 计算每个标的投资进度
    result_json={}
    result_json["code"] = u"10000"
    result_json["content"] = {}
    result_json["content"]["dqb"] = []
    result_json["content"]["gyl"] = []
    result_json["content"]["fcdy"] = []
    result_json["des"] = u"请求成功"
    for products in products_all:
        for product in products:
            percentage = (calculate_percentage(product.id))/(product.total_mount)*100
            if percentage >=100.0 :
                percentage =100.0
            result_dict = {}
            result_dict["id"]=str(product.id)
            result_dict["product_name"] = product.product_name
            result_dict["product_type"] = product.product_type
            result_dict["feature_id"] = product.feature_id
            f = product.feature_id
            if f is not None:
                feature_ids = f.split(",")
                feature_names = ''
                for feature_id in feature_ids:
                    features = query_feature.filter(Feature_info.id == feature_id).first()
                    feature_name = features.feature_name
                    feature_names = feature_names + feature_name + ","
            result_dict["feature_name"] = feature_names[:-1]
            result_dict["rate"] = product.rate
            result_dict["time_limit"] = product.time_limit
            result_dict["total_mount"] = product.total_mount
            result_dict["limit_mount"] = product.limit_mount
            result_dict["percentage"] = percentage
            result_dict["sell_time"] = str(product.sell_time)
            result_dict["raise_limit"] = str(product.raise_limit)
            result_dict["product_status"] = str(product.product_status)
            result_dict["is_recommend"] = product.is_recommend
            ptype = product.product_type
            type = ptype.encode("utf-8")
            if type == "定期宝":
                result_json["content"]["dqb"].append(result_dict)
            if type == "供应链":
                result_json["content"]["gyl"].append(result_dict)
            if type == "房产抵押":
                result_json["content"]["fcdy"].append(result_dict)
    return toolkit.response(result_json, 200, None, True)


@app.route("/v1/product/page/<ptype>/<page_num>", methods=['GET', 'POST'])
def get_product_page(ptype, page_num):

    pnum = int(page_num.encode('ascii'))
    Now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    pnum = (pnum-1) *10
    pro_type = None
    if ptype == "fcdy":
        pro_type = u"房产抵押"
    elif ptype == "gyl":
        pro_type = u"供应链"
    elif ptype == "sxjh":
        pro_type = u"定期宝"
    query_top = db.session.query(Product_info.id, Product_info.product_name, Product_info.product_type, Product_info.rate,Product_info.sell_time,\
                                 Product_info.time_limit, Product_info.product_status, Product_info.raise_limit, Product_info.total_mount, Product_info.limit_mount, Product_info.rate_increase)
    products = query_top.filter(and_(Product_info.start_time <= Now, and_(Product_info.product_status !='1', Product_info.product_status !='6', Product_info.product_status !='7'), Product_info.product_type == pro_type)).order_by(Product_info.start_time.desc())[pnum:pnum+10]

    result_json={}
    result_json["code"] = "10000"
    result_json["desc"] = u"请求成功"
    result_json["content"] = []
    for product in products:
        percentage = round((calculate_percentage(product.id))/(product.total_mount)*100, 2)
        result_dict = {}
        result_dict["id"]=str(product.id)
        result_dict["product_name"] = product.product_name
        result_dict["product_type"] = product.product_type
        result_dict["rate"] = product.rate
        result_dict["time_limit"] = product.time_limit
        result_dict["total_mount"] = product.total_mount
        result_dict["limit_mount"] = product.limit_mount
        result_dict["percentage"] = percentage
        result_dict["sell_time"] = str(product.sell_time)
        result_dict["raise_limit"] = str(product.raise_limit)
        result_dict["product_status"] = str(product.product_status)
        result_json["content"].append(result_dict)

    return toolkit.response(result_json, 200, None, True)


@app.route("/v1/product/<type>/page/all/<page_num>", methods=['GET', 'POST'])
def get_new_product_all(type, page_num):

    pnum = int(page_num.encode('ascii'))
    Now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    pnum = (pnum-1) *10
    query_top = db.session.query(Product_info.id, Product_info.product_name, Product_info.product_type, Product_info.rate,Product_info.sell_time,\
                                 Product_info.time_limit, Product_info.product_status, Product_info.raise_limit, Product_info.total_mount, Product_info.limit_mount, Product_info.rate_increase)
    if type == '0':
        products = query_top.filter(and_(Product_info.start_time <= Now, and_(Product_info.product_status !='1', Product_info.product_status !='6', Product_info.product_status !='7'
                                                                          ,Product_info.product_type == '新手标'))).order_by(Product_info.product_status.asc(), Product_info.sell_time.desc())[pnum:pnum+10]
    elif type == '1':
        products = query_top.filter(and_(Product_info.start_time <= Now, and_(Product_info.product_status !='1', Product_info.product_status !='6', Product_info.product_status !='7'
                                                                          ,Product_info.product_type != '新手标'))).order_by(Product_info.product_status.asc(), Product_info.sell_time.desc())[pnum:pnum+10]
    else:
        response_data["code"] = u"10001"
        response_data["content"] = u"请求参数有误!"
        return toolkit.response({}, 200, None, True)

    result_json = {}
    result_json["code"] = "10000"
    result_json["desc"] = u"请求成功"
    result_json["content"] = []
    response_data_sort_list = []
    response_data_new_sort_list = []
    for product in products:
        max_percentage = True
        percentage = round((calculate_percentage(product.id)) / (product.total_mount) * 100, 2)
        if percentage >= 100.0:
            percentage = 100.0
            max_percentage = False
        result_dict = {}
        result_dict["id"] = str(product.id)
        result_dict["product_name"] = product.product_name
        result_dict["product_type"] = product.product_type
        result_dict["rate"] = product.rate
        result_dict["time_limit"] = product.time_limit
        result_dict["total_mount"] = product.total_mount
        result_dict["limit_mount"] = product.limit_mount
        result_dict["percentage"] = percentage
        result_dict["sell_time"] = str(product.sell_time)
        result_dict["raise_limit"] = str(product.raise_limit)
        result_dict["rate_increase"] = product.rate_increase
        result_dict["product_status"] = str(product.product_status)

        response_data_sort_list.append((max_percentage, percentage, result_dict))

    response_data_sort_list = sorted(response_data_sort_list, key=itemgetter(0, 1), reverse=True)
    for i in response_data_sort_list:
        result_json["content"].append(i[2])

    return toolkit.response(result_json, 200, None, True)


@app.route("/v1/product/sum/<ptype>",methods=['GET', 'POST'])
def get_product_sum_ptype(ptype):

    ptypedict={"gyl":u"供应链","fcdy":u"房产抵押","sxjh":u"定期宝"}
    response_data = {}
    if not ptypedict.has_key(ptype):
        response_data["code"] = u"10001"
        response_data["content"] = {}
        response_data["desc"] =u"无此类型"
        return toolkit.response(response_data, 200, None, True)
    
    query_top = db.session.query(Product_info.id).filter(and_(Product_info.product_type == ptypedict[ptype], Product_info.product_status !='1', \
                                 Product_info.product_status !='6', Product_info.product_status !='7'))
    response_data["code"] = u"10000"
    response_data["content"] =dict(count = unicode(query_top.count()))
    response_data["desc"] =u"请求成功"
    return toolkit.response(response_data, 200, None, True)


@app.route("/v1/product/sum",methods=['GET', 'POST'])
def get_product_sum():
    
    query_top = db.session.query(Product_info.id)
    response_data = {}
    response_data["code"] = u"0"
    response_data["count"] =unicode(query_top.count())
    return toolkit.response(response_data, 200, None, True)


@app.route("/v1/product/detail/<product_id>", methods=['GET','POST'])
def get_product_detail_new(product_id):
    response_data = {}
    base_url = "https://m.boluolc.com/index.php/home/financial/details/id/%s/key/%s"
    query_detail = db.session.query(Product_info, Product_info.borrow_id)
    query_result = query_detail.filter(Product_info.id==product_id).first()
    response_data["content"] = {}

    phone = request.form.get('phone')
    if phone:
        m = Member.query.filter_by(phone=phone).first()
        asset = Member_asset_info.query.filter_by(member_id=m.id).first()
        if asset:
            response_data["content"]["remain_balance"] = asset.rechargeamount + asset.remainamount
        else:
            response_data["content"]["remain_balance"] = ''
        response_data["content"]["is_register_xinwang"] = m.is_register_xinwang
        response_data["content"]["is_pay_bind"] = m.is_pay_bind
    if product_id is None :
        response_data["code"] = u"10001"
        response_data["desc"] = u"请求的参数为空"
        response_data["content"] = {}
        return toolkit.response(response_data, 200, None, True)
    if not query_result:
        response_data["code"] = u"10002"
        response_data["desc"] = u"此项目不存在"
        response_data["content"] = {}
        return toolkit.response(response_data, 200, None, True)
    response_data["content"]["percentage"] = (calculate_percentage(product_id))/(query_result[0].total_mount)*100
    response_data["content"]["remain_money"] = round(query_result[0].total_mount-calculate_percentage(product_id), 2)
    if response_data["content"]["remain_money"] < 0:
        response_data["content"]["remain_money"] = 0
    response_data["content"]["product_name"] = query_result[0].product_name
    response_data["content"]["product_type"] = query_result[0].product_type
    response_data["content"]["rate"] = query_result[0].rate
    response_data["content"]["time_limit"] = query_result[0].time_limit
    response_data["content"]["total_mount"] = query_result[0].total_mount
    response_data["content"]["limit_mount"] = query_result[0].limit_mount
    response_data["content"]["sell_time"] = str(query_result[0].sell_time)
    response_data["content"]["raise_limit"] = str(query_result[0].raise_limit)
    response_data["content"]["product_status"] = str(query_result[0].product_status)
    response_data["content"]["repay_type"] = query_result[0].repay_type
    response_data["content"]["product_detail"] = base_url %(product_id, 1)
    response_data["content"]["product_image"] = base_url %(product_id, 2)
    response_data["content"]["product_invest"] = base_url %(product_id, 3)
    response_data["content"]["rate_increase"] = query_result[0].rate_increase
    response_data["code"] = u"10000"
    response_data["desc"] = u"请求成功"
    return toolkit.response(response_data, 200, None, True)


@app.route("/v1/product/borrower", methods=['GET','POST'])
def get_product_borrower():

    product_id = request.form.get('product_id', None)
    response_data = {}
    if product_id is None:
        response_data["code"] = u"1"
        response_data["content"] = u"请求的项目借款人不存在"
        return toolkit.response(response_data, 200, None, True)

    query_res = Borrower_info.query.join(Product_info, Product_info.borrow_id == Borrower_info.id).filter(Product_info.id == product_id).all()

    return toolkit.query_result_to_json(query_res)


@app.route("/v1/product/image", methods=['GET','POST'])
def get_product_images():

    product_id = request.form.get('product_id', None)
    response_data = {}
    if product_id is None:
        response_data["code"] = u"1"
        response_data["content"] = u"请求的项目图片不存在"
        return toolkit.response(response_data, 200, None, True)

    query_res = Product_image.query.filter(Product_image.borrow_id == product_id).all()

    return toolkit.query_result_json(query_res)


@app.route("/v1/product/invest/<product_id>/<page_total>/<page_num>", methods=['GET','POST'])
def get_invest(product_id, page_total, page_num):
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
    response_data = {}
    query_top = db.session.query(Invest_info, Member.name, Member.phone)
    query_amount = query_top.filter(and_(Invest_info.product_id == product_id, Invest_info.member_id == Member.id)) \
        .order_by(Invest_info.time.desc()).all()
    amount = len(query_amount)
    query_res = query_top.filter(and_(Invest_info.product_id == product_id, Invest_info.member_id == Member.id))\
                                .order_by(Invest_info.time.desc()).all()[pnum:page_mount]

    if product_id is None or len(query_res) == 0:
        response_data["code"] = u"10001"
        response_data["content"] = {}
        response_data["desc"] = u"请求的项目投资信息不存在"
        return toolkit.response(response_data, 200, None, True)


    response_data["code"] = u"10000"
    response_data["desc"] = u"请求成功"
    response_data["amount"] = amount
    response_data["content"] = []
    for item in query_res:
        response_data["content"].append(dict(invest_phone=item[2], invest_money=item[0].money, invest_time=str(item[0].time)))

    return toolkit.response(response_data, 200, None, True)


@app.route("/v1/product/<name_or_phone>/current/invest", methods=['GET', 'POST'])
# @auth.login_required
def user_current_invest(name_or_phone):

    response_data = {}

    m = Member.query.filter(or_(Member.name==name_or_phone, Member.phone==name_or_phone)).first()
    if m is None:
        response_data["code"] = u"10002"
        response_data["desc"] = u"用户不存在"
        return toolkit.response(response_data, 200, None, True)

    query_top = db.session.query(Invest_info, Product_info.product_name, Product_info.product_type, Product_info.total_mount, Product_info.interest_time)
    query_res = query_top.filter(and_(Invest_info.product_id == Product_info.id, or_(Invest_info.status==1, Invest_info.status==2),
                                      Invest_info.member_id == str(m.id).replace('-',''))).order_by(Invest_info.time.desc()).limit(10).all()



    #if query_res is None or len(query_res)==0:
    #    response_data["code"] = u"17"
    #    response_data["content"] = u"用户不存在或者用户没有投资"
    #    return toolkit.response(response_data, 200, None, True)

    return toolkit.query_result_to_json(query_res)


# @app.route("/v1/product/<name_or_phone>/invest", methods=['GET', 'POST'])
# @auth.login_required

@app.route("/v1/product/<name_or_phone>/invest/<page_num>", methods=['GET', 'POST'])
# @auth.login_required
def user_invest(name_or_phone, page_num):
    response_data = {}
    try:
        page = int(page_num)
    except:
        page = 1
    m = Member.query.filter(or_(Member.name == name_or_phone, Member.phone == name_or_phone)).first()
    if m is None:
        response_data["code"] = u"2"
        response_data["content"] = u"用户不存在"
        return toolkit.response(response_data, 200, None, True)

    # invest_list = Invest_info.query.filter_by(member_id=str(m.id).replace('-', '')).first()

    # print invest_list.order_id


    query_top = db.session.query(Invest_info.money, Invest_info.member_id, Invest_info.status, Invest_info.member_name,Invest_info.time, Invest_info.profit, Invest_info.NEWHAND_ID, Invest_info.is_effect,
                                 Invest_info.product_id, Product_info.product_name, Product_info.start_time,
                                 Product_info.time_limit, Product_info.product_type, Product_info.total_mount, Invest_info.order_id,
                                 Product_info.end_time, Product_info.rate, Product_info.rate_increase, Invest_info.hongbao, Product_info.repay_type, Invest_info.contract,
                                 Product_info.product_status, Product_info.interest_time,Invest_info.preservationId, Invest_info.activity, Invest_info.rate_security, Invest_info.extra_rate)
    # query_newhand = db.session.query(Invest_info.money, Invest_info.member_id, Invest_info.status, Invest_info.time, Invest_info.profit, Invest_info.NEWHAND_ID, Product_new.product_name, Product_new.time_limit)
    query_res_total = query_top.filter(and_(Invest_info.member_id == str(m.id).replace('-', ''), Invest_info.product_id == Product_info.id)).order_by(Invest_info.status.asc()).order_by(Invest_info.time.desc()).all()
    # query_newhand_total = query_newhand.filter(and_(Invest_info.member_id == str(m.id).replace('-', ''), Invest_info.NEWHAND_ID == Product_new.id)).order_by(Invest_info.time.desc()).all()

    index = request.args.get('index')
    if str(index) == '1':
        query_res_total = query_top.filter(and_(Invest_info.member_id == str(m.id).replace('-', ''), Invest_info.product_id == Product_info.id,or_(Invest_info.status == '1',Invest_info.status == '2'))).order_by(Invest_info.status.asc()).order_by(Invest_info.time.desc()).all()
    elif str(index) == '2':
        query_res_total = query_top.filter(
            and_(Invest_info.member_id == str(m.id).replace('-', ''), Invest_info.product_id == Product_info.id,Invest_info.status == '3')).order_by(Invest_info.time.desc()).all()
    response_data = {}
    response_data["code"] = u"10000"
    response_data["desc"] = u"请求成功"
    response_data["content"] = []
    status_dict = {"1": u"投资中", "2": u"还款中", "3": u"已完成"}

    for query_res in query_res_total:
        if query_res.is_effect == 0:
            continue
        response_dict = {}
        percentage = (calculate_percentage(query_res.product_id)) / (query_res.total_mount) * 100
        if percentage >= 100.0:
            percentage = 100.0
        response_dict["invest_money"] = query_res.money
        response_dict["id"] = query_res.product_id
        response_dict["invest_status"] = status_dict[query_res.status]
        # response_dict["hongbao"] = query_res.hongbao
        rate_security = query_res.rate_security if query_res.rate_security else 0
        # response_dict["rate_security"] = rate_security
        if query_res.hongbao:
            youhuijuan = '%s元抵扣红包' % query_res.hongbao
        elif rate_security:
            youhuijuan = '%s％加息劵' % (rate_security*100)
        else:
            youhuijuan = ''
        response_dict["hongbao"] = youhuijuan
        response_dict["repay_type"] = query_res.repay_type
        response_dict["rate"] = query_res.rate
        # 额外加息
        response_dict["rate_increase"] = query_res.rate_increase + query_res.extra_rate
        response_dict["percentage"] = round(percentage, 3)

        response_dict["invest_time"] = str(query_res.time)
        if query_res.interest_time:
            response_dict["interest_time"] = str(query_res.interest_time)
        else:
            response_dict["interest_time"] = ''
        response_dict['is_xinshoubiao'] = '1' if query_res.product_type == '新手标' else '0'
        response_dict["pro_fit"] = query_res.profit
        response_dict["order_id"] = query_res.order_id
        response_dict["product_name"] = query_res.product_name
        response_dict["start_time"] = str(query_res.start_time)
        if query_res.preservationId:
            response_dict['link'] = "html5/yibaoquan/%s" % query_res.preservationId
            response_dict['isnew'] = '1'
        else:
            if query_res.contract is not None and query_res.contract != u"":
                contract = Contract.query.filter_by(id=query_res.contract).first()
                response_dict['isnew'] = '0'
                if contract and contract.contract_name == u'借款合同':
                    response_dict['link'] = "product/borrow/demo/%s" % query_res.order_id
                else:
                    response_dict['link'] = "product/order/dianzipingzheng/%s" % query_res.order_id
            else:
                response_dict['isnew'] = '0'
                response_dict['link'] = ''
        response_dict["time_limit"] = str(query_res.time_limit)
        response_dict["total_mount"] = str(query_res.total_mount)
        response_dict["NEWHAND_NAME"] = query_res.product_name
        if query_res.status == '1':
            response_dict['end_time'] = str(query_res.time + timedelta(days=int(query_res.time_limit)))
        else:
            response_dict['end_time'] = str(query_res.end_time) if query_res.end_time else ""

        response_data["content"].append(dict(response_dict))

    response_data["content"] = response_data["content"][10*page-10:10*page]
    return toolkit.response(response_data, 200, None, True)


#回款日历  http://127.0.0.1:8000/v1/product/18519291259/2017-08-02 22:02:48/hkrl
@app.route('/v1/product/<name_or_phone>/hkrl', methods=['GET', 'POST'])
def hkrl(name_or_phone):
    shijian_xin = request.args.get('date')
    response_data = {}

    shijian = time.strptime(shijian_xin, '%Y-%m-%d')

    m = Member.query.filter(or_(Member.name == name_or_phone, Member.phone == name_or_phone)).first()

    if m is None:
        response_data["code"] = u"2"
        response_data["content"] = u"用户不存在"
        return toolkit.response(response_data, 200, None, True)

    response_data["code"] = u"10000"
    response_data["desc"] = u"请求成功"
    response_data["content"] = []
    response_dict = {}

    d = calendar.monthrange(shijian.tm_year, shijian.tm_mon)
    biao_begin = '%s-%s-%s 00:00:00' % (shijian.tm_year, shijian.tm_mon, shijian.tm_mday)
    biao_end = '%s-%s-%s 23:59:59' % (shijian.tm_year,shijian.tm_mon,d[1])

    # tzxq = Invest_info.query.filter(Invest_info.member_id == str(m.id).replace('-', ''),Invest_info.time.between(biao_begin, biao_end)).all()
        # xmmx = Product_info.query.filter(Product_info.id == str(tzxq.product_id).replace('-', '')).first()

    #本月投资金额
    # custom_money = db.session.query(func.sum(Invest_info.money)).filter(and_(
    #     Invest_info.member_id == str(m.id).replace('-', ''), Invest_info.time.between(biao_begin, biao_end))).scalar()
    #本月的标到期的投资的本金
    custom_money_unreturn = db.session.query(func.sum(Invest_info.money)).filter(and_(
        Invest_info.member_id == str(m.id).replace('-', ''), Invest_info.is_effect==1, Invest_info.status != 3,
        Invest_info.product_id == Product_info.id,
        (Product_info.end_time if Product_info.end_time else Invest_info.expect_time).between(biao_begin, biao_end))).scalar()
    #回款金额
    custom_return = db.session.query(func.sum(Invest_info.profit)).filter(and_(
        Invest_info.member_id == str(m.id).replace('-', ''), Invest_info.is_effect==1, Invest_info.status != 3, Invest_info.product_id == Product_info.id,
        (Product_info.end_time if Product_info.end_time else Invest_info.expect_time).between(biao_begin, biao_end))).scalar()
    #回款笔数
    custom_times = db.session.query(Product_info).filter(and_(
        Invest_info.member_id == str(m.id).replace('-', ''), Invest_info.is_effect==1, Invest_info.status != 3, Invest_info.product_id == Product_info.id,
        (Product_info.end_time if Product_info.end_time else Invest_info.expect_time).between(biao_begin, biao_end))).count()
    # 待收收益
    custom_profit = (custom_return or 0) - (custom_money_unreturn or 0)

    response_dict["custom_times"] = custom_times if custom_times else "0"
    response_dict["custom_money"] = round(custom_money_unreturn,2) if custom_money_unreturn else "0"
    response_dict["custom_return"] = round(custom_return,2) if custom_return else "0"
    response_dict["custom_profit"] = round(custom_profit,2) if custom_profit else "0"
    response_data["content"].append(dict(response_dict))

    custom_list = db.session.query(Product_info,Invest_info).filter(and_(
        Invest_info.member_id == str(m.id).replace('-', ''), Invest_info.is_effect==1, Invest_info.status != 3,
        Invest_info.product_id == Product_info.id,
        or_(Product_info.end_time.between(biao_begin, biao_end), Invest_info.expect_time.between(biao_begin, biao_end)))).all()
    riqi = []
    for i in custom_list:
        if i.Product_info.end_time:
            custom_one = i.Product_info.end_time
            if custom_one.timetuple().tm_mon != shijian.tm_mon:
                continue
        else:
            custom_one = i.Invest_info.expect_time
        if dict(day=custom_one.day) not in riqi:
            riqi.append(dict(day=custom_one.day))
    riqi_dict = {'riqi':riqi}
    response_data["content"].append(riqi_dict)

    return toolkit.response(response_data, 200, None, True)


#回款日历ajax
@app.route('/v1/asset/<name_or_phone>/hkrlajax', methods=['GET', 'POST'])
def hkrl2(name_or_phone):
    response_data = {}
    m = Member.query.filter(or_(Member.name == name_or_phone, Member.phone == name_or_phone)).first()
    if m is None:
        response_data["code"] = u"2"
        response_data["content"] = u"用户不存在"
        return toolkit.response(response_data, 200, None, True)

    custom_phone = name_or_phone

    date = request.args.get('date')
    try:
        date = time.strptime(date, '%Y-%m-%d')
    except:
        date = str(datetime.now().date())

    response_data["code"] = u"10000"
    response_data["desc"] = u"请求成功"
    response_data["content"] = []

    query_top = db.session.query(Invest_info.profit - Invest_info.money, Invest_info.money, Invest_info.member_id,
                                 Invest_info.status,
                                 Invest_info.member_name, Invest_info.time, Invest_info.profit,
                                 Invest_info.NEWHAND_ID,
                                 Invest_info.product_id, Product_info.product_name,
                                 Product_info.start_time,
                                 Product_info.time_limit, Product_info.product_type,
                                 Product_info.total_mount, Invest_info.order_id,
                                 Product_info.end_time, Product_info.rate, Product_info.rate_increase,
                                 Invest_info.hongbao, Product_info.repay_type, Invest_info.contract,
                                 Product_info.product_status, Product_info.interest_time,
                                 Invest_info.preservationId, Invest_info.activity, Invest_info.rate_security,
                                 Invest_info.extra_rate)

    query_wes = query_top.filter(
        and_(
            Invest_info.member_name == custom_phone, Invest_info.product_id == Product_info.id, Invest_info.is_effect==1)
    )
    query_res = query_wes.filter(
        or_((func.date(Product_info.end_time) == date),
            and_(func.date(Product_info.end_time) == None, func.date(Invest_info.expect_time) == date))
    ).all()
    # or_((func.date(Product_info.end_time) == date),(func.date(Invest_info.expect_time) == date)))).all()


    for i in query_res:
        response_dict = {}
        response_dict['profit'] = round(i[0], 2)

        status_dict = {"1": u"投资中", "2": u"还款中", "3": u"已完成"}

        percentage = (calculate_percentage(i.product_id)) / (i.total_mount) * 100
        if percentage >= 100.0:
            percentage = 100.0
        response_dict["invest_money"] = i.money
        response_dict["id"] = i.product_id
        response_dict["invest_status"] = status_dict[i.status]
        rate_security = i.rate_security if i.rate_security else 0

        if i.hongbao:
            youhuijuan = '%s元抵扣红包' % i.hongbao
        elif rate_security:
            youhuijuan = '%s％加息劵' % (rate_security * 100)
        else:
            youhuijuan = ''
        response_dict["hongbao"] = youhuijuan
        response_dict["repay_type"] = i.repay_type
        response_dict["rate"] = i.rate
        # 额外加息
        response_dict["rate_increase"] = i.rate_increase + i.extra_rate
        response_dict["percentage"] = round(percentage, 3)

        response_dict["invest_time"] = str(i.time)
        if i.interest_time:
            response_dict["interest_time"] = str(i.interest_time)
        else:
            response_dict["interest_time"] = ''
        response_dict['is_xinshoubiao'] = '1' if i.product_type == '新手标' else '0'
        response_dict["pro_fit"] = i.profit
        response_dict["order_id"] = i.order_id
        response_dict["product_name"] = i.product_name
        response_dict["start_time"] = str(i.start_time)
        if i.preservationId:
            response_dict['link'] = "html5/yibaoquan/%s" % i.preservationId
            response_dict['isnew'] = '1'
        else:
            if i.contract is not None and i.contract != u"":
                contract = Contract.query.filter_by(id=i.contract).first()
                response_dict['isnew'] = '0'
                if contract and contract.contract_name == u'借款合同':
                    response_dict['link'] = "product/borrow/demo/%s" % i.order_id
                else:
                    response_dict['link'] = "product/order/dianzipingzheng/%s" % i.order_id
            else:
                response_dict['isnew'] = '0'
                response_dict['link'] = ''

        response_dict["time_limit"] = str(i.time_limit)
        response_dict["total_mount"] = str(i.total_mount)
        response_dict["NEWHAND_ID"] = i.NEWHAND_ID or ""
        response_dict["NEWHAND_NAME"] = i.product_name
        if i.status == '1':
            response_dict['end_time'] = str(i.time + timedelta(days=int(i.time_limit)))
        else:
            response_dict['end_time'] = str(i.end_time) if i.end_time else ""

        response_data["content"].append(dict(response_dict))

    return toolkit.response(response_data, 200, None, True)


@app.route("/v1/product/<name_or_phone>/invest/<status>/<page_total>/<page_num>",methods=['GET','POST'])
# @auth.login_required
def user_invest_page(name_or_phone, status, page_num, page_total):

    if page_num is None:
        page_num = 1
    else:
        pnum = int(page_num.encode('ascii'))

    if page_total is None:
        page_total = 10
    else:
        page_total = int(page_total.encode('ascii'))

    pnum = (pnum-1) *page_total

    response_data = {}

    page_mount = pnum+page_total
    m = Member.query.filter(or_(Member.name==name_or_phone, Member.phone==name_or_phone)).first()
    if m is None:
        response_data["code"] = u"2"
        response_data["content"] = u"用户不存在"
        return toolkit.response(response_data, 200, None, True)

    query_top = db.session.query(Invest_info, Product_info.product_name, Product_info.start_time, Product_info.product_type, Product_info.interest_time, Product_info.time_limit)
    query_res = query_top.filter(and_(Invest_info.product_id == Product_info.id, Invest_info.status == status,
                                      Invest_info.member_id == str(m.id).replace('-',''))).order_by(Invest_info.time.desc()).all()[pnum:page_mount]
    response_data = {}
    response_data["code"] = u"10000"
    response_data["desc"] = u"请求成功"
    response_data["content"] = []
    for item in query_res:
        response_data["content"].append(dict(product_name=item[1],product_id = item[0].product_id,invest_money=item[0].money, \
                                             pro_fit=item[0].profit, invest_time=str(item[0].time), \
                                             start_time=str(item[2]), time_limit=item[5], invest_status=item[0].status, interest_time=str(item[4])))
        #print item[1]
    return toolkit.response(response_data, 200, None, True)

    # return toolkit.query_result_to_json(query_res)

@app.route("/v1/product/<name_or_phone>/invest/<status>/all",methods=["GET","POST"])
@auth.login_required
def user_invest_total(name_or_phone,status):

    reponse_data = {}

    m = Member.query.filter(or_(Member.name==name_or_phone,Member.phone==name_or_phone)).first()
    if m is  None:
        reponse_data["code"] = u"2"
        reponse_data["content"] = u"用户不存在"
        return toolkit.response(reponse_data,200,None,True)
    query_top = db.session.query(Invest_info,Product_info.product_name,Product_info.start_time,Product_info.product_type)
    query_res = query_top.filter(and_(Invest_info.product_id == Product_info.id, Invest_info.status == status,
                                      Invest_info.member_id == str(m.id).replace('-',''))).order_by(Invest_info.time.desc()).all()

    reponse_data = {}
    reponse_data["code"] = u"0"
    reponse_data["count"] = unicode(len(query_res))
    return toolkit.response(reponse_data, 200, None, True)


@app.route("/v1/product/<name_or_phone>/contract/<id>", methods=['GET', 'POST'])
@auth.login_required
def get_contract(name_or_phone, id):
    
    query_res = Member_real_info.query.join(Member).filter(or_(Member.name == name_or_phone, Member.phone == name_or_phone)).first()
    con = Contract.query.filter(Contract.id==id).first()

    query_top = db.session.query(Product_info, Invest_info, Borrower_info)
    query_res_s = query_top.filter(and_(Invest_info.product_id == Product_info.id, Product_info.borrow_id == Borrower_info.id,
                                        Invest_info.contract == id,Invest_info.member_id == str(query_res.member_id).replace("-", ""))).first()

    response_data = {}
    response_data["code"]=u"0"
    response_data["name"] = query_res.real_name
    response_data["id_card"] = query_res.real_identid
    response_data["contract_tem"] = con.content
    response_data["nterest_time"] = str(query_res_s[0].interest_time)
    response_data["product_name"] = query_res_s[0].product_name
    response_data["money"] = query_res_s[1].money
    response_data["endtime"] = str(query_res_s[0].end_time)
    response_data["rate"] = query_res_s[0].rate
    response_data["product_type"] = query_res_s[0].product_type
    response_data["borrow_type"] = query_res_s[2].borrow_type
    response_data["borrow_id_card"] = query_res_s[2].id_card
    response_data["name"] = query_res_s[2].name
    response_data["time_limit"] = query_res_s[0].time_limit
    return toolkit.response(response_data, 200, None, True)


@app.route('/v1/asset/order/detail',methods=['POST'])
def order_detail():
    response_data = {}
    phone = request.form.get('phone')
    money = request.form.get('money')
    product_id = request.form.get('product_id')

    response_data["content"] = {}

    if not phone or not money:
        response_data["code"] = u"10001"
        response_data["desc"] = u"参数字段有误"
        return toolkit.response(response_data, 200, None, True)
    member = Member.query.filter_by(phone=phone).first()
    if not member:
        response_data["code"] = u"10002"
        response_data["desc"] = u"用户不存在"
        return toolkit.response(response_data, 200, None, True)
    if float(money) <= 0:
        response_data["code"] = u"10003"
        response_data["desc"] = u"输入投资金额有误"
        return toolkit.response(response_data, 200, None, True)
    if not product_id:
        response_data["code"] = u"10004"
        response_data["desc"] = u"产品不存在"
        return toolkit.response(response_data, 200, None, True)
    try:


        balance = Member_asset_info.query.filter_by(member_id=str(member.id).replace('-', '')).first()
        bank_info = Member_pay_info.query.filter_by(member_id=str(member.id).replace('-', '')).first()
        member_real_info = Member_real_info.query.filter_by(member_id=member.id).first()
        bank_logo = Member_bank_logo.query.filter_by(bank_code=bank_info.bank_code).first()
        product = Product_info.query.filter_by(id=product_id).first()

        percentage = calculate_percentage(product_id)
        product_remain = round(float(product.total_mount) - float(percentage), 2)

        query_top = db.session.query(Member_red_pocket, Member_red_pocket_type)
        query_list = query_top.filter(and_(Member_red_pocket.member_id==member.id,
                Member_red_pocket.sort_id==Member_red_pocket_type.id,Member_red_pocket.is_freeze == 0,Member_red_pocket.is_use == 0,Member_red_pocket.generate_time >= datetime.now()
                                           )).order_by(Member_red_pocket_type.money.desc()
                                             ).order_by(Member_red_pocket_type.start_money.desc()).order_by\
            (Member_red_pocket_type.rate.desc()).all()

        response_data["content"]["red_id"] = ""
        response_data["content"]["red_money"] = ""
        response_data["content"]["red_start_money"] = ""
        response_data["content"]["red_rate"] = ""
        response_data["content"]["type"] = ""
        response_data['content']['product_remain'] = product_remain

        for q in query_list:
            if q[1].start_money + q[1].money <= float(money) and int(q[1].invest_days) <= int(product.time_limit):
                response_data["content"]["red_id"] = q[0].id
                response_data["content"]["red_money"] = q[1].money if q[1].money else ''
                response_data["content"]["red_start_money"] = q[1].start_money
                response_data["content"]["red_rate"] = q[1].rate
                if q[1].rate > 0:
                    response_data["content"]["type"] = 1
                else:
                    response_data["content"]["type"] = 0
                break

        try:
            bank_address = BOLUO_URL + bank_logo.logo
        except:
            bank_address = BOLUO_URL + '/static/images/boluo_center404.png'
        response_data["desc"] = u"请求成功"
        response_data["code"] = u"10000"
        response_data["content"].update({'bank_name': bank_info.bank_name, 'bank_code': bank_info.bank_code,
                                         'bank_number': bank_info.pay_bankcard, 'single_amt': bank_info.single_amt,
                                         'day_amt': bank_info.day_amt, 'is_new_member': is_new_member(phone),
                                         'balance': (balance.remainamount + balance.rechargeamount),
                                         'real_name':member_real_info.real_name,'id_card':member_real_info.real_identid,
                                         'limit_mount':product.limit_mount,'rate':product.rate,
                                         'rate_increase':product.rate_increase,'time_limit':product.time_limit,
                                         'total_mount':product.total_mount,'product_name':product.product_name,
                                         'money':money,'bank_address':bank_address, 'product_id': product_id})
        if member.isblack == 'Sync':
            response_data["content"]["balance"] = 0.0

    except Exception,e:
        response_data["code"] = u"10004"
        response_data["desc"] = u"数据库操作失败"
        print '==================='
        print e
        print '==================='
    return toolkit.response(response_data, 200, None, True)


@app.route('/v1/asset/<name_or_phone>/order/submit', methods=['GET', 'POST'])
@sync(threading.Lock())
# @auth.login_required
def order(name_or_phone):
    import sys
    reload(sys)
    sys.setdefaultencoding('utf-8')
    product_id = request.form.get("product_id", None)
    total_fee = request.form.get("total_fee", None)
    red_pocket_id = request.form.get("red_pocket_id", None)
    pay_passwd = request.form.get("pay_passwd", None)
    response_data = {}
    if not product_id or not total_fee:
        response_data["code"] = u"10001"
        response_data["desc"] = u"参数字段不能为空"
        response_data["content"] = {}
        return toolkit.response(response_data, 200, None, True)

    m = Member.query.filter(or_(Member.name==name_or_phone, Member.phone==name_or_phone)).first()

    if m.isblack == 'Sync':
        response_data["code"] = u"10002"
        response_data["content"]={}
        response_data["desc"] = u"您的账户已被迁移到菠萝理财存管版，请用菠萝理财存管版登录！"
        return toolkit.response(response_data, 200, None, True)

    if int(m.is_identity_bind) == 0:
        response_data["code"] = u"10018"
        response_data["desc"] = u"用户未认证"
        response_data["content"] = {}
        return toolkit.response(response_data, 200, None, True)

    if pay_passwd and not m.verify_pay_password(pay_passwd):
        response_data["code"] = u"10010"
        response_data["desc"] = u"支付密码输入错误"
        response_data["content"] = {}
        return toolkit.response(response_data, 200, None, True)

    try:
        if float(total_fee) <= 0:
            response_data["code"] = u"10003"
            response_data["desc"] = u"交易金额不能小于0元"
            response_data["content"] = {}
            return toolkit.response(response_data, 200, None, True)
    except:
        pass

    pro = Product_info.query.filter_by(id = product_id).first()

    if pro is None:
        response_data["code"] = u"10021"
        response_data["desc"] = u"该产品不存在"
        response_data["content"] = {}
        return toolkit.response(response_data, 200, None, True)

    if pro.product_type == '新手标':
        is_new_product = True
    else:
        is_new_product = False

    if is_new_product:
        if is_new_member(name_or_phone) == 'false':
            response_data["code"] = u"10022"
            response_data["desc"] = u"您已经不是新手了"
            response_data["content"] = {}
            return toolkit.response(response_data, 200, None, True)

    if float(total_fee) > pro.limit_mount:
        response_data["code"] = u"10023"
        response_data["desc"] = u"新手标限额%s" % pro.limit_mount
        response_data["content"] = {}
        return toolkit.response(response_data, 200, None, True)

    asset = Member_asset_info.query.filter(Member_asset_info.member_id == str(m.id).replace('-','')).first()
    if round(asset.remainamount + asset.rechargeamount,2) < round(float(total_fee),2):
        response_data["code"] = u"10015"
        response_data["desc"] = u"账户余额不够,请充值"
        response_data["content"] = {}
        return toolkit.response(response_data, 200, None, True)
    has_total_total = float(total_fee) + float(calculate_percentage(product_id))

    if has_total_total <= float(pro.total_mount) and has_total_total+0.1 >= float(pro.total_mount):
        pro.product_status = "3"
    elif has_total_total > float(pro.total_mount):
        response_data["code"] = u"10013"
        response_data["desc"] = u"投资总额已达上限"
        response_data["content"] = {}
        return toolkit.response(response_data, 200, None, True)


    # -----------------------------使用红包------------------------------------

    rp = None
    rpt = None

    # 额外加息
    qg_rate = 0.0
    is_rate_pocket_val = False
    red_pocket_val = 0.0
    rate_security = 0.0
    hongbao_info_id = None

    # 可以用红包但不是新手
    hongbao_source = ''
    if red_pocket_id:
        if not is_new_product:
            query_top = db.session.query(Member_red_pocket_type, Member_red_pocket)
            query_res = query_top.filter(and_(Member_red_pocket.sort_id == Member_red_pocket_type.id, \
                                              Member_red_pocket.id == red_pocket_id)).all()
            if len(query_res)==0 or query_res is None:
                response_data["code"] = u"10008"
                response_data["desc"] = u"红包不存在,请检查错误"
                response_data["content"] = {}
                return toolkit.response(response_data, 200, None, True)
            elif len(query_res) > 1:
                response_data["code"] = u"10007"
                response_data["desc"] = u"存在多个红包,请检查错误"
                response_data["content"] = {}
                return toolkit.response(response_data, 200, None, True)
            else:
                rp = query_res[0][1]
                if rp.generate_time < datetime.now():
                    response_data["code"] = u"10008"
                    response_data["desc"] = u"红包不存在,请检查错误"
                    response_data["content"] = {}
                    return toolkit.response(response_data, 200, None, True)

                rpt = query_res[0][0]

                if int(rpt.invest_days) > int(pro.time_limit):
                    response_data["code"] = u"10008"
                    response_data["desc"] = u"该红包不适用于当前期限的项目"
                    response_data["content"] = {}
                    return toolkit.response(response_data, 200, None, True)

                if rpt.type == '99' and float(total_fee) >= float(query_res[0][0].start_money):
                    qg_rate += float(query_res[0][0].rate)
                    rate_security = float(query_res[0][0].rate)
                    is_rate_pocket_val = True
                else:
                    red_pocket_val = float(query_res[0][0].money)
                    red_pocket_val_start_money = float(query_res[0][0].start_money)
                    if rp.is_freeze:
                        response_data["code"] = u"10007"
                        response_data["desc"] = u"红包已使用,请检查错误"
                        response_data["content"] = {}
                        return toolkit.response(response_data, 200, None, True)

                    if float(total_fee) >= red_pocket_val_start_money:
                        pass
                    else:
                        response_data["code"] = u"10016"
                        response_data["desc"] = u"%s元红包的起投金额为%s, 请重新选择!" % (query_res[0][0].money, int(red_pocket_val_start_money+query_res[0][0].money))
                        response_data["content"] = {}
                        return toolkit.response(response_data, 200, None, True)
                hongbao_info_id = rp.id
                hongbao_source = query_res[0][0].name
        else:
            response_data["code"] = u"10025"
            response_data["desc"] = u"新手不能使用红包"
            response_data["content"] = {}
            return toolkit.response(response_data, 200, None, True)


    # 抢购加息
    if float(total_fee) <= 10000 and float(total_fee) + float(calculate_percentage(product_id)) + 0.1 >= float(pro.total_mount):
        qg_rate += 0.01
        # total_fee = float(pro.total_mount) - float(calculate_percentage(product_id))
        # pro.product_status = "3"

# -----------------------------end使用红包------------------------------------

    inv = Invest_info(member_id=str(m.id).replace('-',''), money=total_fee, hongbao=red_pocket_val,\
                      member_name=m.name, hongbao_source=hongbao_source)

    total_fee_all = float(total_fee) + red_pocket_val

    if Member_invite_info.query.filter_by(invited_id=str(m.id).replace('-','')).first():
        inv.yaoqing_money = round(float(total_fee)*0.01*float(pro.time_limit)/360.0, 2)

    # 默认为投资中
    inv.status = 1
    inv.product_id = product_id
    inv.is_effect = 1
    if hongbao_info_id:
        inv.hongbao_info_id = hongbao_info_id
    # 会员加息
    if m.level == 1:
        qg_rate += 0.01

    # 计算总收益
    pro_fit = round(float(total_fee) + red_pocket_val + float(float(total_fee)*(float(pro.rate)+float(pro.rate_increase)+qg_rate)*float(pro.time_limit)/360.0),2)
    # 普通收益
    inv.interest = round(float(total_fee)*float(pro.rate)*float(pro.time_limit)/360.0, 2)
    # 活动收益
    inv.activity_interest = round(float(total_fee)*(float(pro.rate_increase)+qg_rate)*float(pro.time_limit)/360.0, 2)

    order = Order_dict.query.filter_by(is_use = False).first()
    now_time = datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M:%S')
    inv.profit = pro_fit
    inv.time = datetime.now()
    inv.expect_time = inv.time + timedelta(days=int(pro.time_limit))
    inv.order_id = order.order_id
    inv.bluuid = m.bluuid
    inv.rate_security = rate_security
    inv.extra_rate = qg_rate
    mlogin = Member_login.query.filter(Member_login.member_id==m.id).order_by(Member_login.last_time.desc()).first()
    if mlogin:
        inv.equipment = mlogin.equipment_name
    else:
        inv.equipment = 'app'
    inv.channel = m.channel_id

    if asset.rechargeamount >= float(total_fee):
        asset.rechargeamount = float(asset.rechargeamount)-float(total_fee)
    else:
        asset.remainamount = asset.remainamount + asset.rechargeamount-float(total_fee)
        asset.rechargeamount = 0.0

    asset.freezeamount = float(asset.freezeamount) + float(total_fee) + red_pocket_val
    balance = asset.remainamount + asset.rechargeamount

    try:

        order.is_use=True
        db.session.merge(order)

        if (red_pocket_val > 0.0 or is_rate_pocket_val) and rp:
            rp.is_freeze = True
            rp.product_id = product_id
            db.session.merge(rp)

        db.session.add(inv)
        db.session.commit()

        db.session.merge(asset)

        db.session.merge(pro)



        type = u"投资"
        info = u"冻结账户余额 %s" % total_fee
        ins = Member_income_statement(member_id=str(m.id).replace('-',''), type=type, money=total_fee, \
                                      balance=balance, time=now_time, info=info, order_id=order.order_id,\
                                      product_info=pro.product_name, phone=m.phone)
        db.session.add(ins)

        if red_pocket_val > 0.0:
            type = u"红包"
            info = u"冻结红包金额 %s" % red_pocket_val
            ins = Member_income_statement(member_id=str(m.id).replace('-',''), type=type, money=red_pocket_val, \
                                          balance=balance, time=now_time, info=info, order_id=order.order_id,\
                                          product_info=rpt.name,phone=m.phone)
            db.session.add(ins)
        db.session.commit()

        tem_id = 80335
        query_res = Member_real_info.query.join(Member).filter(
            or_(Member.name == name_or_phone, Member.phone == name_or_phone)).first()

        sex = str(query_res.sex)
        if sex == 'M':
            datas = [query_res.real_name[0:1].encode("utf-8") + u'先生']
        elif sex == 'F':
            datas = [query_res.real_name[0:1].encode("utf-8") + u'女士']
        else:
            datas = [query_res.real_name[0:1].encode("utf-8") + u'先生/女士']
        send_message(m.phone, datas, tem_id)
        response_data['order_id'] = inv.order_id

        #-------------------------------活动区域-------------------------------------
        try:
            huodong(is_new_product, total_fee_all, name_or_phone, pro.time_limit)
        except Exception, e:
            print e
        #-------------------------------活动结束-------------------------------------
        try:
            url = AUTO_PRODUCT_URL + '/jeecg/tjtyyBorrowController.do?getAutoRun&productid=' + str(product_id)
            requests.get(url)
        except Exception:
            pass
        response_data["code"] = u"10000"
        response_data["desc"] = u"数据库操作成功"
        response_data["content"] = {}
        return toolkit.response(response_data, 200, None, True)

    except Exception, e:
        error = Error_log(phone=name_or_phone, type=u'下订单', description=str(e), creat_time=datetime.now())
        db.session.add(error)
        db.session.commit()

        response_data["code"] = u"10004"
        response_data["content"] = u"数据库操作失败"
        response_data["content"] = {}
        return toolkit.response(response_data, 200, None, True)


# 退单（用户下单成功，但是没有调新网接口）
@app.route("/v1/product/invest/chargeback/<order_id>", methods=['GET', 'POST'])
def chargeback(order_id):
    response_data = {}
    response_data["code"] = u"10000"
    response_data["desc"] = u"调用成功"
    response_data["content"] = {}

    try:
        false_order = Invest_info.query.filter(Invest_info.order_id == order_id).first()
        if false_order is None:
            response_data["code"] = u"10002"
            response_data["desc"] = u"订单不存在"
            return toolkit.response(response_data, 200, None, True)
        elif false_order.is_effect == 0:
            false_member_asset = Member_asset_info.query.filter(Member_asset_info.member_id == false_order.member_id).first()
            if false_member_asset is None:
                response_data["code"] = u"10003"
                response_data["desc"] = u"用户财富账户信息异常"
                return toolkit.response(response_data, 200, None, True)
            else:
                if false_member_asset.freezeamount >= false_order.money:
                    false_member_asset.freezeamount -= false_order.money
                    false_member_asset.remainamount += false_order.money
                    false_order.is_effect = 2
                    db.session.merge(false_member_asset)
                    db.session.merge(false_order)
                    db.session.commit()
                    response_data["content"]["result"] = u"冻结金额%0.2f已退回账户余额" % false_order.money
                    response_data["content"]["is_effect"] = false_order.is_effect
                else:
                    response_data["code"] = u"10004"
                    response_data["desc"] = u"账户冻结金额小于退单金额"
                    return toolkit.response(response_data, 200, None, True)
        else:
            response_data["code"] = u"10005"
            response_data["desc"] = u"订单状态不符合退单要求"
            return toolkit.response(response_data, 200, None, True)
    except:
        response_data["code"] = u"10001"
        response_data["desc"] = u"发生未知异常"
        return toolkit.response(response_data, 200, None, True)

    return toolkit.response(response_data, 200, None, True)


@app.route('/v1/product/uploads/image/<phone>',methods=['GET', 'POST'])
def some_uploads(phone):
    response_data = {}
    yijian_imageurl = request.form.get('yijianUrl',None)
    touxiang_imageurl = request.form.get('touxiangUrl',None)
    r = str(randint(10000000,99999999))

    if yijian_imageurl:
        try:
            path = getcwd() + '/media/yijian/images/' + phone + '_' + r + '.png'
            urllib.urlretrieve(yijian_imageurl, path)
            response_data["code"] = u"10000"
            response_data["content"] = u"操作成功"
            return toolkit.response(response_data, 200, None, True)
        except:
            pass
    elif touxiang_imageurl:
        try:
            path = getcwd() + '/media/touxiang/images/' + phone + '_' + r + '.png'
            urllib.urlretrieve(touxiang_imageurl, path)
            response_data["code"] = u"10000"
            response_data["content"] = u"操作成功"
            return toolkit.response(response_data, 200, None, True)
        except Exception, e:
            print '======='
            print e
            print '======='
    response_data["code"] = u"10004"
    response_data["content"] = u"操作失败"
    return toolkit.response(response_data, 200, None, True)


@app.route('/v1/product/order/dianzipingzheng/<order_id>')
def dianzipingzheng(order_id):
    renderData = {}
    query_top = db.session.query(Invest_info, Member_real_info.real_name,  Member_real_info.real_identid)
    qus = query_top.filter(and_(Invest_info.order_id == order_id, Member_real_info.member_id == Invest_info.member_id)).first()

    renderData['real_name'] = qus.real_name if qus else ''
    renderData['real_identid'] = qus.real_identid
    renderData['time'] = qus[0].time
    return render_template('/product/dianzipingzheng.html', renderData=renderData)


@app.route('/v1/product/borrow/demo')
def borrow_demo():
    renderData = {}
    return render_template('/product/borrow.html', renderData=renderData)


@app.route('/v1/product/borrow/demo/<order_id>')
def borrow_demo_order(order_id):
    renderData = {'order_id':order_id}
    invest_info = Invest_info.query.filter_by(order_id=order_id).first()
    if invest_info:
        borrow = Product_info.query.filter_by(id=invest_info.product_id).first()
        member_real_info = Member_real_info.query.filter_by(member_id=invest_info.member_id).first()
        borrower_info = Borrower_info.query.filter_by(id=borrow.borrow_id).first()
        member = Member.query.filter_by(id=invest_info.member_id).first()
        renderData['real_name'] = member_real_info.real_name
        renderData['id_card'] = member_real_info.real_identid
        renderData['borrower_name'] = borrower_info.borrower_name
        renderData['borrower_idcard'] = check_idcard(borrower_info.id_card)
        renderData['borrow_use'] = borrower_info.borrow_use
        renderData['rate'] = check_rate(member,float(borrow.rate * 100))
        renderData['limit_mount'] = borrow.total_mount
        renderData['Limit_Mount'] = cncurrency(int(borrow.total_mount),capital=True,classical=True)
        renderData['muji_limit'] = (borrow.interest_time - borrow.audit_time).days if (borrow.interest_time - borrow.audit_time).days != 0 else 1
        renderData['dingdan_id'] = borrow.product_name
        renderData['phone'] = member.phone
        renderData['invest_money'] = invest_info.money
        renderData['end_time'] = borrow.end_time

        xiadan_time = invest_info.time
        renderData['xiadan_time'] = xiadan_time
        renderData['year'] = xiadan_time.year
        renderData['month'] = xiadan_time.month
        renderData['day'] = xiadan_time.day

        borrow_interest_time = borrow.interest_time
        renderData['borrowStart_year'] = borrow_interest_time.year
        renderData['borrowStart_month'] = borrow_interest_time.month
        renderData['borrowStart_day'] = borrow_interest_time.day

        renderData['end_year'] = borrow.end_time.year
        renderData['end_month'] = borrow.end_time.month
        renderData['end_day'] = borrow.end_time.day
        renderData['borrowtime_limit'] = borrow.time_limit
    return render_template('/product/borrow.html', renderData=renderData)
