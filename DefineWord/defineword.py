import keypirinha as kp
import keypirinha_util as kpu
import keypirinha_net as kpnet

import os
import re
import time
import threading
import traceback
import urllib.error
import urllib.parse

from bs4 import BeautifulSoup
from .lib import mp3play


class DefineWord(kp.Plugin):
    """
    Define a word in english using bing
    """

    USER_AGENT = "Mozilla/5.0"
    URL_SUGGESTION = "https://cn.bing.com/wordfetch/as?q={}"
    URL_TRANSLATION = "https://cn.bing.com/wordfetch/search?q=define%20{}"

    ITEMCAT_SUGGESTION = kp.ItemCategory.USER_BASE + 1
    ITEMCAT_RESULT = kp.ItemCategory.USER_BASE + 2

    def __init__(self):
        super().__init__()

    def on_start(self):
        self._cache_dir = kp.package_cache_dir() + '\\DefineWord\\'
        if not os.path.exists(self._cache_dir):
            os.makedirs(self._cache_dir)

    def on_catalog(self):
        catalog = []
        item = self.create_item(
            category=kp.ItemCategory.KEYWORD,
            label="Define Word",
            short_desc="Get definition of words",
            target="Define Word",
            args_hint=kp.ItemArgsHint.REQUIRED,
            hit_hint=kp.ItemHitHint.NOARGS,
            icon_handle=None)
        catalog.append(item)
        self.set_catalog(catalog)

    def on_suggest(self, user_input, items_chain):
        if not items_chain:
            return
        
        if self.should_terminate(0.25):
            return
        
        category = items_chain[-1].category()
        if category == kp.ItemCategory.KEYWORD:
            input_text = user_input.strip()
            suggestions = self.query_suggestion(input_text)

            suggestion_items = []
            for suggestion in suggestions:
                suggestion_items.append(self.create_item(
                    category=self.ITEMCAT_SUGGESTION,
                    label=suggestion,
                    short_desc='',
                    target=suggestion,
                    args_hint=kp.ItemArgsHint.REQUIRED,
                    hit_hint=kp.ItemHitHint.IGNORE
                ))
            if suggestion_items:
                self.set_suggestions(suggestion_items, kp.Match.ANY, kp.Sort.NONE)
        elif category == self.ITEMCAT_SUGGESTION:
            result = re.match('([a-z]+(-[a-z]+)?) ', items_chain[-1].label(), re.I)
            if result:
                word = result[1]

                opener = urllib.request.build_opener()
                opener.addheaders = [('user-agent', 'Mozilla/5.0'), ('cookie', '_EDGE_S=ui=en-us')]
                with opener.open('https://cn.bing.com/dict/search?q={}'.format(word)) as conn:
                    response = conn.read().decode(encoding='utf-8', errors='strict')
                    soup = BeautifulSoup(response, "html.parser")

                    add_result = lambda l, d: self.create_item(
                            category=self.ITEMCAT_RESULT,
                            label=l,
                            short_desc=d,
                            target=l,
                            args_hint=kp.ItemArgsHint.FORBIDDEN,
                            hit_hint=kp.ItemHitHint.IGNORE
                        )

                    result_items = []

                    # Pronunciation
                    pr_us = soup.find("div", class_="hd_prUS")
                    pr = soup.find("div", class_="hd_pr")
                    if not pr_us or not pr:
                        return
                    pronunciation = pr_us.get_text() + pr.get_text()

                    # Form
                    form = soup.find("div", class_="hd_if")
                    form = form.get_text() if form else ''

                    result_items.append(add_result(pronunciation, form))

                    # meanings
                    define_homoid = soup.find("div", {"id" : "homoid"})
                    defines = define_homoid.find_all("tr", class_="def_row df_div1")
                    for define in defines:
                        catagory = define.find("div", class_="pos pos1")
                        catagory = catagory.get_text() if catagory else ''

                        meanings = define.find_all("div", class_="df_cr_w")
                        for meaning in meanings:
                            result_items.append(add_result(meaning.get_text(), catagory))

                    # Show result
                    if result_items:
                        self.set_suggestions(result_items, kp.Match.ANY, kp.Sort.NONE)

                    # Audio
                    audio = soup.find("div", class_="hd_tf")
                    result = re.search("https://.*mp3", audio.a.attrs["onclick"])
                    if result:
                        audio_path = self._cache_dir + 'pronunce.mp3'

                        audio_url = result[0]
                        with opener.open(audio_url) as conn, open(audio_path, 'w+b') as sound_file:
                            data = conn.read()
                            sound_file.write(data)

                        def play_sound(audio_path):
                            clip = mp3play.load(audio_path)
                            clip.play()
                            time.sleep(clip.seconds())
                            clip.stop()

                        # Play audio
                        t = threading.Thread(target=play_sound, args=(audio_path,))
                        t.setDaemon(True)
                        t.start()

    def on_execute(self, item, action):
        pass

    def on_activated(self):
        pass

    def on_deactivated(self):
        pass

    def on_events(self, flags):
        pass

    @staticmethod
    def query_suggestion(word):
        opener = urllib.request.build_opener()
        # opener.addheaders = [('user-agent', 'Mozilla/5.0'), ('cookie', 'ENSEARCH=BENVER=1;_EDGE_S=ui=en-us')]
        opener.addheaders = [('user-agent', 'Mozilla/5.0'), ('cookie', '_EDGE_S=ui=en-us')]
        with opener.open('https://cn.bing.com/AS/Suggestions?pt=page.bingdict&qry={}&cvid=04DCBA554D43461585E6B3A13AAAE741'.format(word)) as conn:
            response = conn.read().decode(encoding='utf-8', errors='strict')
            soup = BeautifulSoup(response, "html.parser")
            return [s.get_text() for s in soup.find_all('div', class_='sa_tm')]