# -*- coding: utf-8 -*-
"""
This python set of functions help to parse, check, reshape and write into a JSON
file an OSM data file.

"""
import xml.etree.ElementTree as ETree
import re
import codecs
import json
import datetime as dt

CREATED = ["version", "changeset", "timestamp", "user", "uid"]


def get_db(db_name):
    """
    Function to connect to a mongodb server started at the local host, and
    return a pointer to a particular database.
    The code is based on one of the examples of the Data Wrangling class.

    :param db_name: string, name of the database the user wants to connect
    :return: pymongo database.Database instance
    """
    from pymongo import MongoClient
    client = MongoClient('localhost:27017')
    db = client[db_name]
    return db


def check_type(val):
    """
    Check the python type of a variable.

    :param val: the variable to check
    :return: the python type
    """

    try:
        a = float(val)
        return type(a)
    except ValueError:
        pass

    try:
        a = int(val)
        return type(a)
    except ValueError:
        pass

    try:
        a = dt.datetime.strptime(val, '%Y-%m-%dT%H:%M:%SZ')
        return type(a)
    except ValueError:
        pass

    return type(val)


def shape_element(key, value, document, position, prob_tag, tag, attrib_types):
    """
    Builds fields to insert into JSON documents

    :param key:
    :param value:
    :param document:
    :param position:
    :param prob_tag:
    :param tag:
    :param attrib_types:
    :return:
    """

    lower = re.compile(r'^([a-z]|_)*$')
    lower_colon = re.compile(r'^([a-z]|_)*:([a-z]|_)*$')
    problem_chars = re.compile(r'[=\+/&<>;\'"`\?%#$@\,\. \t\r\n]')

    if tag in ['node', 'way']:
        if key in CREATED:
            if 'created' in document.keys():
                document['created'][key] = value
            else:
                document['created'] = {key: value}
        elif key == 'lon':
            position[1] = float(value)
        elif key == 'lat':
            position[0] = float(value)
        else:
            document[key] = value

        t = check_type(value)
        if key in attrib_types.keys():
            attrib_types[key][0].add(t)
            attrib_types[key][1] += 1
        else:
            attrib_types[key] = [set(), 0]
            attrib_types[key][0].add(t)
            attrib_types[key][1] += 1

        return document, position, prob_tag, attrib_types

    elif tag == 'tag':
        if problem_chars.search(key):
            prob_tag.append(key)
        elif len(key.split(':')) == 3:
            prob_tag.append(key)
        elif lower_colon.search(key):
            if key.split(':')[0] == 'addr':
                if 'address' in document.keys():
                    document['address'][key.split(':')[1]] = value
                else:
                    document['address'] = {key.split(':')[1]: value}
            else:
                document[key] = value
        elif lower.search(key):
            document[key] = value
        else:
            prob_tag.append(key)

        if key not in prob_tag:
            t = check_type(value)
            if key in attrib_types.keys():
                attrib_types[key][0].add(t)
                attrib_types[key][1] += 1
            else:
                attrib_types[key] = [set(), 0]
                attrib_types[key][0].add(t)
                attrib_types[key][1] += 1

    elif tag == 'nd':
        if 'node_refs' in document.keys():
            document['node_refs'].append(value)
        else:
            document['node_refs'] = [value]

    return document, position, prob_tag, attrib_types


def process_map(file_in):
    """
    Converts an OSM file into a JSON valid to be ingested by mongodb
    The process includes:
    - Parse the xml files
    - Read the 'node' and 'way' elements (which are two of the three OSM' data
      primitives)
    - Build a document for each element, include its attributes, the variables
      related to the creation of the element, plus the child elements wich are
      either 'tags' or 'nd'.
    - Store the documents in a python list and write them in a JSON file.

    :param file_in:
    :return:
    """
    file_out = "{0}.json".format(file_in)
    osm_file = codecs.open(file_in, 'r')
    data = []
    problems = []
    ctags = 0
    pos = [0, 0]
    attribtypes = {}

    with codecs.open(file_out, "w") as fo:

        started = False
        for event, element in ETree.iterparse(
                osm_file, events=('start', 'end')):

            if not started:
                if event == 'start' and element.tag in ['node', 'way']:
                    started = True
                    doc = {}
                    pos = [0., 0]
                    for a, v in element.attrib.iteritems():
                        doc, pos, problems, attribtypes = shape_element(
                            a, v, doc, pos, problems, element.tag, attribtypes)
                if event == 'end':
                    element.clear()

            elif started:
                if event == 'end' and element.tag in ['node', 'way']:
                    doc['pos'] = pos
                    doc['type'] = element.tag
                    data.append(doc)
                    fo.write(json.dumps(doc) + '\n')
                    started = False
                    element.clear()
                elif event == 'start' and element.tag == 'tag':
                    doc, pos, problems, attribtypes = shape_element(
                        element.attrib['k'], element.attrib['v'], doc, pos,
                        problems, element.tag, attribtypes)
                    ctags += 1
                elif event == 'start' and element.tag == 'nd':
                    doc, pos, problems, attribtypes = shape_element(
                        'ref', element.attrib['ref'], doc, pos, problems,
                        element.tag, attribtypes)
                elif event == 'end':
                    element.clear()

    print ctags
    return data, problems, attribtypes


def count_tags(filename):
    """

    :param filename:
    :return:
    """

    osm_file = open(filename, 'r')
    tags = {}
    levels = {}
    started = 0
    for event, elem in ETree.iterparse(osm_file, events=('start', 'end')):
        if event == 'start':
            started += 1
            if elem.tag not in tags.keys():
                tags[elem.tag] = 1
            else:
                tags[elem.tag] += 1
            if started == 2:
                fl = elem.tag
                if elem.tag not in levels.keys():
                    levels[elem.tag] = set()
            if started == 3:
                levels[fl].add(elem.tag)
        elif event == 'end':
            started -= 1
            elem.clear()
    osm_file.close()
    return tags, levels


def check_struct(filename):
    """

    :param filename:
    :return:
    """
    osm_file = open(filename, 'r')
    structures = []
    problems = []

    lower = re.compile(r'^([a-z]|_)*$')
    lower_colon = re.compile(r'^([a-z]|_)*:([a-z]|_)*$')
    lower_2colon = re.compile(r'^([a-z]|_)*:([a-z]|_)*:([a-z]|_)*$')
    problemchars = re.compile(r'[=\+/&<>;\'"`\?%#$@\,\. \t\r\n]')

    started = False
    count = 0
    c2 = 0
    
    for event, elem in ETree.iterparse(osm_file, events=('start', 'end')):

        if not started:
            if event == 'start' and elem.tag in ['node', 'way']:
                started = True
                groups = []
                dicto = {}

            elif event == 'end':
                elem.clear()
            else:
                continue

        elif started:
            if event == 'end' and elem.tag in ['node', 'way']:
                started = False
                elem.clear()
                if set(groups) not in structures:
                    structures.append(set(groups))
            elif event == 'start':
                atr = elem.attrib
                if elem.tag == 'tag':
                    c2 += 1
                for a in atr:
                    if a == 'k':
                        count += 1
                        if lower_2colon.search(atr[a]):
                            problems.append(atr[a])
                        elif problemchars.search(atr[a]):
                            problems.append(atr[a])
                        elif lower.search(atr[a]) or lower_colon.search(atr[a]):
                            groups.append(atr[a])
                            dicto[atr[a]] = atr['v']
                        else:
                            problems.append(atr[a])

            else:
                elem.clear()
    print count, c2
    return structures, problems