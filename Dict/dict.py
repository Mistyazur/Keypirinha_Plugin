import keypirinha as kp
import keypirinha_util as kpu
import keypirinha_net as kpnet

import os
import re
import time
import json
import threading
import traceback
import urllib.error
import urllib.parse
import winsound

from bs4 import BeautifulSoup
from .lib import mp3play


USER_AGENT = 'Mozilla/5.0 (iPad; CPU OS 11_0 like Mac OS X) AppleWebKit/604.1.34 (KHTML, like Gecko) Version/11.0 Mobile/15A5341f Safari/604.1'

class Dict(kp.Plugin):

    ITEMCAT_SUGGESTION      = kp.ItemCategory.USER_BASE + 1
    ITEMCAT_PRONUNCIATION   = kp.ItemCategory.USER_BASE + 2
    ITEMCAT_DEFINE          = kp.ItemCategory.USER_BASE + 3
    ITEMCAT_DEFINE_DETAIL   = kp.ItemCategory.USER_BASE + 4

    def __init__(self):
        super().__init__()

    def on_start(self):
        # Create directory for audio file
        self._cache_dir = kp.package_cache_dir() + '\\Dict\\'
        if not os.path.exists(self._cache_dir):
            os.makedirs(self._cache_dir)

    def on_catalog(self):
        self.set_catalog([
            self.create_item(
            category=kp.ItemCategory.KEYWORD,
            label='Dict',
            short_desc='English dictionary',
            target='Dict',
            args_hint=kp.ItemArgsHint.REQUIRED,
            hit_hint=kp.ItemHitHint.NOARGS
            )
        ])

    def on_suggest(self, user_input, items_chain):
        if not items_chain:
            return
        
        if self.should_terminate(0.25):
            return
        
        last_item = items_chain[-1]
        category = last_item.category()

        if category == kp.ItemCategory.KEYWORD:
            input_text = user_input.strip()
            suggestions = self.query_suggestion(input_text)
            if suggestions:
                self.set_suggestions([
                    self.create_item(
                    category=self.ITEMCAT_SUGGESTION,
                    label=k,
                    short_desc=v,
                    target=k,
                    args_hint=kp.ItemArgsHint.REQUIRED,
                    hit_hint=kp.ItemHitHint.IGNORE
                ) for k, v in suggestions.items()
                ])
        elif category == self.ITEMCAT_SUGGESTION:
            definition = last_item.data_bag()
            if definition:
                definition = eval(definition)
            else:
                definition = self.query_definition(last_item.label())
                if definition:
                    last_item.set_data_bag(str(definition))

            suggestions = []

            pronunciation = definition.get('pronunciation')
            if pronunciation:
                suggestions.append(
                    self.create_item(
                    category=self.ITEMCAT_PRONUNCIATION,
                    label=pronunciation,
                    short_desc=definition.get('form', ''),
                    target=pronunciation,
                    args_hint=kp.ItemArgsHint.REQUIRED,
                    hit_hint=kp.ItemHitHint.IGNORE,
                    data_bag=definition.get('audio', None)
                ))

            define = definition.get('define')
            if define:
                for gender, define in define.items():
                    details = define.get('details', None)                      
                    suggestions.append(
                        self.create_item(
                        category=self.ITEMCAT_DEFINE,
                            label=gender + ' ' + define.get('main', ''),
                            short_desc=gender,
                            target=gender,
                            args_hint=kp.ItemArgsHint.REQUIRED,
                            hit_hint=kp.ItemHitHint.IGNORE,
                            data_bag='\n'.join(details) if details else None
                    ))

            self.set_suggestions(suggestions, kp.Match.FUZZY, kp.Sort.NONE)
        elif category == self.ITEMCAT_DEFINE:
            details = last_item.data_bag()
            if details:
                details = details.split('\n')
                self.set_suggestions([
                    self.create_item(
                        category=self.ITEMCAT_DEFINE,
                            label=detail,
                            short_desc='',
                            target=detail,
                            args_hint=kp.ItemArgsHint.FORBIDDEN,
                            hit_hint=kp.ItemHitHint.IGNORE,
                    ) for detail in details
                ], kp.Match.FUZZY, kp.Sort.NONE)
        elif category == self.ITEMCAT_PRONUNCIATION:
            audio = last_item.data_bag()
            if audio:
                if audio[:4] == 'http':
                    audio_path = self._cache_dir + 'pronunce.mp3'
                    opener = urllib.request.build_opener()
                    with opener.open(audio) as conn, open(audio_path, 'w+b') as audio_file:
                        data = conn.read()
                        if data:
                            audio_file.write(data)
                            audio = audio_path

                            item = items_chain[-2]
                            definition = item.data_bag()
                            definition = eval(definition) if definition else None
                            if definition:
                                definition['audio'] = audio
                                item.set_data_bag(str(definition))

                if os.path.isfile(audio):
                    clip = mp3play.load(audio)
                    clip.play()
                    time.sleep(clip.seconds())

    def on_execute(self, catalog_item, action):
        pass

    def on_activated(self):
        pass

    def on_deactivated(self):
        pass

    def on_events(self, flags):
        pass

    @staticmethod
    def query_suggestion(word):
        dicts = {}
        query = {
            'word': word,
            'nums': len(word) 
        }

        try:
            query = urllib.parse.urlencode(query)
            opener = urllib.request.build_opener()
            opener.addheaders = [('User-agent', 'Mozilla/5.0 (iPad; CPU OS 11_0 like Mac OS X) AppleWebKit/604.1.34 (KHTML, like Gecko) Version/11.0 Mobile/15A5341f Safari/604.1')]
            url = 'http://dict.iciba.com/dictionary/word/suggestion?{}'.format(query)
            with opener.open(url) as conn:
                response = conn.read().decode(encoding='utf-8', errors='strict')
                data = json.loads(response)
                message = data['message']
                for msg in message:
                    dicts[msg['key']] = msg['paraphrase']
        except:
            print('json error')
            dicts = {}

        return dicts

    @staticmethod
    def query_definition(word):
        result = {}
        is_cn_word = True if re.match('[\u4e00-\u9fa5]+', word) else False
        query = {'q': word}
        query = urllib.parse.urlencode(query)
        opener = urllib.request.build_opener()
        # opener.addheaders = [('user-agent', USER_AGENT)]
        with opener.open('https://cn.bing.com/dict/search?{}'.format(query)) as conn:
            response = conn.read().decode(encoding='utf-8', errors='strict')
            soup = BeautifulSoup(response, 'html.parser')
            define_block = pr = soup.find('div', class_='qdef')
            if not define_block:
                return result

            # Pronunciation
            pronunciation = ''
            pr = define_block.find('div', class_='hd_pr')
            pr_us = define_block.find('div', class_='hd_prUS')
            if pr:
                pronunciation += pr.get_text().strip()
            if pr_us:
                pronunciation = pronunciation + ' ' + pr_us.get_text().strip()
            if pronunciation:
                pronunciation = pronunciation.replace('英\xa0', 'en: ')
                pronunciation = pronunciation.replace('美\xa0', 'us: ')
                result['pronunciation'] = pronunciation

            # Audio
            audio = define_block.find('div', class_='hd_tf')
            if audio:
                match = re.search('https://.*mp3', audio.a.attrs['onclick'])
                if match:
                    result['audio'] = match[0]

            # Form
            form = define_block.find('div', class_='hd_if')
            if form:
                result['form'] = form.get_text().replace('\xa0', ' ')

            define_details = {}
            define_details_block = define_block.find('div', {'id' : 'crossid' if is_cn_word else 'homoid'})
            if define_details_block:
                define_details_block = define_details_block.find_all('tr', {'class' : 'def_row df_div1'})
                for define_details_iter in define_details_block:
                    define_details_gender = define_details_iter.find('div', {'class' : 'pos pos1'})
                    if define_details_gender:
                        define_details_gender = define_details_gender.get_text().strip()
                        define_details_defines = define_details_iter.find_all('div', {'class' : 'de_li1 de_li3'})
                        define_details[define_details_gender] = [
                            define_details_define.get_text().strip() for define_details_define in define_details_defines if define_details_define.parent['class'] == ['def_fl']
                        ]
            # print(define_details_dict)

            define = {}
            define_main_block = define_block.find('ul')
            if define_main_block:
                define_main_block = define_main_block.find_all('li')
                for define_main_iter in define_main_block:
                    define_main_gender = define_main_iter.find('span', class_='pos')
                    define_main_define = define_main_iter.find('span', class_='def b_regtxt')
                    if define_main_gender and define_main_define:
                        define_main_gender = define_main_gender.get_text().strip()
                        define_main_define = define_main_define.get_text().strip()
                        define[define_main_gender] = {
                            'main': define_main_define,
                            'details': define_details.get(define_main_gender, None)
                        }
                        
            # print(define)
            if define:
                result['define'] = define

        return result
