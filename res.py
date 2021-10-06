import requests
import logging
import json
import sys


_LOGGER = logging.getLogger(__name__)
_LOGGER.addHandler(logging.NullHandler())


class Resy:
    def __init__(self, username, password, venue, party, date, times):
        self.headers = {
            'origin': 'https://resy.com',
            'accept-encoding': 'gzip, deflate, br',
            'x-origin': 'https://resy.com',
            'accept-language': 'en-US,en;q=0.9',
            'authorization': 'ResyAPI api_key="VbWk7s3L4KiK5fzlO7JD3Q5EYolJI7n5"',
            'content-type': 'application/x-www-form-urlencoded',
            'accept': 'application/json, text/plain, */*',
            'referer': 'https://resy.com/',
            'authority': 'api.resy.com',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.102 Safari/537.36',
        }
        self.username = username
        self.password = password
        self.venue = venue
        self.party = party
        self.date = date
        self.times = times
        self.datetimes = ["{} {}".format(self.date, t) for t in self.times]
        self.token, self.payment_method = self._login(username, password)

    def _login(self, username,password):
        """ Log into Resy """
        data = {'email': username, 'password': password}
        response = requests.post('https://api.resy.com/3/auth/password', headers=self.headers, data=data)
        res_data = response.json()
        auth_token = res_data['token']
        payment_method = '{\"id\":' + str(res_data['payment_method_id']) + '}'
        _LOGGER.info("Successfully logged in")
        return auth_token, payment_method

    def find_table(self):
        # Format and send request
        params = (
            ('x-resy-auth-token',  self.token),
            ('day', self.date),
            ('lat', '0'),
            ('long', '0'),
            ('party_size', self.party),
            ('venue_id',self.venue),
        )
        response = requests.get('https://api.resy.com/4/find',
                                headers=self.headers,
                                params=params)
        # Parse response
        details = response.json()
        if 'results' not in details:
            _LOGGER.error(response.text)
            raise ValueError(response.text)
        
        # Loop through returned slots to find the best one
        best_slot, best_score = None, len(self.datetimes) + 1
        for slot in details['results']['venues'][0]['slots']:
            slot_time = slot['date']['start']
            if slot_time in self.datetimes:
                score = self.datetimes.index(slot_time)
                if score < best_score:
                    best_slot = slot
                    best_score = score
        if best_slot:
            _LOGGER.info('Best slot: {}'.format(best_slot['date']['start']))
        else:
            _LOGGER.info('No valid slots found.')
        return best_slot

    def reserve(self):

        # Find table
        slot = self.find_table()
        if slot is None:
            return
        
        # Format and send request
        params = (
            ('x-resy-auth-token', self.token),
            ('config_id', slot['config']['token']),
            ('day', self.date),
            ('party_size', self.party),
        )
        response = requests.get('https://api.resy.com/3/details',
                                headers=self.headers,
                                params=params)
        # Parse response
        details = response.json()
        if 'book_token' not in details:
            _LOGGER.error(response.text)
            raise ValueError(response.text)
        
        # Make reservation request
        self.headers['x-resy-auth-token'] = self.token
        data = {
            'book_token': details['book_token']['value'],
            'struct_payment_method': self.payment_method,
            'source_id': 'resy.com-venue-details'
        }
        _LOGGER.info('Making Reservation')
        response = requests.post('https://api.resy.com/3/book',
                             headers=self.headers,
                             data=data)
        # Parse response
        details = response.json()
        if 'reservation_id' not in details:
            _LOGGER.error(response.text)
            raise ValueError(response.text)
        _LOGGER.info('Reservation ID: {}'.format(details['reservation_id']))


def readconfig():
    with open('config.json', 'rt') as f:
        return json.load(f)


def start_logging(verbose=False):
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', '%Y-%m-%d %H:%M:%S')
    if verbose:
        stdout = logging.StreamHandler(sys.stdout)
        stdout.setLevel(logging.INFO)
        stdout.setFormatter(formatter)
        root.addHandler(stdout)
    logfile = logging.FileHandler('res.log')
    logfile.setLevel(logging.INFO)
    logfile.setFormatter(formatter)
    root.addHandler(logfile)


if __name__ == '__main__':
    start_logging(verbose=True)
    resy = Resy(**readconfig())
    resy.reserve()
