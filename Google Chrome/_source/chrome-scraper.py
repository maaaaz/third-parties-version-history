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

from lxml.html.soupparser import fromstring
import requests

# Script version
VERSION = '1.1'

# Options definition
parser = argparse.ArgumentParser(description="version: " + VERSION)
parser.add_argument('-o', '--output-file', help='Output csv file (default ./chrome.csv)', default=path.abspath(path.join(os.getcwd(), './chrome.csv')))

    
def from_wikipedia():
    root = fromstring(requests.get('https://en.wikipedia.org/wiki/Google_Chrome_version_history').content)
    trs = root.findall('.//tbody/tr')
    p_version = re.compile('(?P<version>\d{1,2}\.[0-9.]*)', re.IGNORECASE)
    
    for entry in trs:
        release = entry.xpath('string(td[1])').strip()
        
        # split-trick to keep only the first date occurence, the other ones are details per OS
        date = entry.xpath('string(td[2]/text())').strip().split(' ',2)[0]
        
        version_entry = p_version.search(release)
        if version_entry and date:
            release = version_entry.group('version')
            
            chrome = {}
            datetime_obj = datetime.datetime.strptime(date, "%Y-%m-%d")
            chrome['date'] = datetime_obj.date().isoformat()
        
            yield release, chrome

def from_chocolatey():
    root = fromstring(requests.get('https://chocolatey.org/packages/GoogleChrome').content)
    trs = root.findall('.//tr')
    p_version = re.compile('(?P<version>\d{2}\.[0-9.]*)', re.IGNORECASE)
    
    for entry in trs:
        date = entry.xpath('string(td[4])').strip()
        release = entry.xpath('string(td[2]/a|td[2]/span)')
        
        version_entry = p_version.search(release)
        if version_entry and date:
            release = version_entry.group('version')
            
            chrome = {}
            format_str = "%A, %B %d, %Y"
            datetime_obj = datetime.datetime.strptime(date, format_str)
            chrome['date'] = datetime_obj.date().isoformat()
        
            yield release, chrome
    
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
    sources = [ ('wikipedia', from_wikipedia()), 
                ('chocolatey', from_chocolatey()) ]
    
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