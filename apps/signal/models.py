#!/use/bin/env python
# -*- coding: UTF-8 -*-

import uuid
from apps.dbinstance import db


# 活动分类表
class New_activity_sort(db.Model):

    __tablename__ = "tjtyy_new_activity_sort"

    id = db.Column(db.Integer, primary_key=True)
    activity_name = db.Column(db.String(50))  # 活动名称
    activity_type = db.Column(db.String(36))  # 活动类型
    start_time = db.Column(db.DateTime)  # 活动开始时间
    end_time = db.Column(db.DateTime)  # 活动结束时间
    score = db.Column(db.Integer)  # 参加一次活动得分


# 用户积分表
class New_activity_member_score(db.Model):

    __tablename__ = "tjtyy_new_activity_member_score"

    id = db.Column(db.Integer, primary_key=True)
    phone = db.Column(db.String(50))  # 用户手机号
    score_total = db.Column(db.Integer)  # 积分总数


# 积分记录表
class New_activity_score_record(db.Model):

    __tablename__ = "tjtyy_new_activity_score_record"

    id = db.Column(db.Integer, primary_key=True)
    phone = db.Column(db.String(50))  # 用户手机号
    activity_id = db.Column(db.String(36))  # 活动ID
    create_time = db.Column(db.DateTime)  # 创建时间
    score = db.Column(db.Integer)  # 得分


# 奖品信息表
class New_activity_prize_info(db.Model):

    __tablename__ = "tjtyy_new_activity_prize_info"

    id = db.Column(db.String(36), primary_key=True)  # 奖品ID
    prize_name = db.Column(db.String(50))  # 奖品名称
    amount = db.Column(db.Integer)  # 库存


# 积分奖励表
class New_activity_score_reward(db.Model):

    __tablename__ = "tjtyy_new_activity_score_reward"

    id = db.Column(db.String(36), primary_key=True)
    score_rank = db.Column(db.Integer)  # 积分等级
    prize_id = db.Column(db.String(36))  # 奖品id


# 奖品发放记录表
class New_activity_prize_give_record(db.Model):

    __tablename__ = "tjtyy_new_activity_prize_give_record"

    id = db.Column(db.String(50), primary_key=True)
    member_id = db.Column(db.String(50))  # 用户ID
    prize_id = db.Column(db.String(36))  # 奖品ID
    create_time = db.Column(db.DateTime)  # 创建时间