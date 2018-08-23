#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import requests
import json
from datetime import datetime, timedelta
from apps import app
from flask import render_template, request


@app.route("/", methods=['GET','POST'])
def pc_index():
    render_data = {}
    return render_template('pc/index.html', render_data=render_data)
