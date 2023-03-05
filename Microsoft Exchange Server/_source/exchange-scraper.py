#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# This file is part of third-parties-version-history.
#
# Copyright (C) 2020, Thomas Debize <tdebize at mail.com>
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
VERSION = '1.1'
TARGET = 'exchange'

# Options definition
parser = argparse.ArgumentParser(description="version: " + VERSION)
parser.add_argument('-m', '--mode', help="Mode to choose: check against a previous provided file ('previous'), or 'standalone' scrape (default 'update')", choices = ['previous', 'standalone'], type = str.lower, default = 'previous')
parser.add_argument('-p', '--previous-file', help='Path to previous file to take as a reference (default ../%s.csv)' % TARGET, default=path.abspath(path.join(os.getcwd(), '..', './%s.csv' % TARGET)))
parser.add_argument('-o', '--output-file', help='Output csv file (default ./%s.csv)' % TARGET, default=path.abspath(path.join(os.getcwd(), './%s.csv' % TARGET)))

def from_buildnumbers():
    root = fromstring(requests.get('https://buildnumbers.wordpress.com/exchange/').content)
    trs = root.findall('.//tr')
    
    for entry in trs:
        version = entry.xpath('string(td[1])').strip()
        description = entry.xpath('string(td[2])').strip()
        
        date = entry.xpath('string(td[3])').strip()
        try:
            format_str = "%Y %B %d"
            datetime_obj = datetime.datetime.strptime(date, format_str)
            date = datetime_obj.date().isoformat()
        except ValueError:
            continue
        
        if version and description and date:
            version_major, version_minor, version_build, version_revision = version.split('.', 3)
            
            # We have a short version number
            if len(version_minor) == 1:
                version_full = "%s.%s.%s.%s" % (version_major, version_minor.zfill(2), version_build.zfill(4), version_revision.zfill(3))
                version_short = version
            
            # We have a long version number
            elif len(version_minor) == 2:
                version_short = "%s.%s.%s.%s" % (version_major, version_minor.lstrip('0'), version_build.lstrip('0'), version_revision.lstrip('0'))
                version_full = version
            
            if description and date and version_short and version_full:
                exchange = {}
                
                exchange['date'] = date
                exchange['version_short'] = version_short
                exchange['description'] = description
                
                yield version_full, exchange

def from_microsoft():
    root = fromstring(requests.get('https://docs.microsoft.com/en-US/exchange/new-features/build-numbers-and-release-dates').content)
    trs = root.findall('.//tr')
    
    for entry in trs:
        description = entry.xpath('string(td[1])')
        
        date = entry.xpath('string(td[2])')
        for fmt in ('%B %d, %Y', '%B,%Y'):
            try:
                datetime_obj = datetime.datetime.strptime(date, fmt)
                date = datetime_obj.date().isoformat()
            except ValueError:
                pass
        
        version_short = entry.xpath('string(td[3])')
        version_full = entry.xpath('string(td[4])')
        
        if description and date and ((version_short and version_full) or (version_short and not(version_full))):
            exchange = {}
            exchange['date'] = date
            exchange['version_short'] = version_short
            exchange['description'] = description.strip()
            
            if version_short and not(version_full):
                yield version_short, exchange
            else:
                yield version_full, exchange
    
def scrape_and_merge(sources, results):
    for name, source in sources:
        count = 0
        for version, item in source:
            if version not in results['version_full'].values:
                results.loc[len(results)] = [version, item['version_short'], item['description'], item['date']]
                count = count + 1
                
        print("[+] %s entries collected from '%s'" % (count, name))
    
def scrape_and_generate_csv(opts):
    results = pd.DataFrame(columns=['version_full', 'version_short', 'description', 'date (yyyy-mm-dd)'])
    sources = [ ('microsoft', from_microsoft()),
                ('buildnumbers', from_buildnumbers()) ]
    
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