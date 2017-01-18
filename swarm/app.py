"""Swarm module.

This module contains the facilities to read, parse and transmit csv files to web data collector
in the unified json packet format.
"""
import codecs
import csv
import datetime
import json
import logging
import signal
import sys
from configparser import ConfigParser
from os.path import expanduser, isfile

import requests
import tqdm

ELECTRICITY_KEYS = [
    'aP_1',
    'aP_2',
    'aP_3',
    'rP_1',
    'rP_2',
    'rP_3',
    'apP_1',
    'apP_2',
    'apP_3',
    'v_1',
    'v_2',
    'v_3',
    'c_1',
    'c_2',
    'c_3',
    'pC_1',
    'pC_2',
    'pC_3',
    'v_12',
    'v_13',
    'v_23'
]

LOGGER = logging.getLogger(__name__)


def initialize_logger(logger, level_name, logfile):
    """Initializes the provided logger."""
    level = logging.getLevelName(level_name)
    logger.setLevel(level)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    file_handler = logging.FileHandler(logfile)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)


class TimeserieProcessor():
    """Class TimeserieProcessor

    This class processes timeseries and generates unified packets.
    """

    def __init__(self, timeserie, fake_electric=False, minutes_shift=None):
        self._timeserie = timeserie
        self._fake_electric = fake_electric
        self._minutes_shift = minutes_shift

    def build_unified_packets(self, reference):
        """Generate unified json packets out of the wrapped timeserie.

        reference -- the string containing the channel reference
        """
        timeserie = self._timeserie
        if self._minutes_shift is not None:
            timeserie = self._prepend_padding_value(timeserie, self._minutes_shift)
        if self._fake_electric:
            timeserie = self._electrify(timeserie)
        packets = self._build_unified_packets(timeserie, reference)
        return packets

    @staticmethod
    def _prepend_padding_value(timeserie, minutes):
        padding_entry = {**timeserie[0], **{'value': timeserie[1]}}
        shifted_timeserie = [padding_entry]
        for entry in timeserie:
            shifted_slot_time = entry['tsISO8601'] + datetime.timedelta(minutes=minutes)
            shifted_timeserie.append({**entry, **{'tsISO8601': shifted_slot_time}})
        return shifted_timeserie

    @staticmethod
    def _electrify(timeserie):
        return [
            {
                'tsISO8601': entry['tsISO8601'],
                'pC_1': entry['value'],
                'aP_1': entry['value'] * 6
            }
            for entry in timeserie
            ]

    @staticmethod
    def _build_unified_packets(timeserie, reference):
        packets = []
        for entry in timeserie:
            packet = {**entry, **{
                'id': reference,
                'tsISO8601': entry['tsISO8601'].strftime('%Y-%m-%dT%H:%M:%S.000+00:00')
            }}
            packets.append(packet)
        return packets


def safe_string_to_float(value):
    """Tries to convert a value to a float number.

    Returns the float number if it succeeds or None if it fails.
    """
    try:
        return float(value)
    except ValueError:
        return None


def parse_single_value_csv(filename):
    """Parses a csv file with just timestamp and a single value."""
    expanded_filename = expanduser(filename)
    with codecs.open(expanded_filename, 'r', 'utf-8-sig') as csvfile:
        csvreader = csv.reader(csvfile, delimiter=',')
        timeserie = []
        for row in csvreader:
            timestamp, value = row
            packet_datetime = datetime.datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
            timeserie.append({'tsISO8601': packet_datetime, 'value': safe_string_to_float(value)})
    return timeserie


def parse_electricity_csv(filename):
    """Parses a csv file with timestamp and all the values for an electricity packet."""
    expanded_filename = expanduser(filename)
    with codecs.open(expanded_filename, 'r', 'utf-8-sig') as csvfile:
        csvreader = csv.reader(csvfile, delimiter=',')
        timeserie = []
        for row in csvreader:
            timestamp, *values = row
            values = [safe_string_to_float(value) for value in values]
            LOGGER.debug(json.dumps(values))
            packet_datetime = datetime.datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
            timeserie.append(dict(zip(
                ['tsISO8601', *ELECTRICITY_KEYS],
                [packet_datetime, *values]
            )))
    return timeserie


def send(url, unified_jsons, credentials):
    """Sends the the list of unified json packets to the Web Data Collector.

    url -- string for the complete url (hostname and end point) of the Web Data Collector
    unified_jsons -- list of dict structured as a unified json packet
    credentials -- two strings tuple with username and password for basic authentication
    """
    session = requests.Session()
    session.auth = credentials

    LOGGER.info('Starting the swarm')
    for unified_json in tqdm.tqdm(unified_jsons):
        payload = json.dumps(unified_json)
        try:
            response = session.post(url, data=payload)
            status_code_class = response.status_code / 100
            response_message = response.text.strip()
            if status_code_class == 2:
                LOGGER.debug('%s %s %s', response.status_code, unified_json, response_message)
            elif status_code_class == 3:
                LOGGER.warning('%s %s %s', response.status_code, unified_json, response_message)
            else:
                LOGGER.error('%s %s %s', response.status_code, unified_json, response_message)
        except requests.exceptions.RequestException as exception:
            LOGGER.critical(exception)
    LOGGER.info('Completed')


def print_usage_and_quit():
    """Prints instructions."""
    print('You need to specify the configuration file path as the only parameter.')
    exit(-1)


def main():
    """Main entry point."""
    if len(sys.argv) != 2:
        print_usage_and_quit()

    config_file_path = sys.argv[1]

    config_path = expanduser(config_file_path)
    if not isfile(config_path):
        print('Config file not found')
        exit(-1)

    config = ConfigParser(allow_no_value=True)
    config.read(config_path)

    initialize_logger(LOGGER, config['Logs']['Level'], config['Logs']['Filename'])

    credentials = (config['Web DC']['Username'], config['Web DC']['Password'])

    if config['General']['MinutesShift'] is None:
        minutes_shift = None
    else:
        minutes_shift = int(config['General']['MinutesShift'])

    if config['General']['ChannelType'] == 'real':
        timeserie = parse_electricity_csv(config['General']['Filename'])
    else:
        timeserie = parse_single_value_csv(config['General']['Filename'])
    timeserie_processor = TimeserieProcessor(
        timeserie,
        fake_electric=True if config['General']['ChannelType'] == 'fake' else False,
        minutes_shift=minutes_shift
    )
    unified_jsons = timeserie_processor.build_unified_packets(config['General']['ChannelReference'])
    send(config['Web DC']['URL'], unified_jsons, credentials)


if __name__ == '__main__':
    def abort_and_quit(*_):
        """Gracefully handles Ctrl+C interrupt and quits."""
        message = 'Aborted'
        LOGGER.info(message)
        sys.exit(0)


    signal.signal(signal.SIGINT, abort_and_quit)
    main()
