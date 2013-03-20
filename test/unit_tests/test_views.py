import unittest, json, uuid
from copy import deepcopy
from urllib import quote_plus
from nose.tools import assert_equals, nottest, assert_greater

from totalimpact import app, dao, views, tiredis
from totalimpact.providers.dryad import Dryad
import os


TEST_DRYAD_DOI = "10.5061/dryad.7898"
PLOS_TEST_DOI = "10.1371/journal.pone.0004803"
GOLD_MEMBER_ITEM_CONTENT = ["MEMBERITEM CONTENT"]
TEST_COLLECTION_ID = "TestCollectionId"
TEST_COLLECTION_TIID_LIST = ["tiid1", "tiid2"]
TEST_COLLECTION_TIID_LIST_MODIFIED = ["tiid1", "tiid_different"]

COLLECTION_SEED = json.loads("""{
    "id": "uuid-goes-here",
    "collection_name": "My Collection",
    "owner": "abcdef",
    "created": 1328569452.406,
    "last_modified": 1328569492.406,
    "alias_tiids": {"doi:123": "origtiid1", "github:frank":"origtiid2"}
}""")
COLLECTION_SEED_MODIFIED = deepcopy(COLLECTION_SEED)
COLLECTION_SEED_MODIFIED["alias_tiids"] = dict(zip(["doi:1", "doi:2"], TEST_COLLECTION_TIID_LIST_MODIFIED))

def MOCK_member_items(self, query_string, url=None, cache_enabled=True):
    return(GOLD_MEMBER_ITEM_CONTENT)

# ensures that all the functions in the views.py module will use a local db,
# which we can in turn use for these unit tests.
mydao = views.set_db("http://localhost:5984", os.getenv("CLOUDANT_DB"))
# do the same for redis, handing it local redis and instruction to use "DB 8" 
# to isolate unit testing
myredis = views.set_redis("redis://localhost:6379", db=8)

