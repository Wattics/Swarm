Swarm
=====

Swarm is a simple python app that parses CSV files and uploads the measurements to the `Wattics`_ API.

Basics
------

Installation
************

  `pip install /path/to/swarm/folder`

Usage
*****

  `swarm config_file.ini`

CSV format
----------

Structure
*********

The CSV structure consists of:

+---------------+------------------------+---------+----------------------+
| ``timestamp`` | ``first measurements`` | ``...`` | ``last measurement`` |
+---------------+------------------------+---------+----------------------+

If the CSV includes all electrical parameters, then the measurements are listed in the `Wattics API docs`_, otherwise only one measurement column is allowed.

Technical details
*****************

- No header is expected
- Measurements values are float numbers, where the decimal digits separator is "." (dot)
- The expected separator character is "," (comma)
- The expected timestamp format is "%Y-%m-%d %H:%M:%S" (see python docs for more details)

.. _Wattics: http://www.wattics.com/
.. _Wattics API docs: http://docs.wattics.com/2016/02/22/how-can-i-upload-data-via-the-wattics-rest-api/
