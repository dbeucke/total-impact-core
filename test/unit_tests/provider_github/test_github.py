from totalimpact.models import Metrics, Aliases
from totalimpact.config import Configuration
from totalimpact.providers.github import Github
from totalimpact.providers.provider import Provider, ProviderClientError, ProviderServerError

import os, unittest

# prepare a monkey patch to override the http_get method of the Provider
class DummyResponse(object):
    def __init__(self, status, content):
        self.status_code = status
        self.text = content

def get_memberitems_user_html(self, url, headers=None, timeout=None):
    f = open(GITHUB_MEMBERITEMS_USER_HTML, "r")
    return DummyResponse(200, f.read())

def get_memberitems_orgs_html(self, url, headers=None, timeout=None):
    f = open(GITHUB_MEMBERITEMS_ORGS_HTML, "r")
    return DummyResponse(200, f.read())

# dummy Item class
class Item(object):
    def __init__(self, aliases=None):
        self.aliases = aliases

CWD, _ = os.path.split(__file__)

GITHUB_MEMBERITEMS_USER_HTML = os.path.join(CWD, "sample_extract_user_metrics.json")
GITHUB_MEMBERITEMS_ORGS_HTML = os.path.join(CWD, "sample_extract_orgs_metrics.json")
DOI = "10.5061/dryad.7898"

class Test_Github(unittest.TestCase):

    def setUp(self):
        self.config = Configuration()
        self.old_http_get = Provider.http_get
    
    def tearDown(self):
        Provider.http_get = self.old_http_get
    
    def test_01_init(self):
        # first ensure that the configuration is valid
        assert len(self.config.cfg) > 0
        
        # can we get the config file
        dcfg = None
        for p in self.config.providers:
            if p["class"].endswith("github.Github"):
                dcfg = p["config"]
        print dcfg
        assert os.path.isfile(dcfg)
        
        # instantiate the configuration
        dconf = Configuration(dcfg, False)
        assert len(dconf.cfg) > 0
        
        # basic init of provider
        provider = Github(dconf, self.config)
        assert provider.config is not None
        
        ## FIXME implement state
        #assert provider.state is not None

        assert provider.id == dconf.id
        
    def test_02_implements_interface(self):
        # ensure that the implementation has all the relevant provider methods
        dcfg = None
        for p in self.config.providers:
            if p["class"].endswith("github.Github"):
                dcfg = p["config"]
        dconf = Configuration(dcfg, False)
        provider = Github(dconf, self.config)
        
        # must have the four core methods
        assert hasattr(provider, "member_items")
        assert hasattr(provider, "aliases")
        assert hasattr(provider, "metrics")
        assert hasattr(provider, "provides_metrics")
    

    def test_04_member_items(self):        
        dcfg = None
        for p in self.config.providers:
            if p["class"].endswith("github.Github"):
                dcfg = p["config"]
        dconf = Configuration(dcfg, False)
        provider = Github(dconf, self.config)
        

        Provider.http_get = get_memberitems_user_html
        members = provider.member_items("egonw", "githubUser")
        assert len(members) >= 30, (len(members), members)

        Provider.http_get = get_memberitems_orgs_html
        members = provider.member_items("bioperl", "githubOrg")
        assert len(members) >= 32, (len(members), members)
