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
VERSION = '1.3'
TARGET = 'java'

# Options definition
parser = argparse.ArgumentParser(description="version: " + VERSION)
parser.add_argument('-m', '--mode', help="Mode to choose: check against a previous provided file ('previous'), or 'standalone' scrape (default 'update')", choices = ['previous', 'standalone'], type = str.lower, default = 'previous')
parser.add_argument('-p', '--previous-file', help='Path to previous file to take as a reference (default ../%s.csv)' % TARGET, default=path.abspath(path.join(os.getcwd(), '..', './%s.csv' % TARGET)))
parser.add_argument('-o', '--output-file', help='Output csv file (default ./%s.csv)' % TARGET, default=path.abspath(path.join(os.getcwd(), './%s.csv' % TARGET)))

def from_wikipedia():
    root = fromstring(requests.get('https://en.wikipedia.org/wiki/Java_version_history').content)
    
    p_java_until_9 = re.compile(r'java se (?P<version_major>\d*) update (?P<version_minor>.*)', re.IGNORECASE)
    p_java_9_plus = re.compile(r'java se (?P<version_major>\d*?)\.(?P<version_minor>.*)', re.IGNORECASE)
    
    trs = root.findall('.//tbody/tr')
    for entry in trs:
        release = entry.xpath('string(td[1]/text())')
        date = entry.xpath('string(td[2]/text())')
        
        java_entry = p_java_until_9.search(release)
        if java_entry and not "+" in java_entry.group('version_minor').strip():
            java = {}
            version_full = "1.%s.0_%s" % (java_entry.group('version_major').strip(), java_entry.group('version_minor').strip())
            java['version_major'] = java_entry.group('version_major')
            java['date'] = date.strip()
            yield version_full, java
            
        java_entry = p_java_9_plus.search(release)
        if java_entry and not "+" in java_entry.group('version_minor').strip():
            java = {}
            version_full = "1.%s.%s" % (java_entry.group('version_major').strip(), java_entry.group('version_minor').strip().replace('.','_'))
            java['version_major'] = java_entry.group('version_major')
            java['date'] = date.strip()
            yield version_full, java

def from_chocolatey():
    urls = [ 'https://community.chocolatey.org/packages/oraclejdk',
             'https://community.chocolatey.org/packages/jre8',
             'https://community.chocolatey.org/packages/corretto11jdk',
             'https://community.chocolatey.org/packages/openjdk11',
           ]
    for url in urls:
        root = fromstring(requests.get(url).content)
        trs = root.findall('.//tr')
        p_version = re.compile(r'(?P<version_major>\d{1,2}?)\.(?P<version_0>.)\.(?P<version_minor>.*)', re.IGNORECASE)
        
        for entry in trs:
            date = entry.xpath('string(td[4])').strip()
            release = entry.xpath('string(td[2]/a|td[2]/span)')
            
            
            version_entry = p_version.search(release)
            if version_entry and date:
                release = "1.%s.%s_%s" % (version_entry.group('version_major').strip(),version_entry.group('version_0').strip() , version_entry.group('version_minor').strip())
                
                java = {}
                format_str = "%A, %B %d, %Y"
                datetime_obj = datetime.datetime.strptime(date, format_str)
                java['date'] = datetime_obj.date().isoformat()
                java['version_major'] = version_entry.group('version_major')
            
                yield release, java

def scrape_and_merge(sources, results):
    for name, source in sources:
        count = 0
        for version, item in source:
            if version not in results['version_full'].values:
                results.loc[len(results)] = [version, item['version_major'], item['date']]
                count = count + 1
                
        print("[+] %s entries collected from '%s'" % (count, name))
    
def scrape_and_generate_csv(opts):
    results = pd.DataFrame(columns=['version_full', 'version_major', 'date (yyyy-mm-dd)'])
    sources = [ ('wikipedia', from_wikipedia()), 
                ('chocolatey', from_chocolatey()) ]
    
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