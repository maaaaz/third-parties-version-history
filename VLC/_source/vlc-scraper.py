#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# This file is part of third-parties-version-history.
#
# Copyright (C) 2018, Thomas Debize <tdebize at mail.com>
# All rights reserved.
#
# third-parties-version-history is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# third-parties-version-history is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with third-parties-version-history.  If not, see <http://www.gnu.org/licenses/>.

from codecs import open
from os import path
import re
import csv
import os
import argparse
import datetime
import locale

from lxml.html.soupparser import fromstring
import requests

# Script version
VERSION = '1.1'

# Options definition
parser = argparse.ArgumentParser(description="version: " + VERSION)
parser.add_argument('-o', '--output-file', help='Output csv file (default ./vlc.csv)', default=path.abspath(path.join(os.getcwd(), './vlc.csv')))

    
def from_wikipedia():
    locale.setlocale(locale.LC_ALL, "fr_FR.utf8")
    
    root = fromstring(requests.get('https://fr.wikipedia.org/wiki/VLC_media_player').content)
    trs = root.findall('.//*[@id="mw-content-text"]/div/table[1]/tbody/tr')
    p_version = re.compile('(?P<version>\d{1,2}\.[0-9.]*)', re.IGNORECASE)
    
    for entry in trs:
        release = entry.xpath('string(td[1])').strip()
        
        version_entry = p_version.search(release)
        if version_entry:
            release = version_entry.group('version')
            vlc = {}
            # fuzzy search of date
            for i in [2,3]:
                date = entry.xpath("string(td[%s])" % i).strip().replace('1er','01')
                try:
                    datetime_obj = datetime.datetime.strptime(date, "%d %B %Y")
                    vlc = {}
                    vlc['date'] = datetime_obj.date().isoformat()
                    break
                except ValueError:
                    pass

            yield release, vlc
    
def scrape_and_merge(sources, results):
    for name, source in sources:
        count = 0
        for version, item in source:
            if version not in results:
                results[version] = item
                count = count + 1
                
        print("[+] %s entries collected from '%s'" % (count, name))
    
def scrape(opts):
    results = {}
    sources = [ ('wikipedia', from_wikipedia()) ]
    
    scrape_and_merge(sources, results)
    
    return results

    
def generate_csv(results, options):
    keys = ['version_full', 'date (yyyy-mm-dd)']
    
    if results:
        with open(options.output_file, mode='w', encoding='utf-8') as fd_output:
            spamwriter = csv.writer(fd_output, delimiter=';', quoting=csv.QUOTE_ALL, lineterminator='\n')
            spamwriter.writerow(keys)
            
            for version_full in sorted(results.keys(), key=lambda s: list(map(int, s.split('.')))):
                output_line = []
                item = results[version_full]
                output_line = [version_full, item['date']]
                spamwriter.writerow(output_line) 
    return
    
def main():
    """
        Dat main
    """
    global parser
    options = parser.parse_args()
    
    options.output_file = path.abspath(path.join(os.getcwd(), options.output_file)) if options.output_file else options.output_file
              
    results = scrape(options)
    generate_csv(results, options)
    
    return

if __name__ == "__main__" :
    main()