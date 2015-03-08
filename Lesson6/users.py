#!/usr/bin/env python
# -*- coding: utf-8 -*-
import xml.etree.ElementTree as ETree
import pprint

"""
Your task is to explore the data a bit more.
The first task is a fun one - find out how many unique users
have contributed to the map in this particular area!

The function process_map should return a set of unique user IDs ("uid")
"""


def get_user(element):
    if 'uid' in element.attrib:
        return element.attrib['uid']
    return None


def process_map(filename):
    users = set()
    for _, element in ETree.iterparse(filename):
        if element.tag in ['node', 'way', 'relation']:
            uid = get_user(element)
            if uid is not None:
                users.add(uid)

    return users


def test(filename='example.osm'):

    users = process_map(filename)
    pprint.pprint(users)

    if filename == 'example.osm':
        assert len(users) == 6


if __name__ == "__main__":
    test()