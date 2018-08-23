#coding=utf-8
from flask import session
from datetime import datetime
from apps.dbinstance import db
from apps.signal.models import New_activity_sort, New_activity_member_score, New_activity_score_record, New_activity_prize_info, New_activity_score_reward, New_activity_prize_give_record
from apps.asset.models import Member_asset_info
from apps.activity.models import Sign_record
from apps.signal import process_collection


def sign_process():
    try:
        k = Sign_record.__tablename__
        if 'changes' in session:
            if k in session['changes']:
                act_sort = New_activity_sort.query.filter_by(id='0').first()
                act_mem_score = New_activity_member_score.query.filter_by(phone=session['changes'][k]['content']['phone']).first()
                if not act_mem_score and act_sort:
                    mem_score = New_activity_member_score(phone=session['changes'][k]['content']['phone'],
                                                          score_total=act_sort.score)
                    score_record = New_activity_score_record(phone=session['changes'][k]['content']['phone'],
                                                             activity_id=act_sort.id, create_time=datetime.now(),
                                                             score=act_sort.score)
                    db.session.add(mem_score)
                    db.session.add(score_record)
                    db.session.commit()
                elif act_mem_score and act_sort:
                    act_mem_score.score_total = act_mem_score.score_total + act_sort.score
                    score_record = New_activity_score_record(phone=session['changes'][k]['content']['phone'],
                                                             activity_id=act_sort.id, create_time=datetime.now(),
                                                             score=act_sort.score)
                    db.session.merge(act_mem_score)
                    db.session.add(score_record)
                    db.session.commit()
    except:
        pass


process_collection[Sign_record.__tablename__] = sign_process
