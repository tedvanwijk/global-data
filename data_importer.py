import os
import requests

class DataImporter:
    API_URL = 'https://data-portal.s5p-pal.com/api/'

    def __init__(self):
        super(DataImporter, self).__init__()

    def get_collections(self):
        result = requests.get(os.path.join(self.API_URL, 's5p-l3')).json()
        links = []
        for link in result['links']:
            if link['rel'] == 'child':
                links.append(link)
        return links
    
    def get_links(self, href):
        result = requests.get(href).json()
        return result['links']
    
    def get_links_with_api_url(self, href):
        result = requests.get(os.path.join(self.API_URL, href)).json()
        return result['links']
    
    def get_json(self, href):
        result = requests.get(href).json()
        return result