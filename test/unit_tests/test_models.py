from nose.tools import raises, assert_equals, nottest
import os, unittest, json, time
from copy import deepcopy

from totalimpact import models
from totalimpact import dao, api

TEST_COLLECTION = {
    "id": "uuid-goes-here",
    "collection_name": "My Collection",
    "owner": "abcdef",
    "created": 1328569452.406,
    "last_modified": 1328569492.406,
    "item_tiids": ["origtiid1", "origtiid2"] 
    }

TEST_ALIAS = {
    "tiid":"0987654321",
    "title":["Why Most Published Research Findings Are False"],
    "url":["http://www.plosmedicine.org/article/info:doi/10.1371/journal.pmed.0020124"],
    "doi": ["10.1371/journal.pmed.0020124"],
    "created": 12387239847.234,
    "last_modified": 1328569492.406
    }

TEST_ALIAS_CANONICAL = {
    "tiid":"0987654321",
    "title":["Why Most Published Research Findings Are False"],
    "url":["http://www.plosmedicine.org/article/info:doi/10.1371/journal.pmed.0020124"],
    "doi": ["10.1371/journal.pmed.0020124"],
    "created": 12387239847.234,
    "last_modified": 1328569492.406
    }

TEST_SNAP = {
    "id": "mendeley:readers",
    "value": 16,
    "created": 1233442897.234,
    "last_modified": 1328569492.406,
    "provenance_url": ["http://api.mendeley.com/research/public-chemical-compound-databases/"],
    "static_meta": {
        "display_name": "readers",
        "provider": "Mendeley",
        "provider_url": "http://www.mendeley.com/",
        "description": "Mendeley readers: the number of readers of the article",
        "icon": "http://www.mendeley.com/favicon.ico",
        "category": "bookmark",
        "can_use_commercially": "0",
        "can_embed": "1",
        "can_aggregate": "1",
        "other_terms_of_use": "Must show logo and say 'Powered by Santa'"
        }
    }

TEST_SNAP_HASH = "5771be360d7f79aba51a2824636fef6f"

TEST_METRICS = {
    "update_meta": {
        "mendeley": {
            "last_modified": 128798498.234,
            "last_requested": 2139841098.234,
            "ignore": False
            }
        },
        "bucket":{
            TEST_SNAP_HASH: TEST_SNAP
        }
    }


TEST_BIBLIO = {
        "title": "An extension of de Finetti's theorem", 
        "journal": "Advances in Applied Probability", 
        "author": [
            "Pitman, J"
            ], 
        "collection": "pitnoid", 
        "volume": "10", 
        "id": "p78",
        "year": "1978",
        "pages": "268 to 270"
    }


TEST_ITEM = {
    "created": 1330260456.916,
    "last_modified": 12414214.234,
    "last_requested": 124141245.234, 
    "aliases": TEST_ALIAS,
    "metrics": TEST_METRICS,
    "biblio": TEST_BIBLIO
    }
    
TEST_DB_NAME = "test_models"

class TestItem():

    def setUp(self):
        self.d = dao.Dao(TEST_DB_NAME)
        
        self.d.create_new_db_and_connect(TEST_DB_NAME)
        self.d.get = lambda id: TEST_ITEM
        def fake_save(data, id):
            self.input = data
        self.d.update_item = fake_save

        self.providers = api.provider_objects

    def test_new_testing_class(self):
        assert True

    def test_mock_dao(self):
        assert_equals(self.d.get("123"), TEST_ITEM)

    def test_item_init(self):
        i = models.Item(self.d)
        assert_equals(len(i.id), 32) # made a uuid, yay

    def test_item_load(self):
        i = models.Item(self.d, id="123")
        i.load()
        assert_equals(i.aliases.as_dict(), TEST_ALIAS_CANONICAL)
        assert_equals(i.created, TEST_ITEM["created"])

    @raises(LookupError)
    def test_load_with_nonexistant_item_fails(self):
        i = models.Item(self.d, id="123")
        self.d.get = lambda id: None # that item doesn't exist in the db
        i.load()

    def test_item_save(self):
        i = models.Item(self.d, id="123")

        # load all the values from the item_seed into the test item.
        for key in TEST_ITEM:
            setattr(i, key, TEST_ITEM[key])
        i.save()

        assert_equals(i.aliases, TEST_ALIAS)

        seed = deepcopy(TEST_ITEM)
        seed["_id"] = "123"
        # the fake dao puts the doc-to-save in the self.input var.
        assert_equals(self.input, seed)



