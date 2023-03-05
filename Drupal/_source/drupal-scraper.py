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
from urllib.parse import urljoin
import re
import csv
import os
import argparse
import datetime
import functools
import requests
import types
import concurrent.futures

from lxml.html.soupparser import fromstring
#from looseversion import LooseVersion
from distutils.version import LooseVersion
from packaging import version
import requests
import pandas as pd
import numpy as np

# Globals
VERSION = '1.1'
TARGET = 'drupal'

# Options definition
parser = argparse.ArgumentParser(description="version: " + VERSION)
parser.add_argument('-m', '--mode', help="Mode to choose: check against a previous provided file ('previous'), or 'standalone' scrape (default 'update')", choices = ['previous', 'standalone'], type = str.lower, default = 'previous')
parser.add_argument('-p', '--previous-file', help='Path to previous file to take as a reference (default ../%s.csv)' % TARGET, default=path.abspath(path.join(os.getcwd(), '..', './%s.csv' % TARGET)))
parser.add_argument('-o', '--output-file', help='Output csv file (default ./%s.csv)' % TARGET, default=path.abspath(path.join(os.getcwd(), './%s.csv' % TARGET)))

def from_drupal_old_releases():
    url_old_release = 'https://www.drupal.org/docs/8/understanding-drupal-version-numbers/drupal-release-history'
    root = fromstring(requests.get(url_old_release).content)
    trs = root.findall('.//p')
    p_release_and_date = re.compile(r'Drupal (?P<version>\d{1,2}\..*), (?P<date>.*)$', re.IGNORECASE)
    for entry in trs:
        date = entry.xpath('string(td[2])').strip()
        release = entry.xpath('string(td[1])').strip()
        
        release_and_date = p_release_and_date.search(entry.text)
        if release_and_date:
            release = release_and_date.group('version')
            
            drupal = {}
            format_str = "%Y-%m-%d"
            datetime_obj = datetime.datetime.strptime(release_and_date.group('date'), format_str)
            drupal['date'] = datetime_obj.date().isoformat()
            
            yield release, drupal

def from_drupal_new_releases_enum(target):
    page_url = 'https://www.drupal.org/project/drupal/releases?version=%d' % target
    root = fromstring(requests.get(page_url).content)

    div = root.xpath('.//div[contains(@class,"node-project-release")]')
    root_entry = div[0]
    
    p_version = re.compile(r'(?P<version>\d{1,2}\..*)$', re.IGNORECASE)
    page_url_version = urljoin('https://www.drupal.org/project/', root_entry.xpath('string(h2/a/@href)'))
    root_version = fromstring(requests.get(page_url_version).content)
    
    entry_version = root_version.xpath('.//div[contains(@class, "item-list")]/ul/li')
    for entry in entry_version:
        release = entry.xpath('string(span[1]/span/a)')
        date = entry.xpath('string(span[2]/span)')
    
        version_entry = p_version.search(release)
        if version_entry and date:
            release = version_entry.group('version')
            
            drupal = {}
            format_str = "%d %B %Y"
            datetime_obj = datetime.datetime.strptime(date, format_str)
            drupal['date'] = datetime_obj.date().isoformat()
            
            yield release, drupal

def from_drupal_new_releases():
    base_url = 'https://www.drupal.org/project/drupal/releases'
    root = fromstring(requests.get(base_url).content)
    
    targets = range(7,11)
    
    # enum each version page
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futs = [ ("Drupal releases version %s" % target, executor.submit(functools.partial(from_drupal_new_releases_enum, target)))
                 for target in targets ]
    
        return futs

def scrape_and_merge(sources, results):
    for name, source in sources:
        count = 0
        if isinstance(source, types.GeneratorType):
            for version, item in source:
                if version not in results['version_full'].values and not('x-dev' in version):
                    results.loc[len(results)] = [version, item['date']]
                    count = count + 1
                
            print("[+] %s entries collected from '%s'" % (count, name))
        
        if isinstance(source, concurrent.futures._base.Future):
            for version, item in source.result():
                if version not in results['version_full'].values and not('x-dev' in version):
                    results.loc[len(results)] = [version, item['date']]
                    count = count + 1
                
            print("[+] %s entries collected from '%s'" % (count, name))
    
def scrape_and_generate_csv(opts):
    results = pd.DataFrame(columns=['version_full', 'date (yyyy-mm-dd)'])
    sources = [ ('drupal_old', from_drupal_old_releases()) ]
    sources = sources + from_drupal_new_releases()
    
    scrape_and_merge(sources, results)
    
    if opts.mode == 'previous':
        old_results = pd.read_csv(opts.previous_file, delimiter=';', quoting=csv.QUOTE_ALL, lineterminator='\n')
        results_concat = pd.concat([old_results, results]).drop_duplicates(subset = 'version_full')
        results = results_concat
    
    final_results = results.sort_values(by='version_full', key=np.vectorize(version.parse)).reset_index(drop=True)
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