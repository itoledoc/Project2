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

# Functions and variables to fix streets
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


# Functions to fix phone numbers with pymongo.
def correct_phone_dict(collection):

    phone = []
    cursor = collection.find(
        {'$or': [{'phone': {'$exists': 1}},
                 {'contact:phone': {'$exists': 1}}]},
        {'_id': 0, 'phone': 1, 'contact:phone': 1})
    for c in cursor:
        phone.append(c.values()[0])

    correct = {}
    nofix = 0
    problemc = re.compile(r'\D')
    for p in phone:
        ptemp = p.split(';')
        fix = False
        for i in range(len(ptemp)):
            ptemp[i] = ptemp[i].replace(' ','').replace('(','').replace(')','').replace('-','').replace('+','')
            if problemc.search(ptemp[i]):
                correct[p] = 'FIXME'
                fix = True
                break
            if len(ptemp[i]) > 11:
                correct[p] = 'FIXME'
                fix = True
                break
            if len(ptemp[i]) == 11  and ptemp[i].startswith('5622'):
                ptemp[i] = "+56 2 2" + ptemp[i][4:]
                nofix += 1
                continue
            if len(ptemp[i]) == 10  and ptemp[i].startswith('562'):
                ptemp[i] = "+56 2 2" + ptemp[i][3:]
                continue
            if len(ptemp[i]) == 11  and ptemp[i].startswith('5602'):
                ptemp[i] = "+56 2 2" + ptemp[i][4:]
                continue
            if len(ptemp[i]) == 12  and ptemp[i].startswith('56022'):
                ptemp[i] = "+56 2 2" + ptemp[i][5:]
                continue
            if len(ptemp[i]) == 11  and ptemp[i].startswith('569'):
                ptemp[i] = "+56 9" + ptemp[i][3] + ' ' + ptemp[i][4:]
                continue
            if len(ptemp[i]) == 9 and ptemp[i].startswith('02'):
                ptemp[i] = "+56 2 2" + ptemp[i][2:]
                continue
            if len(ptemp[i]) == 10 and ptemp[i].startswith('022'):
                ptemp[i] = "+56 2 2" + ptemp[i][3:]
                continue
            if len(ptemp[i]) == 8 and ptemp[i].startswith('2'):
                ptemp[i] = "+56 2 2" + ptemp[i][1:]
                continue
            if len(ptemp[i]) == 9 and ptemp[i].startswith('22'):
                ptemp[i] = "+56 2 2" + ptemp[i][2:]
                continue

            if len(ptemp[i]) == 7:
                ptemp[i] = "+56 2 2" + ptemp[i]
                continue

            if len(ptemp[i]) == 10 and (ptemp[i].startswith('800') or ptemp[i].startswith('600')):
                ptemp[i] = ptemp[i][0:3] + ' ' + ptemp[i][3:6] + ' ' + ptemp[i][6:]
                continue

            correct[p] = 'FIXME'
            fix = True
            break

        if fix:
            continue
        if len(ptemp) == 1:
            ptemp = ptemp[0]

        correct[p] = ptemp


def do_correct_phone(collection, phone_dict):

    for k, v in phone_dict.iteritems():
        collection.update(
            {'contact:phone': k},
            {'$set': {'contact:phone': v}},
            multi=True)
        collection.update(
            {'phone': k},
            {'$set': {'phone': v}},
            multi=True)