from test.unit_tests.providers import common
from test.unit_tests.providers.common import ProviderTestCase
from totalimpact.providers.provider import Provider, ProviderContentMalformedError

import os
import collections
from nose.tools import assert_equals, raises, nottest

datadir = os.path.join(os.path.split(__file__)[0], "../../../extras/sample_provider_pages/bibtex")
SAMPLE_EXTRACT_MEMBER_ITEMS_PAGE = os.path.join(datadir, "Vision.bib")

class TestBibtex(ProviderTestCase):

    provider_name = "bibtex"

    testitem_members = "egonw"

    def setUp(self):
        ProviderTestCase.setUp(self) 

    def test_extract_members_success(self):        
        file_contents = open(SAMPLE_EXTRACT_MEMBER_ITEMS_PAGE, "r").read()
        pages = self.provider.paginate(file_contents)
        members = self.provider.member_items(pages[1])
        print members
        assert_equals(set(members), set([('doi', u'10.1093/bioinformatics/btm001'), ('doi', u'10.1104/pp.103.023085'), ('doi', u'10.1093/bioinformatics/btg1008')]))

    def test_paginate(self):
        file_contents = open(SAMPLE_EXTRACT_MEMBER_ITEMS_PAGE, "r").read()
        response = self.provider.paginate(file_contents)
        assert_equals(len(response), 17)
