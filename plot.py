#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
import base64
import io

import matplotlib
import matplotlib.dates as mdates
from dateutil import tz

matplotlib.use('agg')
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import style
from flask import Flask, request
from datetime import datetime, timedelta

app = Flask(__name__)

style.use('ggplot')


@app.route("/")
def plot():
    xstart = request.args.get('start')
    xend = request.args.get('end')
    x, z, y = np.genfromtxt('results.csv', skip_header=1,
                            unpack=True, encoding=None,
                            delimiter=";", dtype=str)

    x = mdates.datestr2num(x)
    y = np.array(np.char.replace(y, ',', ''), dtype=int)
    z = np.array(np.char.replace(z, ',', ''), dtype=int)

    fig, ax = plt.subplots()
    ax.plot(x, y, 'b')
    ax.set_ylabel('Minuten', color='b')

    ax2 = ax.twinx()
    ax2.plot(x, z, 'r')
    ax2.set_ylabel('Episoden', color='r')

    vor_24h = datetime.utcnow() - timedelta(days=1)
    if xstart is not None:
        xstart = mdates.datestr2num(xstart)
        ax.set_xlim(left=xstart)
    else:
        xstart = mdates.date2num(vor_24h)
        ax.set_xlim(left=xstart)
    if xend is not None:
        xend = mdates.datestr2num(xend)
        ax.set_xlim(right=xend)

    ax.set_ylim(bottom=0)
    ax2.set_ylim(bottom=0)

    plt.title('Podcastminuten')
    plt.xlabel('Datum')
    xfmt = mdates.DateFormatter('%Y-%m-%d %H:%M:%S')
    ax.xaxis.set_major_formatter(xfmt)

    fig.autofmt_xdate()

    img = io.BytesIO()
    plt.plot(x, y)
    plt.savefig(img, format='png')
    img.seek(0)

    plot_url = base64.b64encode(img.getvalue()).decode()

    today = datetime.utcnow().date()
    start_of_day = datetime(today.year, today.month, today.day, tzinfo=tz.tzutc())
    now = datetime.utcnow()
    end_of_day = start_of_day + timedelta(days=1)
    start_of_week = start_of_day - timedelta(days=start_of_day.weekday())
    end_of_week = start_of_week + timedelta(days=7)
    start_of_month = start_of_day.replace(day=1)
    next_month = start_of_day.replace(day=28) + timedelta(days=4)
    end_of_month = next_month - timedelta(days=(next_month.day - 1))
    start_of_year = start_of_day.replace(day=1, month=1)
    end_of_year = start_of_day.replace(day=1, month=1, year=start_of_day.year + 1)

    return """<html><body>
    <h1>Podcastzeiten</h1>
    <p>
        <a href="?start={}&end={}">24h</a>
        <a href="?start={}&end={}">Heute</a>
        <a href="?start={}&end={}">Diese Woche</a>
        <a href="?start={}&end={}">Dieser Monat</a>
        <a href="?start={}&end={}">Dieses Jahr</a>
        <a href="?start={}">Seit Anbeginn der Zeit</a>
    </p>
    <img src="data:image/png;base64,{}">""".format(vor_24h.isoformat(), now.isoformat(),
                                                   start_of_day.isoformat(), end_of_day.isoformat(),
                                                   start_of_week.isoformat(), end_of_week.isoformat(),
                                                   start_of_month.isoformat(), end_of_month.isoformat(),
                                                   start_of_year.isoformat(), end_of_year.isoformat(),
                                                   mdates.num2date(x[0]).isoformat().replace('+00:00', ''),
                                                   plot_url)
