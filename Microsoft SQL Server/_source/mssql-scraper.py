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
import codecs
from contextlib import closing

# Script version
VERSION = '1.0'

# Options definition
parser = argparse.ArgumentParser(description="version: " + VERSION)
parser.add_argument('-o', '--output-file', help='Output csv file (default ./mssql.csv)', default=path.abspath(path.join(os.getcwd(), './mssql.csv')))

def from_sqlserverbuilds():
    url = 'https://docs.google.com/spreadsheets/d/16Ymdz80xlCzb6CwRFVokwo0onkofVYFoSkc7mYe6pgw/export?gid=0&format=csv'
    with closing(requests.get(url, stream=True)) as r:
        spamreader = csv.DictReader(codecs.iterdecode(r.iter_lines(), 'utf-8'))
        for row in spamreader:
            mssql = {}
            date = ''
            if row['ReleaseDate']:
                datetime_obj = datetime.datetime.strptime(row['ReleaseDate'], "%Y-%m-%d")
                date = datetime_obj.date().isoformat()
            
            mssql['date'] = date
            mssql['description'] = row['Description']
            
            yield row['Build'], mssql
    
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
    sources = [ ('sqlserverbuilds', from_sqlserverbuilds()) ]
    
    scrape_and_merge(sources, results)
    
    return results

    
def generate_csv(results, options):
    keys = ['version_full', 'description', 'date (yyyy-mm-dd)']
    
    if results:
        with open(options.output_file, mode='w', encoding='utf-8') as fd_output:
            spamwriter = csv.writer(fd_output, delimiter=';', quoting=csv.QUOTE_ALL, lineterminator='\n')
            spamwriter.writerow(keys)
            
            for version_full in sorted(results.keys(), key=LooseVersion):
                output_line = []
                item = results[version_full]
                output_line = [version_full, item['description'], item['date']]
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