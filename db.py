#!/use/bin/env python
# -*- coding: UTF-8 -*-

from flask_script import Manager
from flask_migrate import Migrate, MigrateCommand
from run import app
from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy(app)
migrate = Migrate(app, db)
manager = Manager(app)
manager.add_command('db', MigrateCommand)

if __name__ == '__main__':
    manager.run()

