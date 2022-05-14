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
from urllib.parse import urljoin
from packaging import version
import requests

# Script version
VERSION = '1.1'

# Options definition
parser = argparse.ArgumentParser(description="version: " + VERSION)
parser.add_argument('-o', '--output-file', help='Output csv file (default ./clamav.csv)', default=path.abspath(path.join(os.getcwd(), './clamav.csv')))

def from_clamav():
    urls = ['https://www.clamav.net/downloads', 'https://www.clamav.net/previous_stable_releases']
    
    # specifying headers to bypass Cloudflare protection
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36"}
    for url in urls:
        root = fromstring(requests.get(url, headers=headers).content)
        trs = root.findall('.//tr')
        p_version = re.compile(r'clamav-(?P<version>\d{1,2}\..*)\.tar\.gz$', re.IGNORECASE)
        
        for entry in trs:
            date = entry.xpath('string(td[2])').strip()
            release = entry.xpath('string(td[1])').strip()
            
            version_entry = p_version.search(release)
            if version_entry and date:
                release = version_entry.group('version')
                
                clamav = {}
                format_str = "%Y-%m-%d %H:%M:%S UTC"
                datetime_obj = datetime.datetime.strptime(date, format_str)
                clamav['date'] = datetime_obj.date().isoformat()
            
                yield release, clamav

def from_chocolatey():
    root = fromstring(requests.get('https://chocolatey.org/packages/clamav').content)
    trs = root.findall('.//tr')
    p_version = re.compile(r'(?P<version>\d{1,2}\..*)', re.IGNORECASE)
    
    for entry in trs:
        date = entry.xpath('string(td[4])').strip()
        release = entry.xpath('string(td[2]/a|td[2]/span)')
        
        version_entry = p_version.search(release)
        if version_entry and date:
            release = version_entry.group('version')
            
            clamav = {}
            format_str = "%A, %B %d, %Y"
            datetime_obj = datetime.datetime.strptime(date, format_str)
            clamav['date'] = datetime_obj.date().isoformat()
        
            yield release, clamav
    
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
    sources = [ ('clamav', from_clamav()), 
                ('chocolatey', from_chocolatey()) ]
    
    scrape_and_merge(sources, results)
    
    return results

    
def generate_csv(results, options):
    keys = ['version_full', 'date (yyyy-mm-dd)']
    
    if results:
        with open(options.output_file, mode='w', encoding='utf-8') as fd_output:
            spamwriter = csv.writer(fd_output, delimiter=';', quoting=csv.QUOTE_ALL, lineterminator='\n')
            spamwriter.writerow(keys)
            
            for version_full in sorted(results.keys(), key=version.parse):
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