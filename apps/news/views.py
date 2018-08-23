#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from apps import app
from config import BOLUO_URL
from sqlalchemy import and_
from flask import request
from models import News, Sort
from apps.utils import toolkit


@app.route("/v1/banner/url", methods=['GET', 'POST'])
def get_banner_url():

    base_url = "https://m.boluolc.com"
    query_res = News.query.join(Sort, Sort.id == News.sortid).filter(and_(Sort.label == "banner", \
                                Sort.metakeyword == "banner")).order_by(News.posttime.desc()).limit(5).all()
    response_data = {}
    response_data["code"] = u"10000"
    response_data["des"] = u"请求成功"
    response_data["content"] = []
    for item in query_res:
        img_url = base_url + item.image
        response_data["content"].append(dict(img=img_url, url=item.content))
    return toolkit.response(response_data, 200, None, True) 

@app.route("/v1/news/notice", methods=['GET', 'POST'])
def get_notice_url():

    base_url = "https://m.boluolc.com/index.php/home/news/newdetail/id/"
    query_res = News.query.join(Sort, Sort.id == News.sortid).filter(and_(Sort.label == "notice", \
                                Sort.metakeyword == "announcement")).order_by(News.posttime.desc()).limit(5).all()
    response_data = {}
    response_data["code"] = u"10000"
    response_data["des"] = u"请求成功"
    response_data["content"] = []
    for item in query_res:
        url = base_url + str(item.id).replace("-", "")
        response_data["content"].append(dict(title=item.title, url=url))
    return toolkit.response(response_data, 200, None, True) 


@app.route("/v1/news/notice/all", methods=['GET', 'POST'])
def get_notice_all():

    base_url = "https://m.boluolc.com/index.php/home/news/newdetail/id/"
    query_res = News.query.join(Sort, Sort.id == News.sortid).filter(and_(Sort.label == "notice", \
                                Sort.metakeyword == "announcement")).order_by(News.posttime.desc()).all()
    response_data = {}
    response_data["code"] = u"10000"
    response_data["des"] = u"请求成功"
    response_data["content"] = []
    for item in query_res:
        url = base_url + str(item.id).replace("-", "")
        response_data["content"].append(dict(title=item.title, posttime=str(item.posttime), url=url))
    return toolkit.response(response_data, 200, None, True) 


@app.route("/v1/news/media/top3", methods=['GET', 'POST'])
def get_media_top3():

    base_url = "https://m.boluolc.com/index.php/home/news/newdetail/id/"
    query_res = News.query.join(Sort, Sort.id == News.sortid).filter(and_(Sort.label == "news", \
                                Sort.metakeyword == "report")).order_by(News.posttime.desc()).limit(3).all()
    response_data = {}
    response_data["code"] = u"10000"
    response_data["des"] = u"请求成功"
    response_data["content"] = []
    for item in query_res:
        url = base_url + str(item.id).replace("-", "")
        id = str(item.id).replace("-","")
        response_data["content"].append(dict(title=item.title, posttime=str(item.posttime)[:10], url=url,id=id, image=str(item.image)))
    return toolkit.response(response_data, 200, None, True)

@app.route("/v1/news/media/all", methods=['GET', 'POST'])
def get_media_all():

    base_url = "https://m.boluolc.com/index.php/home/news/newdetail/id/"
    query_res = News.query.join(Sort, Sort.id == News.sortid).filter(and_(Sort.label == "news", \
                                Sort.metakeyword == "report")).order_by(News.posttime.desc()).all()
    response_data = {}
    response_data["code"] = u"10000"
    response_data["des"] = u"请求成功"
    response_data["content"] = []
    for item in query_res:
        url = base_url + str(item.id).replace("-", "")
        response_data["content"].append(dict(title=item.title, posttime=str(item.posttime)[:10], url=url, image=BOLUO_URL + str(item.image)))
    return toolkit.response(response_data, 200, None, True)

@app.route("/v1/news/<label>/<metakeyword>/<page_num>/<page_total>", methods=['GET','POST'])
def get_news(label, metakeyword, page_num, page_total):

    response_data = {}
    if page_num is None:
        page_num = 1
    else:
        pnum = int(page_num.encode('ascii'))

    if page_total is None:
        page_total = 10
    else:
        page_total = int(page_total.encode('ascii'))

    pnum = (pnum-1) *page_total
    if label is None or metakeyword is None:
        response_data["code"] = u"1"
        response_data["content"] = u"请求的新闻不存在"
        return toolkit.response(response_data, 200, None, True)

    page_mount = pnum+page_total
    query_res = News.query.join(Sort, Sort.id == News.sortid).filter(and_(Sort.label == label, Sort.metakeyword == metakeyword)).all()[pnum:page_mount]
    return toolkit.query_result_json(query_res)


@app.route("/v1/news/sum/<label>/<metakeyword>", methods=['GET','POST'])
def get_news_sum(label, metakeyword):

    response_data = {}
    if label is None or metakeyword is None:
        response_data["code"] = u"1"
        response_data["content"] = u"请求的新闻不存在"
        return toolkit.response(response_data, 200, None, True)

    query_res = News.query.join(Sort, Sort.id == News.sortid).filter(and_(Sort.label == label, Sort.metakeyword == metakeyword)).all()

    response_data = {}
    response_data["code"] = u"0"
    response_data["count"] =unicode(len(query_res))
    return toolkit.response(response_data, 200, None, True)


@app.route("/v1/news/detail", methods=['GET', 'POST'])
def get_content():

    news_id = request.form.get('news_id', None)

    response_data = {}
    if news_id is None:
        response_data["code"] = u"1"
        response_data["content"] = u"请求的新闻不存在"
        return toolkit.response(response_data, 200, None, True)

    query_res = News.query.filter(News.id == news_id).all()
    return toolkit.query_result_json(query_res)
