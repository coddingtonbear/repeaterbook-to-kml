import argparse
import csv
import logging
import os
import re
from urllib2 import urlparse

from apiclient.discovery import build
import lxml.html
import percache
import requests
import simplekml


FIELDS = [
    'Location', 'Name', 'Frequency', 'Duplex', 'Offset', 'Tone',
    'rToneFreq', 'cToneFreq', 'DtcsCode', 'DtcsPolarity', 'Mode',
    'TStep', 'Comment'
]

GOOGLE_CLIENT = None


cache = percache.Cache('/tmp/repeaterbook-to-kml.cache')

logger = logging.getLogger(__name__)


def get_google_client(key):
    global GOOGLE_CLIENT

    if not GOOGLE_CLIENT:
        GOOGLE_CLIENT = build('customsearch', 'v1', developerKey=key)

    return GOOGLE_CLIENT


def validate_document(reader):
    if set(reader.fieldnames) != set(FIELDS):
        raise ValueError(
            "Field names did not match our expectations; are you sure "
            "this is the CHIRP format CSV file?"
        )


@cache
def get_repeaterbook_url(line, key):
    client = get_google_client(key)
    cse = client.cse()

    results = cse.list(
        cx='008049306912733949078:onrj7uchdv0',
        q=line['Name']
    ).execute()

    for result in results['items']:
        if 'details.php' in result['link']:
            return result['link']

    raise ValueError('Could not find link for %s' % line['Name'])


@cache
def get_repeaterbook_data(line, key):
    def get_node_text(node):
        return (
            ' '.join(node.xpath('text()') + node.xpath('*/text()')).strip()
        )

    data = {
        'fields': {}
    }

    try:
        url = get_repeaterbook_url(line, key)
    except ValueError:
        return data

    data.update({'url': url})

    repeaterbook = requests.get(url)
    document = lxml.html.fromstring(repeaterbook.content)
    matches = re.search(
        r'myLatlng = new google\.maps\.LatLng\('
        r'(?P<latitude>[0-9-.]+),(?P<longitude>[0-9-.]+)\);',
        repeaterbook.content,
    )
    if matches:
        data.update(matches.groupdict())

    results = document.xpath("//table[@class='details']//tr")
    for result in results:
        key = get_node_text(result[0]).strip(':')
        if not key:
            continue

        try:
            value = get_node_text(result[1])
        except:
            continue

        if value:
            data['fields'][key] = value

    return data


def annotate_row(line, key):
    line.update(get_repeaterbook_data(line, key))


def get_name(line):
    return line['Name']


def get_description(line):
    def add_line(description, field_name):
        if line[field_name]:
            description.append(
                '%s: %s' % (
                    field_name,
                    line[field_name],
                )
            )

    description = []
    if 'url' in line:
        description.append(
            "<a href='%s'>%s</a>" % (
                line['url'],
                line['url']
            )
        )
        description.append('')

    for field in FIELDS:
        add_line(description, field)

    description.append('')

    for key, value in line['fields'].items():
        if value and key not in FIELDS:
            description.append(
                '%s: %s' % (
                    key,
                    value
                )
            )

    return '<br>'.join(description)


def get_coords(line):
    if line.get('latitude') and line.get('longitude'):
        return [
            (float(line['longitude']), float(line['latitude']), )
        ]


def main(csv_path, kml_path, google_key=None):
    with open(csv_path, 'r') as inf:
        reader = csv.DictReader(inf.readlines())

    kml = simplekml.Kml()

    printed = set()

    validate_document(reader)
    for line in reader:
        if line['Name'] in printed or not line['Name']:
            continue

        logger.info('Processing %s', line['Name'])
        if google_key:
            annotate_row(line, google_key)
        coords = get_coords(line)
        if not coords:
            continue

        kml.newpoint(
            name=get_name(line),
            description=get_description(line),
            coords=coords,
        )

        printed.add(line['Name'])

    kml.save(kml_path)


def cmdline():
    parser = argparse.ArgumentParser()
    parser.add_argument('csv_path')
    parser.add_argument('kml_path')
    parser.add_argument(
        '--google-api-key',
        default=os.environ.get('GOOGLE_API_KEY'),
        help=(
            "If provided, will fetch additional information about this "
            "repeater from Repeaterbook.com."
        )
    )
    parser.add_argument('--log-level', default='INFO')
    args = parser.parse_args()

    logging.basicConfig(level=logging.getLevelName(args.log_level))

    main(
        args.csv_path,
        args.kml_path,
        google_key=args.google_api_key,
    )
