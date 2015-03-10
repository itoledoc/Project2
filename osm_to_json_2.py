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


def shape_element(key, value, document, position, tag, father):
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

        return document, position

    elif tag == 'tag':
        if problem_chars.search(key):
            a = None
        elif len(key.split(':')) == 3:
            a = None
        elif lower_colon.search(key):
            if key.split(':')[0] == 'addr':
                if key.split(':')[1] == 'street':
                    value = correct_name(value)
                if 'address' in document.keys():
                    document['address'][key.split(':')[1]] = value
                else:
                    document['address'] = {key.split(':')[1]: value}
            else:
                if (father == 'way') and (key == 'name'):
                    value = correct_name(value)
                document[key] = value
        elif lower.search(key):
            if (father == 'way') and (key == 'name'):
                value = correct_name(value)
            document[key] = value
        else:
            a = None

    elif tag == 'nd':
        if 'node_refs' in document.keys():
            document['node_refs'].append(value)
        else:
            document['node_refs'] = [value]

    return document, position


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
    pos = [0, 0]

    with codecs.open(file_out, "w") as fo:

        started = False
        for event, element in ETree.iterparse(
                osm_file, events=('start', 'end')):

            if not started:
                if event == 'start' and element.tag in ['node', 'way']:
                    started = True
                    doc = {}
                    pos = [0., 0]
                    father = element.tag
                    for a, v in element.attrib.iteritems():
                        doc, pos = shape_element(
                            a, v, doc, pos, element.tag, father)
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
                    doc, pos = shape_element(
                        element.attrib['k'], element.attrib['v'], doc, pos,
                        element.tag, father)
                elif event == 'start' and element.tag == 'nd':
                    doc, pos = shape_element(
                        'ref', element.attrib['ref'], doc, pos,
                        element.tag, father)
                elif event == 'end':
                    element.clear()

    return data


CORRECT = {'Avda': 'Avenida',
           'Avda.': 'Avenida',
           'Av': 'Avenida',
           'Av.': 'Avenida',
           'Pje': 'Pasaje',
           'Pja': 'Pasaje',
           'Pje.': 'Pasaje'}


def correct_name(name):

    for k, v in CORRECT.iteritems():
        if (k in name) and (v not in name):
            return name.replace(k, v)

    return name