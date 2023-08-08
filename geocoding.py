import json
from collections import namedtuple
from typing import Any

import requests

Coordinates = namedtuple('Coordinates', ['lat', 'long'])

GEOCODER_FORMAT_URL = "https://geocoding.geo.census.gov/geocoder/locations/address"

def get_coords_from_address(address: str, city: str = "", state: str = "", zip: str = ""):
    # set up the query params
    params = {
        'format': 'json',
        'benchmark': '2020',
        'street': address,
    }

    for key, value in dict(city=city, state=state, zip=zip).items():
        if len(value):
            params[key] = value

    # do the actual http request and raise error if necessary
    try:
        r = requests.get(GEOCODER_FORMAT_URL, params=params)
        r.raise_for_status()
    except Exception as e:
        # decode json and raise error if necessary
        response = json.loads(r.content)
        if response.get("errors"):
            raise ValueError(response['errors'])
        else:
            raise e
    
    # rip the coordinates out of the json
    response = json.loads(r.content)

    if not response.get("result"):
        raise ValueError("Census geocoder returned unexpected JSON: {0}".format(r.content))
    if not len(response['result'].get("addressMatches")):
        raise ValueError("Invalid address: {0} {1} {2} {3}".format(address, city, state, zip))
    
    raw_coords = response['result']['addressMatches'][0]['coordinates']
    
    return Coordinates(round(raw_coords['y'], 4), round(raw_coords['x'], 4))

if __name__ == "__main__":
    coords = get_coords_from_address("1600 Pennsylvania Avenue", "Washington", "DC")
    print(coords)