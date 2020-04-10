#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

import datetime
import re
import os
import requests

from influxdb import InfluxDBClient
from functools import reduce
from html.parser import HTMLParser
from dotenv import load_dotenv

load_dotenv()

session = requests.Session()


def login():
    # Request
    # POST https://overcast.fm/login

    try:
        response = session.post(
            url="https://overcast.fm/login",
            headers={
                "Content-Type": "application/x-www-form-urlencoded; charset=utf-8",
            },
            data={
                "email": os.environ.get("OVERCAST_EMAIL"),
                "password": os.environ.get("OVERCAST_PASS"),
            },
        )
        if response.status_code == 302:
            # erfolg, weitermachen
            return True
        else:
            # passwort falsch, return, warnung, oder so?
            return False
    except requests.exceptions.RequestException:
        print('HTTP Request failed')
        return False


def load_podcasts():
    try:
        response = session.get(
            url="https://overcast.fm/podcasts",
        )
        if response.status_code != 200:
            return None
        return response.content.decode('utf-8')
    except requests.exceptions.RequestException:
        print('HTTP Request failed')
        return None


def publish_influx(episode_count, duration):
    json_body = [
        {
            "measurement": "podcast_count",
            "time": datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
            "fields": {
                "episodes": float(episode_count),
                "minutes": float(duration)
            }
        }
    ]

    client = InfluxDBClient(os.environ.get('INFLUX_HOST'), int(os.environ.get('INFLUX_PORT')),
                            os.environ.get('INFLUX_USER'), os.environ.get(
                                'INFLUX_PASS'), os.environ.get('INFLUX_DB'),
                            ssl=bool(os.environ.get('INFLUX_SSL')), verify_ssl=True)

    client.write_points(json_body)


class OCEpisode:
    podcast = None
    title = None
    duration = 0

    def __str__(self):
        return self.podcast + ": " + self.title + "(" + str(self.duration) + " Min)\n"

    def csv(self):
        return "\"" + self.podcast + "\";\"" + self.title + "\";" + str(self.duration)


class OCParser(HTMLParser):
    inEpisodeCell = False
    inTitleStack = False
    row = -1

    episodes = list()
    currentEpisode = None

    # HTML Parser Methods
    def handle_starttag(self, start_tag, attrs):
        classes = ""
        for attr, value in attrs:
            # print(attr + ": " + value)
            if attr == "class":
                classes = value

        if start_tag == "a":
            if "episodecell" in classes:
                self.inEpisodeCell = True
                return

        if start_tag == "div" and self.inEpisodeCell:
            if "titlestack" in classes:
                self.inTitleStack = True
                return

        if start_tag == "div" and self.inTitleStack:
            if "singleline" in classes:
                self.row += 1
                if self.row == 0:
                    self.currentEpisode = OCEpisode()

    def handle_data(self, data):
        if self.inEpisodeCell and self.inTitleStack:
            if self.row == 0:
                if self.currentEpisode.podcast is None:
                    self.currentEpisode.podcast = data
                else:
                    self.currentEpisode.podcast = self.currentEpisode.podcast + data
            elif self.row == 1:
                if self.currentEpisode.title is None:
                    self.currentEpisode.title = data
                else:
                    self.currentEpisode.title = self.currentEpisode.title + data
            elif self.row == 2:
                reg = re.compile("(\d+) min", re.IGNORECASE)
                res = reg.search(data)
                if res:
                    current_duration = res.group(1)
                    try:
                        self.currentEpisode.duration += int(current_duration)
                    except ValueError:
                        pass

    def handle_endtag(self, end_tag):
        if end_tag == "a" and self.inEpisodeCell:
            self.inEpisodeCell = False
            self.inTitleStack = False
            self.row = -1
            if self.currentEpisode is not None:
                self.currentEpisode.podcast = self.currentEpisode.podcast.strip()
                self.currentEpisode.title = self.currentEpisode.title.strip()
                self.episodes.append(self.currentEpisode)
                self.currentEpisode = None

    def handle_startendtag(self, start_end_tag, attrs):
        pass

    def error(self, message):
        pass


if __name__ == '__main__':
    parser = OCParser()
    login()
    page = load_podcasts()
    parser.feed(page)
    print("=== Statistik ===")
    print("Episodenzahl:\t" + str(parser.episodes.__len__()))
    duration = reduce((lambda x, y: x + y.duration), parser.episodes, 0)
    print("Gesamtdauer:\t" + str(duration) + " Minuten")

    with open(os.environ.get('OUTPUT_CSV_FILENAME'), "a") as file:
        dt = datetime.datetime.utcnow().replace(
            tzinfo=datetime.timezone.utc).isoformat()
        file.write(dt + ";" + str(parser.episodes.__len__()) +
                   ";" + str(duration) + "\n")

    publish_influx(parser.episodes.__len__(), duration)
