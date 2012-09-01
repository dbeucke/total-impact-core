import json, logging, threading, Queue

from totalimpact.models import ItemFactory
from totalimpact.providers.provider import ProviderFactory

logger = logging.getLogger('ti.backend_new')
logger.setLevel(logging.DEBUG)

class backendException(Exception):
    pass

class Backend(object):
    
    def __init__(self, couch_queues, myredis, dao):
        self.couch_queues = couch_queues
        self.myredis = myredis
        self.dao = dao

    def push_on_update_queue(self, tiid, aliases):
        aliases_doc = json.dumps((tiid, aliases))
        self.myredis.lpush("alias", aliases_doc)

    def pop_from_update_queue(self):
        response = None
        response_json = self.myredis.rpop("alias")
        if response_json:
            logger.info('Got fresh item %s' %response_json)
            response = json.loads(response_json)  
        return response

    def push_on_couch_queue(self, tiid, method_name, new_stuff):
        self.couch_queues[0].put((tiid, method_name, new_stuff))

    def pop_from_couch_queue(self):
        response = self.couch_queues[0].get()
        self.couch_queues[0].task_done()
        return(response)

    def decide_who_to_call_next(self, item):
        simple_products_provider_lookup = {
            "dataset":["dryad"], 
            "software":["github"],
            "slides":["slideshare"], 
            "webpage":["webpage"], 
            "unknown":[]}

        # default to nothing
        aliases = []
        biblio = []
        metrics = []

        has_alias_urls = "url" in item["aliases"]
        has_biblio = "title" in item["biblio"]
        genre = ItemFactory.decide_genre(item["aliases"])
        print genre

        if (genre == "article"):
            if has_alias_urls:
                metrics = "all"
                if not has_biblio:
                    if "doi" in item["aliases"]:
                        biblio = ["crossref"]
                    else:
                        biblio = ["pubmed"]
            else:
                aliases = ["pubmed", "crossref"]
        else:
            relevant_providers = simple_products_provider_lookup[genre]
            print relevant_providers
            if has_alias_urls:
                # aliases are all done
                metrics = "all"
                if not has_biblio:
                    biblio = relevant_providers
            else:
                aliases = relevant_providers

        return({"aliases":aliases, "biblio":biblio, "metrics":metrics})

    def add_new_aliases_to_item(self, new_alias_tuples, item):
        for ns, nid in new_alias_tuples:
            try:
                item["aliases"][ns].append(nid)
                item["aliases"][ns] = list(set(item["aliases"][ns]))
            except KeyError: # no ids for that namespace yet. make it.
                item["aliases"][ns] = [nid]
            except AttributeError:
                # nid is a string; overwrite.
                item["aliases"][ns] = nid
                logger.debug("aliases[{ns}] is a string ('{nid}'); overwriting".format(
                    ns=ns, nid=nid))
        return item

    def add_response_to_item(self, item, new_stuff, method_name):
        if method_name=="aliases":
            item = self.add_new_aliases_to_item(new_stuff, item)
        elif method_name=="biblio":
            # just overwrite whatever was there
            item["biblio"] = new_stuff
        else:
            print "oh oh"
        print item
        return item

    def add_aliases_to_update_queue(self, tiid, new_aliases, method):
        self.push_on_couch_queue(tiid, "aliases", new_aliases)
        self.push_on_update_queue(tiid, new_aliases)

    def wrapper(self, args):
        # args all passed in as a tuple from thread launch
        (tiid, aliases, provider_names, method_name, callback) = args
        alias_tuples = ItemFactory.alias_tuples_from_dict(aliases)

        responses = []
        # call the method for all the listed providers
        for provider_name in provider_names:
            provider = ProviderFactory.get_provider(provider_name)
            method = getattr(provider, method_name)

            response = method(alias_tuples)
            print response
            responses += [response]

        # then put the item on the right callback
        callback(tiid, method_name, response)
        return responses


    def run(self):
        (tiid, aliases) = self.pop_from_update_queue()
        if aliases:
            logger.info("popped item '{tiid}'; beginning update.".format(tiid=tiid))

            providers = self.decide_who_to_call_next(aliases)
            logger.info("got decide_who_to_call_next for '{tiid}': {providers}".format(
                tiid=tiid))

            threading.Thread(self.wrapper, 
                (tiid, aliases, providers["aliases"], "aliases", self.add_aliases_to_update_queue))
            threading.Thread(self.wrapper, 
                (tiid, aliases, providers["biblio"], "biblio", self.push_on_couch_queue))
            threading.Thread(self.wrapper, 
                (tiid, aliases, providers["metrics"], "metrics", self.push_on_couch_queue))

            logger.debug("finished launching update threads for '{tiid}'".format(tiid=tiid))
        else:
            time.sleep(0.5)

    def run_in_loop(self):
        while True:
            self.run()


class CouchWorker():
    def __init__(self, couch_queue, mydao):
        logger.info("%20s init" % ("CouchWorker"))
        self.couch_queue = couch_queue
        self.mydao = mydao

    def run(self):
        logger.info("%20s in run" % ("CouchWorker"))

        while True:
            (doc_type, doc) = self.couch_queue.get()
            if doc is None:
                self._interruptable_sleep(0.5)
            else:
                logger.info('Saving doc in CouchWorker!')
                self.mydao.save(doc)
                self.couch_queue.task_done()



def main():
    mydao = dao.Dao(os.environ["CLOUDANT_URL"], os.environ["CLOUDANT_DB"])
    mydao.update_design_doc()

    couch_queue = Queue.Queue()
    t = CouchWorker(couch_queue, mydao)
    t.start()
    t.thread_id = 'CouchWorker_thread'

    backend = Backend([couch_queue], myredis, mydao)
    backend.run_in_loop()
 
if __name__ == "__main__":
    main()
