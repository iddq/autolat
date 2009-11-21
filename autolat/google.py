from datetime import datetime
import logging
from xml.etree import ElementTree

from webservice import WebService


class Google(WebService):
    loginform_url = 'https://www.google.com/accounts/ServiceLogin'
    loginform_data = {
        'service': 'friendview',
        'hl': 'en',
        'nui': '1',
        'continue': 'http://maps.google.com/maps/m?mode=latitude',
    }
    loginform_id = 'gaia_loginform'
    loginform_user_field = 'Email'
    loginform_pass_field = 'Passwd'
    loginform_persist_field = 'PersistentCookie'

    def update_latitude(self, location):
        self._logger.info('Updating latitude location (%s, %s) ~%sm @ %s',
            location.longitude,
            location.latitude,
            location.accuracy,
            location.datetime.strftime('%d/%m/%Y %H:%M:%S')
        )
        data = {
            't': 'ul',
            'mwmct': 'iphone',
            'mwmcv': '5.8',
            'mwmdt': 'iphone',
            'mwmdv': '30102',
            'auto': 'true',
            'nr': '180000',
            'cts': location.timestamp*1000,
            'lat': '%s' % location.latitude,
            'lng': '%s' % location.longitude,
            'accuracy': location.accuracy,
        }
        return (self._post('http://maps.google.com/glm/mmap/mwmfr', data, {'X-ManualHeader': 'true'}).code == 200)

    def get_history(self, start, end):
        url = 'http://www.google.com/latitude/apps/history/kml'
        data = {
            'startDay': start,
            'endDay': end,
        }
        self._logger.info('Fetching latitude history from %s until %s', start, end)
        kml = self._get(url, data).read()
        if self._logger.isEnabledFor(logging.DEBUG):
            self._logger.debug('Got KML:')
            for line in kml.split('\n'):
                self._logger.debug('\t%s', line)
        kml = kml.replace('http://www.opengis.net/kml/2.2', '') # it just makes parsing the tags easier
        return sorted((Location.from_kml(placemark) for placemark in ElementTree.fromstring(kml).findall('.//Placemark')), key=lambda l: l.datetime)

class Location(object):
    """ Represents a Latitude "Check In". """
    def __init__(self, dt, latitude, longitude, accuracy, altitude):
        self.accuracy = accuracy
        self.altitude = altitude
        self.datetime = dt
        self.latitude = latitude
        self.longitude = longitude

    def __str__(self):
        return '(%s,%s) @ %s' % (
            self.latitude,
            self.longitude,
            self.datetime.strftime('%d/%m/%Y %H:%M:%S')
        )

    @classmethod
    def from_kml(cls, kml):
        if isinstance(kml, basestring):
            tree = ElementTree.fromstring(kml)
        else:
            tree = kml
        longitude, latitude, altitude = tree.find('.//Point/coordinates').text.split(',')
        for data in tree.findall('.//Data/'):
            if data.attrib['name'] == 'accuracy':
                accuracy = data.find('value').text
            if data.attrib['name'] == 'timestamp':
                dt = datetime.fromtimestamp(int(data.find('value').text)/1000)
        return cls(dt, latitude, longitude, accuracy, altitude)
