#!/use/bin/env python
# -*- coding: UTF-8 -*-


from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import SQLAlchemyError
from utils.uuidgen import GUID
from flask_redis import FlaskRedis

db = SQLAlchemy()
db.GUID = GUID

class DbOperation():

    def session_commit(self):
        try:
            db.session.commit()
        except SQLAlchemyError as e:
            db.session.rollback()
            reason = str(e)
            return reason

    def add(self, resource):
        db.session.add(resource)
        return self.session_commit()

    def read(self):
        return self.query.all()

    def update(self):
        return self.session_commit()

    def delete(self, resource):
        db.session.delete(resource)
        return self.session_commit()

redis = FlaskRedis()
