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
from lxml.html.soupparser import fromstring
from urllib.parse import urljoin
from looseversion import LooseVersion

import re
import csv
import os
import argparse
import datetime
import functools
import requests
import types
import concurrent.futures

# Script version
VERSION = '1.0'

# Options definition
parser = argparse.ArgumentParser(description="version: " + VERSION)
parser.add_argument('-o', '--output-file', help='Output csv file (default ./drupal.csv)', default=path.abspath(path.join(os.getcwd(), './drupal.csv')))


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
                if version not in results:
                    results[version] = item
                    count = count + 1
                
            print("[+] %s entries collected from '%s'" % (count, name))
        
        if isinstance(source, concurrent.futures._base.Future):
            for version, item in source.result():
                if version not in results:
                    results[version] = item
                    count = count + 1
                
            print("[+] %s entries collected from '%s'" % (count, name))
    
def scrape(opts):
    results = {}
    sources = [ ('drupal_old', from_drupal_old_releases()) ]
    sources = sources + from_drupal_new_releases()
    
    scrape_and_merge(sources, results)
    
    return results

    
def generate_csv(results, options):
    keys = ['version_full', 'date (yyyy-mm-dd)']
    if results:
        with open(options.output_file, mode='w', encoding='utf-8') as fd_output:
            spamwriter = csv.writer(fd_output, delimiter=';', quoting=csv.QUOTE_ALL, lineterminator='\n')
            spamwriter.writerow(keys)
            
            for version_full in sorted(results.keys(), key=LooseVersion):
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