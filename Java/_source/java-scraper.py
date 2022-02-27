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

from lxml.html.soupparser import fromstring
import requests
import datetime
from distutils.version import LooseVersion

# Script version
VERSION = '1.2'

# Options definition
parser = argparse.ArgumentParser(description="version: " + VERSION)
parser.add_argument('-o', '--output-file', help='Output csv file (default ./java.csv)', default=path.abspath(path.join(os.getcwd(), './java.csv')))

    
def from_wikipedia():
    root = fromstring(requests.get('https://en.wikipedia.org/wiki/Java_version_history').content)
    
    p_java_until_9 = re.compile('java se (?P<version_major>\d*) update (?P<version_minor>.*)', re.IGNORECASE)
    p_java_9_plus = re.compile('java se (?P<version_major>\d*?)\.(?P<version_minor>.*)', re.IGNORECASE)
    
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

'''
def from_oracle():
    root = fromstring(requests.get('https://java.com/releases/', headers={"user-agent": "Chrome 72"}).content)
    
    p_java = re.compile('java (?P<version_major>\d*) update (?P<version_minor>\d*)', re.IGNORECASE)
    
    trs = root.findall('.//tr')
    for entry in trs:
        release = entry.xpath('string(td[1]/text())')
        date = entry.xpath('string(td[2]/text())')
        
        java_entry = p_java.search(release)
        if java_entry:
            java = {}
            version_full = "1.%s.0_%s" % (java_entry.group('version_major').strip(), java_entry.group('version_minor').strip())
            java['version_major'] = java_entry.group('version_major')
            java['date'] = date.strip()
            yield version_full, java
'''
def from_chocolatey():
    urls = [ 'https://community.chocolatey.org/packages/oraclejdk',
             'https://community.chocolatey.org/packages/jre8',
             'https://community.chocolatey.org/packages/corretto11jdk',
             'https://community.chocolatey.org/packages/openjdk11',
           ]
    for url in urls:
        root = fromstring(requests.get(url).content)
        trs = root.findall('.//tr')
        p_version = re.compile('(?P<version_major>\d{1,2}?)\.(?P<version_0>.)\.(?P<version_minor>.*)', re.IGNORECASE)
        
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
    keys = ['version_full', 'version_major', 'date (yyyy-mm-dd)']
    
    if results:
        with open(options.output_file, mode='w', encoding='utf-8') as fd_output:
            spamwriter = csv.writer(fd_output, delimiter=';', quoting=csv.QUOTE_ALL, lineterminator='\n')
            spamwriter.writerow(keys)
            '''
            for version_full in sorted(results.keys(), key=lambda s: list(map(int, s.replace('.0_','.').split('.', 2)))):
            '''
            for version_full in sorted(results.keys(), key=LooseVersion):
                output_line = []
                item = results[version_full]
                output_line = [version_full, item['version_major'], item['date']]
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