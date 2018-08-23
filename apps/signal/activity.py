#coding=utf-8
from flask import request_finished, session
from flask_sqlalchemy import models_committed, before_models_committed
from apps import app
from apps.signal import process_collection


# @before_models_committed.connect_via(app)
def model_saved_before(app, changes, **extra):
    try:
        for k in process_collection:
            for cha in changes:
                if cha[0].__tablename__ == k:
                    if 'changes' not in session:
                        session['changes'] = {}
                    session['changes'][k] = {
                        'type': cha[1],
                        'finished': False,
                        'model_name': cha[0].__tablename__,
                        'content': {}
                    }
                    for kk, vv in cha[0].__dict__.items():
                        if not kk.startswith('_'):
                            session['changes'][k]['content'][kk] = vv
    except:
        pass


# @models_committed.connect_via(app)
def model_saved_after(app, changes, **extra):
    try:
        for k in process_collection:
            if 'changes' in session:
                for cha in changes:
                    if cha[0].__tablename__ == k:
                        if k in session['changes']:
                            session['changes'][k]['finished'] = True
                            for kk, vv in cha[0].__dict__.items():
                                if not kk.startswith('_') and kk not in session['changes'][k]['content']:
                                    session['changes'][k]['content'][kk] = vv
    except:
        pass


# @request_finished.connect_via(app)
def request_finished_process(app, response, **extra):
    try:
        if 'changes' in session:
            for k, v in process_collection.items():
                if k in session['changes']:
                    if session['changes'][k]['model_name'] == k and session['changes'][k]['finished'] is True:
                        v()
            del(session['changes'])
    except:
        pass
