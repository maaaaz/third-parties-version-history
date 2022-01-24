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
from distutils.version import LooseVersion
import requests

# Script version
VERSION = '1.0'

# Options definition
parser = argparse.ArgumentParser(description="version: " + VERSION)
parser.add_argument('-o', '--output-file', help='Output csv file (default ./virtualbox.csv)', default=path.abspath(path.join(os.getcwd(), './virtualbox.csv')))

def from_virtualbox():
    urls = ['https://www.virtualbox.org/wiki/Changelog',
           'https://www.virtualbox.org/wiki/Changelog-6.0',
           'https://www.virtualbox.org/wiki/Changelog-5.2',
           'https://www.virtualbox.org/wiki/Changelog-5.1',
           'https://www.virtualbox.org/wiki/Changelog-5.0',
           'https://www.virtualbox.org/wiki/Changelog-4.3',
           'https://www.virtualbox.org/wiki/Changelog-4.2',
           'https://www.virtualbox.org/wiki/Changelog-4.1',
           'https://www.virtualbox.org/wiki/Changelog-4.0']
    
    for url in urls:
        root = fromstring(requests.get(url).content)
        trs = root.xpath('.//p')
        
        p_version_and_date = re.compile('VirtualBox (?P<version>(\d{1,2}\.?){3}) \(released\s(?P<date>.*?)\)', re.IGNORECASE)
        for entry in trs:
            
            version_and_date = p_version_and_date.search(entry.text_content())
            if version_and_date:
                release = version_and_date.group('version')
                date = version_and_date.group('date')
                
                virtualbox = {}
                for fmt in ('%B %d %Y', '%Y-%m-%d'):
                    try:
                        datetime_obj = datetime.datetime.strptime(date, fmt)
                    except ValueError:
                        pass
                
                virtualbox['date'] = datetime_obj.date().isoformat()
            
                yield release, virtualbox

def from_chocolatey():
    root = fromstring(requests.get('https://chocolatey.org/packages/virtualbox').content)
    trs = root.findall('.//tr')
    p_version = re.compile('(?P<version>\d{1,2}\..*)', re.IGNORECASE)
    
    for entry in trs:
        date = entry.xpath('string(td[4])').strip()
        release = entry.xpath('string(td[2]/a|td[2]/span)')
        
        version_entry = p_version.search(release)
        if version_entry and date:
            release = version_entry.group('version')
            
            virtualbox = {}
            format_str = "%A, %B %d, %Y"
            datetime_obj = datetime.datetime.strptime(date, format_str)
            virtualbox['date'] = datetime_obj.date().isoformat()
        
            yield release, virtualbox
    
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
    sources = [ ('virtualbox', from_virtualbox()),
                ('chocolatey', from_chocolatey()) ]
    
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