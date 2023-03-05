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
from looseversion import LooseVersion
import requests
import pandas as pd
import numpy as np

# Globals
VERSION = '1.2'
TARGET = 'flash'

# Options definition
parser = argparse.ArgumentParser(description="version: " + VERSION)
parser.add_argument('-m', '--mode', help="Mode to choose: check against a previous provided file ('previous'), or 'standalone' scrape (default 'update')", choices = ['previous', 'standalone'], type = str.lower, default = 'previous')
parser.add_argument('-p', '--previous-file', help='Path to previous file to take as a reference (default ../%s.csv)' % TARGET, default=path.abspath(path.join(os.getcwd(), '..', './%s.csv' % TARGET)))
parser.add_argument('-o', '--output-file', help='Output csv file (default ./%s.csv)' % TARGET, default=path.abspath(path.join(os.getcwd(), './%s.csv' % TARGET)))

    
def from_adobe():
    root = fromstring(requests.get('https://helpx.adobe.com/flash-player/kb/archived-flash-player-versions.html').content)
    
    p_version_1 = re.compile(r'flash player (?P<version_full>[.0-9]*)', re.IGNORECASE)
    p_version_2 = re.compile(r'flash player (?P<version_full_1>[.0-9]*)\s+and (?P<version_full_2>[.0-9]*)', re.IGNORECASE)
    p_date = re.compile(r'.*released (?P<date>.*)\)', re.IGNORECASE)
    
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
            if version not in results['version_full'].values:
                results.loc[len(results)] = [version, item['date']]
                count = count + 1
                
        print("[+] %s entries collected from '%s'" % (count, name))
    
def scrape_and_generate_csv(opts):
    results = pd.DataFrame(columns=['version_full', 'date (yyyy-mm-dd)'])
    sources = [ ('adobe', from_adobe()), 
                ('snapfiles', from_snapfiles()) ]
    
    scrape_and_merge(sources, results)
    
    if opts.mode == 'previous':
        old_results = pd.read_csv(opts.previous_file, delimiter=';', quoting=csv.QUOTE_ALL, lineterminator='\n')
        results_concat = pd.concat([old_results, results]).drop_duplicates(subset = 'version_full')
        results = results_concat
    
    final_results = results.sort_values(by='version_full', key=np.vectorize(LooseVersion)).reset_index(drop=True)
    final_results.to_csv(opts.output_file, sep=';', index=False, quoting=csv.QUOTE_ALL, lineterminator='\n')
    
    return
    
def main():
    """
        Dat main
    """
    global parser
    options = parser.parse_args()
    
    if options.mode == 'previous':
        if os.path.isfile(options.previous_file):
            print('[+] using previous mode with "%s" file' % options.previous_file)
        else:
            parser.error('[!] previous file "%s" cannot be found' % options.previous_file)
        
    options.output_file = path.abspath(path.join(os.getcwd(), options.output_file)) if options.output_file else options.output_file
              
    scrape_and_generate_csv(options)
    
    return

if __name__ == "__main__" :
    main()