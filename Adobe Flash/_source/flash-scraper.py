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
parser.add_argument('-o', '--output-file', help='Output csv file (default ./flash.csv)', default=path.abspath(path.join(os.getcwd(), './flash.csv')))

    
def from_adobe():
    root = fromstring(requests.get('https://helpx.adobe.com/flash-player/kb/archived-flash-player-versions.html').content)
    
    p_version_1 = re.compile('flash player (?P<version_full>[.0-9]*)', re.IGNORECASE)
    p_version_2 = re.compile('flash player (?P<version_full_1>[.0-9]*)\s+and (?P<version_full_2>[.0-9]*)', re.IGNORECASE)
    p_date = re.compile('.*released (?P<date>.*)\)', re.IGNORECASE)
    
    trs = root.findall('.//li')
    for entry in trs:
        release = entry.xpath('string(a/text())')
        date = entry.xpath('string(text())')
        
        date_entry = p_date.search(date)
        version_1_entry = p_version_1.search(release)
        version_2_entry = p_version_2.search(release)
        
        if date_entry and (version_1_entry or version_2_entry):
            flash = {}
            format_str = '%m/%d/%Y'
            datetime_obj = datetime.datetime.strptime(date_entry.group('date'), format_str)
            flash['date'] = datetime_obj.date().isoformat()
            
            if version_1_entry:
                version_full = version_1_entry.group('version_full')
                yield version_full, flash
            
            if version_2_entry:
                version_full_1 = version_2_entry.group('version_full_1')
                yield version_full_1, flash
                
                version_full_2 = version_2_entry.group('version_full_2')
                yield version_full_2, flash

def from_snapfiles():
    root = fromstring(requests.get('https://www.snapfiles.com/apphistory/flashplayer_history.html').content)
    trs = root.findall('.//*[@id="apphistory-container"]/h3')
    for entry in trs:
        date = entry.xpath('string(span/text())')
        release = entry.xpath('string(text())').strip()
        
        if release and date:
            flash = {}
            format_str = "%b %d, %Y"
            datetime_obj = datetime.datetime.strptime(date, format_str)
            flash['date'] = datetime_obj.date().isoformat()
        
            yield release, flash
    

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
    sources = [ ('adobe', from_adobe()), 
                ('snapfiles', from_snapfiles()) ]
    
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