import uuid

from apps.dbinstance import db

class Sort(db.Model):
    __tablename__ = "tjtyy_article_sort"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128))
    metakeyword = db.Column(db.String(128))
    label = db.Column(db.String(128))
    news_infos = db.relationship('News', backref="tjtyy_article_sort",lazy="dynamic")


class News(db.Model):
    __tablename__ = "tjtyy_article_content"

    id = db.Column(db.GUID, primary_key=True, default=uuid.uuid4)
    sortid = db.Column(db.Integer, db.ForeignKey("tjtyy_article_sort.id"))
    title = db.Column(db.String(128))
    image = db.Column(db.String(128))
    content = db.Column(db.Text)
    hits = db.Column(db.Integer)
    posttime = db.Column(db.DateTime)
    can_link = db.Column(db.Integer)
    end_time = db.Column(db.DateTime)