class TestCollection():

    def setUp(self):        
        self.d = dao.Dao(TEST_DB_NAME)
        self.d.create_new_db_and_connect(TEST_DB_NAME)

    def test_mock_dao(self):
        self.d.get = lambda id: deepcopy(TEST_COLLECTION)
        assert_equals(self.d.get("SomeCollectionId"), TEST_COLLECTION)

    def test_collection_init(self):
        c = models.Collection(self.d)
        assert_equals(len(c.id), 32) # made a uuid, yay

    def test_collection_add_items(self):
        c = models.Collection(self.d, seed=deepcopy(TEST_COLLECTION))
        c.add_items(["newtiid1", "newtiid2"])
        assert_equals(c.item_ids(), [u'origtiid1', u'origtiid2', 'newtiid1', 'newtiid2'])

    def test_collection_remove_item(self):
        c = models.Collection(self.d, seed=deepcopy(TEST_COLLECTION))
        c.remove_item("origtiid1")
        assert_equals(c.item_ids(), ["origtiid2"])

    def test_collection_load(self):
        self.d.get = lambda id: deepcopy(TEST_COLLECTION)
        c = models.Collection(self.d, id="SomeCollectionId")
        c.load()
        assert_equals(c.collection_name, "My Collection")
        assert_equals(c.item_ids(), [u'origtiid1', u'origtiid2'])

    @raises(LookupError)
    def test_load_with_nonexistant_collection_fails(self):
        self.d.get = lambda id: None # that item doesn't exist in the db
        c = models.Collection(self.d, id="AnUnknownCollectionId")
        c.load()

    def test_collection_save(self):
        # this fake save method puts the doc-to-save in the self.input variable
        def fake_save(data, id):
            self.input = data
        self.d.update_item = fake_save

        c = models.Collection(self.d)

        # load all the values from the item_seed into the test item.
        for key in TEST_COLLECTION:
            setattr(c, key, TEST_COLLECTION[key])
        c.save()

        seed = deepcopy(TEST_COLLECTION)
        # the dao changes the contents to give the id variable the leading underscore expected by couch
        seed["_id"] = seed["id"]
        del(seed["id"])

        # check to see if the fake save method did in fact "save" the collection as expected
        assert_equals(self.input, seed)



