OpenStreetMap data wrangling with MongoDb
=========================================

.. toctree::
   :maxdepth: 2


Introduction
============

The goal of this project is to use data wrangling (munging) techniques over data
obtained from the `OpenStreetMap <http://www.openstreetmap.org>`_. The data
correspond to a particular area of the world chosen by us. The data wrangling
consisted in :

* Obtaining the data from an API in OSM format.
* Parse the data using an python xml library.
* Transform the parsed data into a valid JSON file to be imported by MongoDB
* Import the JSON file into MongoDB
* Audit the data set and fix as many problems as possible.