class ViewsTester(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        pass

    def setUp(self):
        """
        This test item is a lightly-modified version of a real doc from our
        demo collection; it's available at http://total-impact-core.herokuapp.com/collection/kn5auf
        """
        test_item = '''
            {
            "_id": "1aff9dfebea711e1bdf912313d1a5e63",
            "_rev": "968-c7891982fca2ea41346a20b80c2b888d",
            "aliases": {
                "doi": [
                    "10.5061/dryad.j1fd7"
                ],
                "title": [
                    "Data from: Data archiving is a good use of research funds",
                    "data from: data archiving is a good  investment"
                ],
                "url": [
                    "http://datadryad.org/handle/10255/dryad.33537",
                    "http://hdl.handle.net/10255/dryad.33537"
                ]
            },
            "biblio": {
                "authors": "Piwowar, Vision, Whitlock, Piwowar, Vision, Whitlock, Piwowar, Vision, Whitlock",
                "genre": "dataset",
                "h1": "Data from: Data archiving is a good  investment",
                "repository": "Dryad Digital Repository",
                "title": "Data from: Data archiving is a good  investment",
                "year": "2011"
            },
            "created": "2012-06-25T09:21:11.960271",
            "currently_updating": false,
            "last_modified": "2012-11-18T04:57:40.539053",
            "metrics": {
                "delicious:bookmarks": {
                    "provenance_url": "http://www.delicious.com/url/4794ddb7a3e934ba23165af65fcfa9cd",
                    "static_meta": {
                        "description": "The number of bookmarks to this artifact (maximum=100).",
                        "display_name": "bookmarks",
                        "icon": "http://www.delicious.com/favicon.ico",
                        "provider": "Delicious",
                        "provider_url": "http://www.delicious.com/"
                    },
                    "values": {
                        "raw": 1
                    }
                },
                "dryad:total_downloads": {
                    "provenance_url": "http://dx.doi.org/10.5061/dryad.j1fd7",
                    "static_meta": {
                        "description": "Dryad total downloads: combined number of downloads of the data package and data files",
                        "display_name": "total downloads",
                        "icon": "http:\\/\\/datadryad.org\\/favicon.ico",
                        "provider": "Dryad",
                        "provider_url": "http:\\/\\/www.datadryad.org\\/"
                    },
                    "values": {
                        "dryad": {
                            "CI95_lower": 91,
                            "CI95_upper": 98,
                            "estimate_lower": 96,
                            "estimate_upper": 96
                        },
                        "raw": 207,
                        "raw_history": {
                            "2012-06-25T09:21:16.027149": 132,
                            "2012-06-26T18:05:19.598432": 132,
                            "2012-06-26T20:10:16.858294": 132
                        }
                    }
                }
            },
            "type": "item"
        }
        '''

        test_api_user = """
                {
           "_id": "yDnhDa3fdFxxEsQnzYnA96",
           "created": "2012-11-19T16:11:17.713812",
           "current_key": "validkey",
           "registered_items": {
               "doi:10.1371/journal.pcbi.1000355": {
                   "tiid": "b229e24abec811e1887612313d1a5e63",
                   "registered_date": "2012-12-29T18:11:20.870026"
               }
           },
           "max_registered_items": 1000,
           "key_history": {
               "2012-11-19T16:11:17.713812": "validkey"
           },
           "meta": {
               "planned_use": "individual CV",
               "example_url": "",
               "api_key_owner": "Superman",
               "organization": "individual",
               "email": "superman@secret.com"
           },
           "type": "api_user"
        }
        """

        # hacky way to delete the "ti" db, then make it fresh again for each test.
        temp_dao = dao.Dao("http://localhost:5984", os.getenv("CLOUDANT_DB"))
        temp_dao.delete_db(os.getenv("CLOUDANT_DB"))
        self.d = dao.Dao("http://localhost:5984", os.getenv("CLOUDANT_DB"))
        self.d.update_design_doc()

        self.d.save(json.loads(test_item))
        self.d.save(json.loads(test_api_user))

        #postgres
        self.postgres_d = dao.PostgresDao("postgres://localhost/unittests")
        self.postgres_d.create_tables()

        # do the same thing for the redis db.  We're using DB 8 for unittests.
        self.r = tiredis.from_url("redis://localhost:6379", db=8)
        self.r.flushdb()

        #setup api test client
        self.app = app
        self.app.testing = True
        self.client = self.app.test_client()

    def tearDown(self):
        self.postgres_d.close()

        pass

    @classmethod
    def tearDownClass(cls):
        pass

class DaoTester(unittest.TestCase):
    def test_dao(self):
        assert_equals(mydao.db.name, os.getenv("CLOUDANT_DB"))

class TestApiKeys(ViewsTester):
    def test_does_not_require_key_if_preversioned_url(self):
        resp = self.client.get("/")
        assert_equals(resp.status_code, 200)

    def test_forbidden_if_no_key_in_v1(self):
        resp = self.client.get("/v1/provider")
        assert_equals(resp.status_code, 403)

    def test_ok_if_registered_key_in_v1(self):
        resp = self.client.get("/v1/provider?key=validkey")
        assert_equals(resp.status_code, 200)

    def test_forbidden_if_unregistered_key_in_v1(self):
        resp = self.client.get("/v1/provider?key=invalidkey")
        assert_equals(resp.status_code, 403)

class TestMemberItems(ViewsTester):

    def setUp(self):                 
        super(TestMemberItems, self).setUp()
        # Mock out relevant methods of the Dryad provider
        self.orig_Dryad_member_items = Dryad.member_items
        Dryad.member_items = MOCK_member_items

    def tearDown(self):
        Dryad.member_items = self.orig_Dryad_member_items

    def test_memberitems_get(self):        
        response = self.client.get('/provider/dryad/memberitems/Otto%2C%20Sarah%20P.?method=sync')
        print response
        print response.data
        assert_equals(response.status_code, 200)
        assert_equals(json.loads(response.data)["memberitems"], GOLD_MEMBER_ITEM_CONTENT)
        assert_equals(response.mimetype, "application/json")

    def test_file_parsing(self):
        datadir = os.path.join(os.path.split(__file__)[0], "../../extras/sample_provider_pages/bibtex")
        path = os.path.join(datadir, "Vision.bib")
        bibtex_str = open(path, "r").read()


class TestProvider(ViewsTester):

        def test_exists(self):
            resp = self.client.get("/provider")
            assert resp

        def test_gets_delicious_static_meta(self):
            resp = self.client.get("/provider")
            md = json.loads(resp.data)
            print md["delicious"]
            assert md["delicious"]['metrics']["bookmarks"]["description"]



class TestItem(ViewsTester):

    def test_item_post_unknown_tiid(self):
        response = self.client.post('/item/doi/AnIdOfSomeKind/')
        print response
        print response.data
        assert_equals(response.status_code, 201)  #Created
        assert_equals(len(json.loads(response.data)), 24)
        assert_equals(response.mimetype, "application/json")

    def test_item_post_success(self):
        resp = self.client.post('/item/doi/' + quote_plus(TEST_DRYAD_DOI))
        tiid = json.loads(resp.data)

        response = self.client.get('/item/' + tiid)
        assert_equals(response.status_code, 210) # 210 created, but not done updating...
        assert_equals(response.mimetype, "application/json")
        saved_item = json.loads(response.data)

        assert_equals([unicode(TEST_DRYAD_DOI)], saved_item["aliases"]["doi"])


    def test_item_get_missing_no_create_param_returns_404(self):
        url = '/v1/item/doi/' + quote_plus(TEST_DRYAD_DOI) + "?key=validkey"
        response = self.client.get(url)
        assert_equals(response.status_code, 404) # created but still updating

    def test_item_get_create_param_makes_new_item(self):
        url = '/v1/item/doi/' + quote_plus(TEST_DRYAD_DOI) + "?key=validkey&register=true"
        response = self.client.get(url)
        assert_equals(response.status_code, 210) # created and still updating
        item_info = json.loads(response.data)
        assert_equals(item_info["aliases"]["doi"][0], TEST_DRYAD_DOI)

    def test_v1_item_post_success(self):
        url = '/v1/item/doi/' + quote_plus(TEST_DRYAD_DOI) + "?key=validkey"
        response = self.client.post(url)
        assert_equals(response.status_code, 201)
        assert_equals(json.loads(response.data), "ok")

    def test_item_get_success_realid(self):
        # First put something in
        response = self.client.get('/item/doi/' + quote_plus(TEST_DRYAD_DOI))
        tiid = response.data
        print response
        print tiid

    def test_v1_item_get_success_realid(self):
        # First put something in
        url = '/v1/item/doi/' + quote_plus(TEST_DRYAD_DOI) + "?key=validkey"
        response_post = self.client.post(url)
        # now check response
        response_get = self.client.get(url)
        assert_equals(response_get.status_code, 210)
        expected = {u'created': u'2012-11-06T19:57:15.937961', u'_rev': u'1-05e5d8a964a0fe9af4284a2a7804815f', u'currently_updating': True, u'metrics': {}, u'last_modified': u'2012-11-06T19:57:15.937961', u'biblio': {u'genre': u'dataset'}, u'_id': u'jku42e6ogs8ghxbr7p390nz8', u'type': u'item', u'aliases': {u'doi': [u'10.5061/dryad.7898']}}
        response_data = json.loads(response_get.data)        
        assert_equals(response_data["aliases"], {u'doi': [u'10.5061/dryad.7898']})

    def test_item_post_unknown_namespace(self):
        response = self.client.post('/item/AnUnknownNamespace/AnIdOfSomeKind/')
        # cheerfully creates items whether we know their namespaces or not.
        assert_equals(response.status_code, 201)

    def test_item_nid_with_bad_character(self):
        url = 'v1/item/doi/10.5061/dryad.' + u'\u200b' + 'j1fd7?key=validkey'
        response_get = self.client.get(url)
        assert_equals(response_get.status_code, 200)

    def test_item_removes_history_by_default(self):
        url = 'v1/item/doi/10.5061/dryad.j1fd7?key=validkey'
        response = self.client.get(url)
        metrics = json.loads(response.data)["metrics"]


        assert_equals(
                metrics["dryad:total_downloads"]["values"]["raw"],
                207
            )
        assert_equals(
            set(metrics["dryad:total_downloads"]["values"].keys()),
            set(["dryad", "raw"]) # no raw_history
        )

    def test_item_include_history_param(self):
        url = 'v1/item/doi/10.5061/dryad.j1fd7?key=validkey&include_history=true'
        response = self.client.get(url)

        metrics = json.loads(response.data)["metrics"]
        print (metrics["dryad:total_downloads"])
        assert_equals(
            set(metrics["dryad:total_downloads"]["values"].keys()),
            set(["dryad", "raw", "raw_history"])
        )

#        assert_equals(
#            metrics["dryad:total_downloads"]["values"]["raw_history"].values(),
#            ["103", "103", "103"]
#        )


class TestItems(ViewsTester):
    def test_post_with_aliases_already_in_db(self):
        items = [
            ["doi", "10.123"],
            ["doi", "10.124"],
            ["doi", "10.125"]
        ]
        resp = self.client.post(
            '/collection',
            data=json.dumps({"aliases": items, "title":"mah collection"}),
            content_type="application/json"
        )
        coll = json.loads(resp.data)["collection"]

        new_items = [
            ["doi", "10.123"], # duplicate
            ["doi", "10.124"], # duplicate
            ["doi", "10.999"]  # new
        ]

        resp2 = self.client.post(
            '/collection',
            data=json.dumps({"aliases": new_items, "title": "mah_collection"}),
            content_type="application/json"
        )
        new_coll = json.loads(resp2.data)["collection"]

        # 3+1 new items + 2 collections + 1 test_item + 1 api_user_doc + at least 7 design docs
        assert_greater(self.d.db.info()["doc_count"], 15)



class TestCollection(ViewsTester):

    def setUp(self):
        self.aliases = [
            ["doi", "10.123"],
            ["doi", "10.124"],
            ["doi", "10.125"]
        ]
        super(TestCollection, self).setUp()

    def test_collection_post_new_collection(self):

        response = self.client.post(
            '/collection',
            data=json.dumps({"aliases": self.aliases, "title":"My Title"}),
            content_type="application/json")

        print response
        print response.data
        assert_equals(response.status_code, 201)  #Created
        assert_equals(response.mimetype, "application/json")
        response_loaded = json.loads(response.data)
        assert_equals(
                set(response_loaded.keys()),
                set(["collection", "key"])
        )
        coll = response_loaded["collection"]
        assert_equals(len(coll["_id"]), 6)
        assert_equals(
            set(coll["alias_tiids"].keys()),
            set([":".join(alias) for alias in self.aliases])
        )

    def test_new_collection_includes_key(self):

        response = self.client.post(
            '/collection',
            data=json.dumps({"aliases": self.aliases, "title":"My Title"}),
            content_type="application/json"
        )
        print response.data
        resp_loaded = json.loads(response.data)
        assert_equals(resp_loaded.keys(), ["key", "collection"])


    def test_collection_get_with_no_id(self):
        response = self.client.get('/collection/')
        assert_equals(response.status_code, 404)  #Not found

    def test_collection_get(self):

        response = self.client.post(
            '/collection',
            data=json.dumps({"aliases": self.aliases, "title":"mah collection"}),
            content_type="application/json"
        )
        collection = json.loads(response.data)["collection"]
        collection_id = collection["_id"]
        print collection_id

        resp = self.client.get('/collection/'+collection_id)
        assert_equals(resp.status_code, 210)
        collection_data = json.loads(resp.data)
        assert_equals(
            set(collection_data.keys()),
            {u'title',
             u'items',
             u'_rev',
             u'created',
             u'last_modified',
             u'alias_tiids',
             u'_id',
             u'key',
             u'owner',
             u'type'}
        )
        assert_equals(len(collection_data["items"]), len(self.aliases))


    def test_get_csv(self):
        response = self.client.post(
            '/collection',
            data=json.dumps({"aliases": self.aliases, "title":"mah collection"}),
            content_type="application/json"
        )
        collection = json.loads(response.data)["collection"]
        collection_id = collection["_id"]

        resp = self.client.get('/collection/'+collection_id+'.csv')
        print resp
        rows = resp.data.split("\n")
        print rows
        assert_equals(len(rows), 5) # header plus 3 items plus csvDictWriter adds an extra line

    def test_collection_update_puts_items_on_alias_queue(self):
        # put some stuff in the collection:
        # put some items in the db
        for doc in mydao.db.update([
                {"_id":"larry", "aliases":{}},
                {"_id":"curly", "aliases":{}},
                {"_id":"moe", "aliases":{}}
        ]):
            pass # no need to do anything, just put 'em in couch.

        collection = {
            "_id":"123",
            "alias_tiids": {"doi:abc":"larry", "doi:def":"moe", "ghi":"curly"}
            }
        mydao.save(collection)
        resp = self.client.post(
            "/collection/123"
        )
        assert_equals(resp.data, "true")

        larry = mydao.get("larry")
        print larry

        # test it is on the redis queue
        response = self.r.rpop("aliasqueue")
        assert_equals(response, '["moe", {}, []]')
        
    def test_collection_owner_set_at_creation(self):

        response = self.client.post(
            '/collection',
            data=json.dumps({"aliases": self.aliases, "title":"mah collection", "owner":"plato"}),
            content_type="application/json"
        )
        collection = json.loads(response.data)["collection"]
        assert_equals(collection["owner"], "plato")

    def test_delete_collection_item(self):
        # make a new collection
        response = self.client.post(
            '/collection',
            data=json.dumps({"aliases": self.aliases, "title":"mah collection", "owner":"plato"}),
            content_type="application/json"
        )
        resp = json.loads(response.data)
        coll =  resp["collection"]
        key =  resp["key"]


        # delete an item.
        tiid_to_delete = coll["alias_tiids"]["doi:10.123"]
        r = self.client.delete(
            "/collection/{id}/items?edit_key={key}".format(id=coll["_id"], key=key),
            data=json.dumps({"tiids": [tiid_to_delete]}),
            content_type="application/json"
        )

        changed_coll = self.d.get(coll["_id"])
        assert_equals(set(changed_coll["alias_tiids"]),
                      set(["doi:10.124", "doi:10.125"]))

    def test_add_collection_item(self):
        # make a new collection
        response = self.client.post(
            '/collection',
            data=json.dumps({"aliases": self.aliases, "title":"mah collection", "owner":"plato"}),
            content_type="application/json"
        )
        resp = json.loads(response.data)
        coll = resp["collection"]
        key = resp["key"]

        alias_list = []
        alias_list.append(["doi", "10.new"])


        r = self.client.put(
            "/collection/{id}/items?edit_key={key}".format(id=coll["_id"], key=key),
            data=json.dumps({"aliases": alias_list}),
            content_type="application/json"
        )

        changed_coll = self.d.get(coll["_id"])

        # we added a new item
        assert_equals(len(changed_coll["alias_tiids"]), 4)

        # it's got a tiid
        assert_equals(len(changed_coll["alias_tiids"]["doi:10.new"]), 24)



    def test_change_collection_requires_key(self):

        # make a new collection
        response = self.client.post(
            '/collection',
            data=json.dumps({"aliases": self.aliases, "title":"mah collection", "owner":"plato"}),
            content_type="application/json"
        )
        resp = json.loads(response.data)
        coll =  resp["collection"]
        key =  resp["key"]

        alias_list = []
        alias_list.append(["doi", "10.new"])

        # 403 Forbidden if wrong edit key
        r = self.client.put(
            "/collection/{id}/items?edit_key={key}".format(id=coll["_id"], key="wrong!"),
            data=json.dumps({"aliases": alias_list}),
            content_type="application/json"
        )
        assert_equals(r.status_code, 403)

        # 404 Bad Request if no edit key
        r = self.client.put(
            "/collection/{id}/items".format(id=coll["_id"]),
            data=json.dumps({"aliases": alias_list}),
            content_type="application/json"
        )
        assert_equals(r.status_code, 404)

        # get the collection out the db and make sure nothing's changed
        changed_coll = self.d.get(coll["_id"])
        assert_equals(changed_coll["title"], "mah collection")
        assert_equals(changed_coll["owner"], "plato")




class TestApi(ViewsTester):

    def setUp(self):
        super(TestApi, self).setUp()

    def tearDown(self):
        pass

    def test_tiid_get_with_unknown_alias(self):
        # try to retrieve tiid id for something that doesn't exist yet
        plos_no_tiid_resp = self.client.get('/tiid/doi/' +
                quote_plus(PLOS_TEST_DOI))
        assert_equals(plos_no_tiid_resp.status_code, 404)  # Not Found


    def test_tiid_get_with_known_alias(self):
        # create new plos item from a doi
        plos_create_tiid_resp = self.client.post('/item/doi/' +
                quote_plus(PLOS_TEST_DOI))
        plos_create_tiid = json.loads(plos_create_tiid_resp.data)

        # retrieve the plos tiid using tiid api
        plos_lookup_tiid_resp = self.client.get('/tiid/doi/' +
                quote_plus(PLOS_TEST_DOI))
        assert_equals(plos_lookup_tiid_resp.status_code, 303)
        plos_lookup_tiids = json.loads(plos_lookup_tiid_resp.data)

        # check that the tiids are the same
        assert_equals(plos_create_tiid, plos_lookup_tiids)

    def test_tiid_get_tiids_for_multiple_known_aliases(self):
        # create two new items with the same plos alias
        first_plos_create_tiid_resp = self.client.post('/item/doi/' +
                quote_plus(PLOS_TEST_DOI))
        first_plos_create_tiid = json.loads(first_plos_create_tiid_resp.data)

        second_plos_create_tiid_resp = self.client.post('/item/doi/' +
                quote_plus(PLOS_TEST_DOI))
        second_plos_create_tiid = json.loads(second_plos_create_tiid_resp.data)

        # check that the tiid lists are the same
        assert_equals(first_plos_create_tiid, second_plos_create_tiid)

class TestInbox(ViewsTester):

    def setUp(self):
        # example from http://docs.cloudmailin.com/http_post_formats/json/        
        self.example_payload = {
               "headers": {
                   "To": "7be5eb5001593217143f@cloudmailin.net",
                   "Mime-Version": "1.0",
                   "X-Received": "by 10.58.45.134 with SMTP id n6mr13476387vem.35.1361476813304; Thu, 21 Feb 2013 12:00:13 -0800 (PST)",
                   "Received": "by mail-vc0-f202.google.com with SMTP id m8so955261vcd.3 for <7be5eb5001593217143f@cloudmailin.net>; Thu, 21 Feb 2013 12:00:13 -0800",
                   "From": "Google Scholar Alerts <scholaralerts-noreply@google.com>",
                   "DKIM-Signature": "v=1; a=rsa-sha256; c=relaxed/relaxed; d=google.com; s=20120113; h=mime-version:x-received:message-id:date:subject:from:to :content-type; bh=74dhtWOnoX2dYtmZibjD2+Tp65AZ7UnVwRTR7Qwho/o=; b=Fabq5urMfTyUX0s3XgFhVx1pyZ+tW/n38Sm/3T5EXTWeG2k7C6mxbrv1DdmpNpl/a8 Sr70eG6St7oytXii5tg9TrwrlwhftpFZKkJQS8GMWswiEaBkOfnNkoRrN174jRYfBUuZ oKWJr49dxw9hV3uKYoSis0zL6R8P+7GXt1rtqblBELrfIJ3pKC7d7WS65i6hdM2kA+sY va9geqt1fFFN7098U7WELlM2JoXhS4fbIQTev/Z6cF89Sfs4888GXb7PIq0d1kfd6t7c kXK8bV6TkqSP4AxDm646Cv1TR9cfo6+9yCrkK8oW6ihAMzM0Lwobq22NLrRY2QK8494s WAuA==",
                   "Date": "Thu, 21 Feb 2013 20:00:13 +0000",
                   "Message-ID": "<089e0115f968d3b38604d6418577@google.com>",
                   "Content-Type": "text/plain; charset=ISO-8859-1; delsp=yes; format=flowed",
                   "Subject": "Confirm your Google Scholar Alert"
               },
               "reply_plain": None,
               "attachments": [
               ],
               "plain": "Google received a request to start sending Scholar Alerts to  \n7be5eb5001593217143f@cloudmailin.net for the query:\nNew articles in Jonathan A. Eisen's profile\n\nClick to confirm this request:\nhttp://scholar.google.ca/scholar_alerts?update_op=confirm_alert&hl=en&alert_id=IMEzMffmofYJ&email_for_op=7be5eb5001593217143f%40cloudmailin.net\n\nClick to cancel this request:\nhttp://scholar.google.ca/scholar_alerts?view_op=cancel_alert_options&hl=en&alert_id=IMEzMffmofYJ&email_for_op=7be5eb5001593217143f%40cloudmailin.net\n\nThanks,\nThe Google Scholar Team",
               "envelope": {
                   "to": "7be5eb5001593217143f@cloudmailin.net",
                   "helo_domain": "mail-vc0-f202.google.com",
                   "from": "3zXwmURUKAO4iSXebQhQbUhji-dehUfboWeeWbU.Sec@scholar-alerts.bounces.google.com",
                   "remote_ip": "209.85.220.202",
                   "spf": {
                       "domain": "scholar-alerts.bounces.google.com",
                       "result": "neutral"
                   }
               },
               "html": None
            }
        super(TestInbox, self).setUp()

    def tearDown(self):
        pass

    def test_inbox(self):
        response = self.client.post(
            "/v1/inbox?key=validkey",
            data=json.dumps(self.example_payload),
            content_type="application/json"
        )
        assert_equals(200, response.status_code)

    def test_save_email(self):
        doc_id = views.save_email(self.example_payload)

        stored_email = self.postgres_d.get_email(doc_id)

        assert_equals(stored_email[0].keys(), ['payload', 'id', 'created'])
        assert_equals(json.loads(stored_email[0]["payload"]), self.example_payload)

    def test_alert_if_google_scholar_notification_confirmation(self):
        response = views.alert_if_google_scholar_notification_confirmation(self.example_payload)
        expected = ('Jonathan A. Eisen', 'http://scholar.google.ca/scholar_alerts?update_op=confirm_alert&hl=en&alert_id=IMEzMffmofYJ&email_for_op=7be5eb5001593217143f%40cloudmailin.net')
        assert_equals(response, expected)

    def test_alert_if_google_scholar_new_articles(self):
        self.example_payload["headers"]["Subject"] = "Scholar Alert - John P. A. Ioannidis - new articles"
        response = views.alert_if_google_scholar_new_articles(self.example_payload, "1234")
        expected = 'John P. A. Ioannidis'
        assert_equals(response, expected)


class TestTiid(ViewsTester):

    def test_tiid_post(self):
        # POST isn't supported
        response = self.client.post('/tiid/Dryad/NotARealId')
        assert_equals(response.status_code, 405)  # Method Not Allowed

    def test_item_get_unknown_tiid(self):
        # pick a random ID, very unlikely to already be something with this ID
        response = self.client.get('/item/' + str(uuid.uuid1()))
        assert_equals(response.status_code, 404)  # Not Found

    def test_item_post_known_tiid(self):
        response = self.client.post('/item/doi/IdThatAlreadyExists/')
        print response
        print "here is the response data: " + response.data

        # FIXME should check and if already exists return 200
        # right now this makes a new item every time, creating many dups
        assert_equals(response.status_code, 201)
        assert_equals(len(json.loads(response.data)), 24)
        assert_equals(response.mimetype, "application/json")

class TestUser(ViewsTester):

    def test_create(self):

        user = {
            "_id": "horace@rome.it",
            "key": "hash",
            "colls": {}
        }
        resp = self.client.put(
            "/user",
            data=json.dumps(user),
            content_type="application/json"
        )
        assert_equals("horace@rome.it", json.loads(resp.data)["_id"])


    def test_create_without_key_in_body(self):
        user = {
            "_id": "horace@rome.it",
            "colls": {}
        }
        resp = self.client.put(
            "/user",
            data=json.dumps(user),
            content_type="application/json"
        )
        assert_equals(400, resp.status_code)

    def test_create_without_colls_in_body(self):
        user = {
            "_id": "horace@rome.it",
            "key":"hash"
        }
        resp = self.client.put(
            "/user",
            data=json.dumps(user),
            content_type="application/json"
        )
        assert_equals(400, resp.status_code)


    def test_get_user_doesnt_exist(self):
        resp = self.client.get("/user/test@foo.com")
        assert_equals(resp.status_code, 404)

    def test_get_user(self):
        user = {
            "_id": "horace@rome.it",
            "key": "hash",
            "colls": {}
        }
        r = self.client.put(
            "/user",
            data=json.dumps(user),
            content_type="application/json"
        )
        resp = self.client.get("/user/horace@rome.it?key=hash")
        resp_dict = json.loads(resp.data)
        print resp_dict

        assert_equals(resp_dict["_id"], "horace@rome.it")

    def test_update_user(self):

        user = {
            "_id": "horace@rome.it",
            "key": "hash",
            "colls": {}
        }
        r = self.client.put(
            "/user",
            data=json.dumps(user),
            content_type="application/json"
        )

        # get the new user and add a coll
        resp = self.client.get("/user/horace@rome.it?key=hash")
        assert_equals(resp.status_code, 200)

        user = json.loads(resp.data)
        user["colls"] = ["cid:123"]

        # put the new, modified user in the db
        res = self.client.put(
            "/user",
            data=json.dumps(user),
            content_type="application/json"
        )

#        returned_user = json.loads(res.data)
#        assert_equals(returned_user["_id"], "catullus@rome.it")
#
#        # get the user out again, and check to see if it was modified
#        resp = self.client.get("/user/catullus@rome.it?key=passwordhash")
#        user = json.loads(resp.data)
#        assert_equals(user["colls"], ["cid:123"])





