import requests
import logging
import json
import sys
import os


_LOGGER = logging.getLogger(__name__)
_LOGGER.addHandler(logging.NullHandler())


def resy(username, password, venue, party, date, times, reserve):
    _LOGGER.info('Initializing application')
    headers = {
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
    username = username
    password = password
    venue = venue
    party = party
    date = date
    times = times
    datetimes = ['{} {}'.format(date, t) for t in times]

    ################################
    # Log Into Resy
    ################################

    data = {'email': username, 'password': password}
    response = requests.post('https://api.resy.com/3/auth/password', headers=headers, data=data)
    
    # Parse response
    details = response.json()
    if 'token' not in details:
        _LOGGER.error(response.text)
        raise ValueError(response.text)
    
    payment_method = '{\"id\":' + str(details['payment_method_id']) + '}'
    _LOGGER.info('Successfully logged in')
    token = details['token']
    payment_method = payment_method
    
    ################################
    # Search for Tables
    ################################

    # Format and send request
    params = (
        ('x-resy-auth-token',  token),
        ('day', date),
        ('lat', '0'),
        ('long', '0'),
        ('party_size', party),
        ('venue_id',venue),
    )
    response = requests.get('https://api.resy.com/4/find',
                            headers=headers,
                            params=params)
    # Parse response
    details = response.json()
    if 'results' not in details:
        _LOGGER.error(response.text)
        raise ValueError(response.text)
    
    # Log venue name
    venue_name = details['results']['venues'][0]['venue']['name']
    _LOGGER.info('Venue: {} ({})'.format(venue_name, venue))

    # Loop through returned slots to find the best one
    best_slot, best_score = None, len(datetimes) + 1
    for slot in details['results']['venues'][0]['slots']:
        slot_time = slot['date']['start']
        if slot_time in datetimes:
            score = datetimes.index(slot_time)
            if score < best_score:
                best_slot = slot
                best_score = score
    
    ################################
    # Make Reservation
    ################################
    if best_slot and reserve == 'True':
        _LOGGER.info('Best slot: {}'.format(best_slot['date']['start']))    
        params = (  # Format and send request
            ('x-resy-auth-token', token),
            ('config_id', best_slot['config']['token']),
            ('day', date),
            ('party_size', party),
        )
        response = requests.get('https://api.resy.com/3/details',
                                headers=headers,
                                params=params)
        # Parse response
        details = response.json()
        if 'book_token' not in details:
            _LOGGER.error(response.text)
            raise ValueError(response.text)
        
        # Make reservation request
        headers['x-resy-auth-token'] = token
        data = {
            'book_token': details['book_token']['value'],
            'struct_payment_method': payment_method,
            'source_id': 'resy.com-venue-details'
        }
        _LOGGER.info('Making Reservation')
        response = requests.post('https://api.resy.com/3/book',
                             headers=headers,
                             data=data)

        details = response.json()  # Parse response
        if 'reservation_id' not in details:
            _LOGGER.error(response.text)
            raise ValueError(response.text)
        _LOGGER.info('Reservation ID: {}'.format(details['reservation_id']))
        return True
    else:
        _LOGGER.info('No valid slots found.')
    return False


def read_config():
    config_file = os.path.join(os.path.dirname(__file__), 'config.json')
    with open(config_file, 'rt') as f:
        return json.load(f)


def read_success():
    """Returns true if success file exists"""
    success_file = os.path.join(os.path.dirname(__file__), 'success')
    return os.path.exists(success_file)


def write_success():
    """Creates success file"""
    success_file = os.path.join(os.path.dirname(__file__), 'success')
    with open(success_file, 'wt') as f:
        f.write('success')


def start_logging(verbose=False):
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', '%Y-%m-%d %H:%M:%S')
    if verbose:
        # Create handler for stdout logging
        stdout = logging.StreamHandler(sys.stdout)
        stdout.setLevel(logging.INFO)
        stdout.setFormatter(formatter)
        root.addHandler(stdout)
    # Create handler for log file
    file_name = os.path.join(os.path.dirname(__file__), 'res.log')
    logfile = logging.FileHandler(file_name)
    logfile.setLevel(logging.INFO)
    logfile.setFormatter(formatter)
    root.addHandler(logfile)


if __name__ == '__main__':
    start_logging(verbose=False)
    if read_success():
        _LOGGER.info('Success file found - Skipping')
    else:
        _LOGGER.info('No success file found - Proceeding')
        success = resy(**read_config())
        if success:
            write_success()
            _LOGGER.info('Created success file')
    _LOGGER.info('Exiting')