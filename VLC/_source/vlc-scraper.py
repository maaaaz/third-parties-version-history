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
import pprint

from lxml.html.soupparser import fromstring
import requests

# Script version
VERSION = '1.2'

# Options definition
parser = argparse.ArgumentParser(description="version: " + VERSION)
parser.add_argument('-o', '--output-file', help='Output csv file (default ./vlc.csv)', default=path.abspath(path.join(os.getcwd(), './vlc.csv')))

def from_digital_digest():
    root = fromstring(requests.get('http://www.digital-digest.com/software/videolan_history.html').content)
    trs = root.findall('.//div[@class="softwareDescription"]/ul/li/a')
    p_version = re.compile('Version (?P<version>[0-9.]*) \((?P<date>(.*))\)', re.IGNORECASE)
    
    for entry in trs:
        release_and_date = p_version.match(entry.text_content())
        if release_and_date:
            vlc = {}
            release = release_and_date.group('version')
            date = release_and_date.group('date')
            datetime_obj = datetime.datetime.strptime(date, "%b %d, %Y").date().isoformat()
            vlc['date'] = datetime_obj
            
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
    sources = [ ('digital_digest', from_digital_digest()) ]
    
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
                output_line = [version_full, item['date'] if 'date' in item else '']
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