class TestModelObjects(unittest.TestCase):

    def setUp(self):
        self.providers = api.provider_objects

        pass
        
    def tearDown(self):
        pass

    def test_01_aliases_init(self):
        a = models.Aliases()
        
        # a blank init always sets an id
        assert len(a.data.keys()) == 1
        assert a.data["tiid"] is not None
        assert a.tiid is not None
        assert a.tiid == a.data["tiid"]
        
        a = models.Aliases("123456")
        
        # check our id has propagated
        assert len(a.data.keys()) == 1
        assert a.data["tiid"] == "123456"
        assert a.tiid == "123456"
        
        a = models.Aliases(seed=TEST_ALIAS)
        
        assert len(a.data.keys()) == 6
        assert a.tiid == "0987654321"
        assert a.title == ["Why Most Published Research Findings Are False"]
        assert a.url == ["http://www.plosmedicine.org/article/info:doi/10.1371/journal.pmed.0020124"]
        assert a.doi == ["10.1371/journal.pmed.0020124"]
        assert a.created == 12387239847.234
        assert a.last_modified == 1328569492.406
        
        a = models.Aliases(tiid="abcd", doi="10.1371/journal/1", title=["First", "Second"])
        
        assert len(a.data.keys()) == 3
        assert a.tiid == "abcd"
        assert a.doi == ["10.1371/journal/1"]
        assert a.title == ["First", "Second"]
        
    def test_03_aliases_add(self):
        a = models.Aliases()
        a.add_alias("foo", "id1")
        a.add_alias("foo", "id2")
        a.add_alias("bar", "id1")
        
        # check the data structure is correct
        expected = {"tiid": a.tiid, "foo":["id1", "id2"], "bar":["id1"]}
        assert a.data == expected, a.data
        
        to_add = [
            ("baz", "id1"),
            ("baz", "id2"),
            ("foo", "id3"),
            ("bar", "id1")
        ]
        a.add_unique(to_add)
        
        # check the data structure is correct
        expected = {"tiid": a.tiid, 
                    "foo":["id1", "id2", "id3"], 
                    "bar":["id1"], 
                    "baz" : ["id1", "id2"]}
        assert a.data == expected, a.data
        
    def test_aliases_add_potential_errors(self):
        # checking for the string/list type bug
        a = models.Aliases()
        a.data["doi"] = "error"
        a.add_alias("doi", "noterror")
        assert a.data['doi'] == ["error", "noterror"], a.data['doi']
        
    def test_04_aliases_single_namespaces(self):
        a = models.Aliases(seed=TEST_ALIAS)
        
        ids = a.get_ids_by_namespace("doi")
        assert ids == ["10.1371/journal.pmed.0020124"]
        
        ids = a.get_ids_by_namespace("url")
        assert ids == ["http://www.plosmedicine.org/article/info:doi/10.1371/journal.pmed.0020124"]
        
        aliases = a.get_aliases_list()
        assert len(aliases) == 4
        
        aliases = a.get_aliases_list("doi")
        assert aliases == [("doi", "10.1371/journal.pmed.0020124")], aliases
        
        aliases = a.get_aliases_list("title")
        assert aliases == [("title", "Why Most Published Research Findings Are False")]
        
    def test_05_aliases_missing(self):
        a = models.Aliases(seed=TEST_ALIAS)
        
        failres = a.get_ids_by_namespace("my_missing_namespace")
        assert failres == [], failres
        
        failres = a.get_aliases_list("another_missing_namespace")
        assert failres == [], failres
        
    def test_06_aliases_multi_namespaces(self):
        a = models.Aliases(seed=TEST_ALIAS)
        
        ids = a.get_aliases_list(["doi", "url"])
        assert ids == [("doi", "10.1371/journal.pmed.0020124"),
                        ("url", "http://www.plosmedicine.org/article/info:doi/10.1371/journal.pmed.0020124")], ids
    
    def test_07_aliases_dict(self):
        a = models.Aliases(seed=TEST_ALIAS)
        assert a.get_aliases_dict() == TEST_ALIAS_CANONICAL
    
    def test_08_alias_seed_validation(self):
        # FIXME: seed validation has not yet been implemented.  What does it
        # do, and how should it be tested?
        pass
    
    """{
        "id": "mendeley:readers",
        "value": 16,
        "created": 1233442897.234,
        "last_modified": 1328569492.406,
        "provenance_url": ["http://api.mendeley.com/research/public-chemical-compound-databases/"],
        "static_meta": {
            "display_name": "readers"
            "provider": "Mendeley",
            "provider_url": "http://www.mendeley.com/",
            "description": "Mendeley readers: the number of readers of the article",
            "icon": "http://www.mendeley.com/favicon.ico",
            "category": "bookmark",
            "can_use_commercially": "0",
            "can_embed": "1",
            "can_aggregate": "1",
            "other_terms_of_use": "Must show logo and say 'Powered by Santa'",
        }
    }
    """
    
    def test_09_metric_snap_init(self):
        snap_simple = models.MetricSnap(seed=deepcopy(TEST_SNAP))
        
        assert snap_simple.id == "mendeley:readers"
        assert snap_simple.value() == 16
        assert snap_simple.created == 1233442897.234
        assert snap_simple.last_modified == 1328569492.406
        assert snap_simple.provenance() == ["http://api.mendeley.com/research/public-chemical-compound-databases/"]
        assert snap_simple.static_meta() == TEST_SNAP['static_meta']
        assert snap_simple.data == TEST_SNAP
        
        now = time.time()
        snap = models.MetricSnap(id="richard:metric", 
                                    value=23, created=now, last_modified=now,
                                    provenance_url="http://total-impact.org/")
        assert snap.id == "richard:metric"
        assert snap.value() == 23
        assert snap.created == now
        assert snap.last_modified == now
        assert snap.provenance() == ["http://total-impact.org/"]
        assert len(snap.static_meta()) == 0
        
        snap_from_seed = models.MetricSnap(id="richard:metric", 
                                    value=23, created=now, last_modified=now,
                                    provenance_url="http://total-impact.org/",
                                    static_meta=TEST_SNAP['static_meta'])
        assert snap_from_seed.static_meta() == TEST_SNAP['static_meta']
    
    def test_10_metric_snap_get_set(self):
        snap = models.MetricSnap(seed=deepcopy(TEST_SNAP))
        stale = time.time()
        
        assert snap.value() == 16
        snap.value(17)
        assert snap.value() == 17
        assert snap.last_modified > stale
        stale = snap.last_modified
        
        assert snap.static_meta() == TEST_SNAP['static_meta']
        snap.static_meta({"test": "static_meta"})
        assert snap.static_meta() == {"test" : "static_meta"}
        assert snap.last_modified > stale
        stale = snap.last_modified
        
        assert snap.provenance() == ["http://api.mendeley.com/research/public-chemical-compound-databases/"]
        snap.provenance("http://total-impact.org")
        assert snap.provenance() == ["http://api.mendeley.com/research/public-chemical-compound-databases/", "http://total-impact.org"]
        assert snap.last_modified > stale
        
        snap.provenance(["http://total-impact.org"])
        assert snap.provenance() == ["http://total-impact.org"], snap.provenance()
    
    """
    {
        "update_meta": {
            "PROVIDER_ID": {
                "last_modified": 128798498.234,
                "last_requested": 2139841098.234,
                "ignore": false
            }
        },
        "bucket":[
            "LIST OF PROVIDER METRIC OBJECTS"
        ]
    }
    """
    
    def test_11_metrics_init(self):
        m = models.Metrics(providers=self.providers)
        
        assert len(m.update_meta()) >= 3, m.update_meta()
        assert len(m.list_metric_snaps()) == 0
        
        m = models.Metrics(deepcopy(TEST_METRICS), providers=self.providers)
        
        assert len(m.update_meta()) >= 4, m.update_meta()
        assert len(m.list_metric_snaps()) == 1
        
        assert m.update_meta()['mendeley'] is not None
        assert m.update_meta()['mendeley']['last_modified'] == 128798498.234
        assert m.update_meta()['mendeley']['last_requested'] != 0  # don't know exactly what it will be
        assert not m.update_meta()['mendeley']['ignore']
        
        assert m.update_meta()['wikipedia'] is not None
        assert m.update_meta()['wikipedia']['last_modified'] == 0
        assert m.update_meta()['wikipedia']['last_requested'] != 0 # don't know exactly what it will be
        assert not m.update_meta()['wikipedia']['ignore']
        
        metric_snaps = m.list_metric_snaps()[0]
        assert metric_snaps == models.MetricSnap(seed=deepcopy(TEST_SNAP)), (metric_snaps.data, TEST_SNAP)
        
    def test_12_metrics_update_meta(self):
        m = models.Metrics(TEST_METRICS, providers=self.providers)
        assert len(m.update_meta()) >= 4, m.update_meta()
        assert m.update_meta()['mendeley'] is not None
        
        assert m.update_meta("mendeley") is not None
        assert m.update_meta("mendeley") == m.update_meta()['mendeley']
    
    def test_13_metrics_add_metric_snap(self):
        now = time.time()
        
        m = models.Metrics(deepcopy(TEST_METRICS), providers=self.providers)
        new_seed = deepcopy(TEST_SNAP)
        new_seed['value'] = 25
        m.add_metric_snap(models.MetricSnap(seed=new_seed))
        
        assert len(m.update_meta()) >= 4, (m.update_meta(), len(m.update_meta()))
        assert len(m.list_metric_snaps()) == 2
        assert len(m.list_metric_snaps(new_seed['id'])) == 2
        
        assert m.update_meta('mendeley')['last_modified'] > now
        
    def test_14_metrics_list_metric_snaps(self):
        m = models.Metrics(deepcopy(TEST_METRICS), providers=self.providers)
        
        assert len(m.list_metric_snaps()) == 1
        assert m.list_metric_snaps("mendeley:readers")[0] == models.MetricSnap(seed=deepcopy(TEST_SNAP))
        
        assert len(m.list_metric_snaps("Some:other")) == 0
    
    def test_15_metrics_canonical(self):
        m = models.Metrics(providers=self.providers)
        
        simple_dict = {"one" : 1, "two" : 2, "three" : 3}
        simple_expected = "one1three3two2"
        canon = m._canonical_repr(simple_dict)
        assert canon == simple_expected, (canon, simple_expected)
        
        nested_dict = { "one" : 1, "two" : { "three" : 3, "four" : 4 } }
        nested_expected = "one1two{four4three3}"
        canon = m._canonical_repr(nested_dict)
        assert canon == nested_expected, (canon, nested_expected)
        
        nested_list = {"one" : 1, "two" : ['c', 'b', 'a']}
        list_expected = "one1two[abc]"
        canon = m._canonical_repr(nested_list)
        assert canon == list_expected, (canon, list_expected)
        
        nested_both = {"zero" : 0, "one" : {"two" : 2, "three" : 3}, "four" : [7,6,5]}
        both_expected = "four[567]one{three3two2}zero0"
        canon = m._canonical_repr(nested_both)
        assert canon == both_expected, (canon, both_expected)
        
    def test_15_metrics_hash(self):
        m = models.Metrics(providers=self.providers)
        metric_snap = models.MetricSnap(seed=deepcopy(TEST_SNAP))
        
        hash = m._hash(metric_snap)
        assert hash == TEST_SNAP_HASH, (hash, TEST_SNAP_HASH)
        
        m.add_metric_snap(metric_snap)
        assert m.data['bucket'].keys()[0] == TEST_SNAP_HASH
    
    # FIXME: Biblio has not been fully explored yet, so no tests for it
    



    

        
        
        
