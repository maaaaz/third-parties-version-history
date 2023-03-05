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
TARGET = 'edge'

# Options definition
parser = argparse.ArgumentParser(description="version: " + VERSION)
parser.add_argument('-m', '--mode', help="Mode to choose: check against a previous provided file ('previous'), or 'standalone' scrape (default 'update')", choices = ['previous', 'standalone'], type = str.lower, default = 'previous')
parser.add_argument('-p', '--previous-file', help='Path to previous file to take as a reference (default ../%s.csv)' % TARGET, default=path.abspath(path.join(os.getcwd(), '..', './%s.csv' % TARGET)))
parser.add_argument('-o', '--output-file', help='Output csv file (default ./%s.csv)' % TARGET, default=path.abspath(path.join(os.getcwd(), './%s.csv' % TARGET)))

def from_chocolatey():
    root = fromstring(requests.get('https://chocolatey.org/packages/microsoft-edge').content)
    trs = root.findall('.//tr')
    p_version = re.compile(r'(?P<version>\d{1,3}\.[0-9.]*)', re.IGNORECASE)
    
    for entry in trs:
        date = entry.xpath('string(td[4])').strip()
        release = entry.xpath('string(td[2]/a|td[2]/span)')
        
        version_entry = p_version.search(release)
        if version_entry and date:
            release = version_entry.group('version')
            
            edge = {}
            format_str = "%A, %B %d, %Y"
            datetime_obj = datetime.datetime.strptime(date, format_str)
            edge['date'] = datetime_obj.date().isoformat()
        
            yield release, edge
    
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
    sources = [ ('chocolatey', from_chocolatey()) ]
    
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