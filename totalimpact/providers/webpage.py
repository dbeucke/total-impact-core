from totalimpact.providers import provider
from totalimpact.providers.provider import Provider, ProviderContentMalformedError
import lxml.html

import logging
logger = logging.getLogger('ti.providers.webpage')

class Webpage(Provider):  

    example_id = ("url", "http://total-impact.org/")

    biblio_url_template = "%s"
    provenance_url_template = "%s"
    descr = "Information scraped from webpages by total-impact"
    url = "http://total-impact.org"


    def __init__(self):
        super(Webpage, self).__init__()

    def is_relevant_alias(self, alias):
        (namespace, nid) = alias
        return("url" == namespace)


    # use lxml because is html

    def _extract_biblio(self, page, id=None):
        #dict_of_keylists = {
        #    'title' : ['html', 'head', 'title'],
        #    'h1' : ['h1']
        #}

        biblio_dict = {}
        parsed_html = lxml.html.document_fromstring(page.encode("utf-8"))
        

        try:
            response = parsed_html.find(".//title").text
            if response:
                biblio_dict["title"] = response
        except AttributeError:
            pass

        try:
            response = parsed_html.find(".//h1").text
            if response:
                biblio_dict["h1"] = response
        except AttributeError:
            pass


        return biblio_dict    
