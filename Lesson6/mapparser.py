#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Your task is to use the iterative parsing to process the map file and
find out not only what tags are there, but also how many, to get the
feeling on how much of which data you can expect to have in the map.
The output should be a dictionary with the tag name as the key
and number of times this tag can be encountered in the map as value.

Note that your code will be tested with a different data file than the
'example.osm'
"""

import xml.etree.ElementTree as ETree
import pprint


def count_tags(filename):
    osm_file = open(filename, 'r')
    tags1 = {}
    for event, elem in ETree.iterparse(osm_file, events=('start', 'end')):
        if elem.tag in tags1.keys() and event == 'start':
            tags1[elem.tag] += 1
        elif event == 'start':
            tags1[elem.tag] = 1
        if event == 'end':
            elem.clear()
    return tags1


def test(filename='example.osm'):
    tags = count_tags(filename)
    pprint.pprint(tags)
    assert tags == {'bounds': 1,
                    'member': 3,
                    'nd': 4,
                    'node': 20,
                    'osm': 1,
                    'relation': 1,
                    'tag': 7,
                    'way': 1}