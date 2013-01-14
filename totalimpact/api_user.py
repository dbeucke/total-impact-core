import datetime, shortuuid, os

from totalimpact import item, mixpanel
from totalimpact.utils import Retry
from couchdb import ResourceConflict

import logging
logger = logging.getLogger('ti.api_user')


class ApiLimitExceededException(Exception):
    pass

class InvalidApiKeyException(Exception):
    pass

class ItemAlreadyRegisteredToThisKey(Exception):
    pass

def is_current_api_user_key(key, mydao):
    if not key:
        return False

    api_user_id = get_api_user_id_by_api_key(key, mydao)
    if api_user_id:
        return True
    return False

def is_internal_key(key):
    if not key:
        return False

    # make sure these are all lowercase because that is how they come in from flask
    if key.lower() in ["yourkey", "samplekey", "item-report-page", "api-docs", os.getenv("API_KEY").lower()]:
        return True
    return False

def is_valid_key(key, mydao):
    # do quick and common check first
    if is_internal_key(key):
        return True
    if is_current_api_user_key(key, mydao):
        return True
    return False


def build_api_user(prefix, max_registered_items, **meta):
    api_user_doc = {}

    new_api_key = prefix.lower() + "-" + shortuuid.uuid().lower()[0:6]
    now = datetime.datetime.now().isoformat()

    api_user_doc["max_registered_items"] = int(max_registered_items)
    api_user_doc["created"] = now
    api_user_doc["type"] = "api_user"
    api_user_doc["meta"] = meta
    api_user_doc["current_key"] = new_api_key
    api_user_doc["key_history"] = {now: new_api_key}
    api_user_doc["registered_items"] = {}
    api_user_doc["_id"] = shortuuid.uuid()[0:24]

    return (api_user_doc, new_api_key)

def is_registered(alias, api_key, mydao):
    if is_internal_key(api_key):
        return False

    alias = item.canonical_alias_tuple(alias)
    alias_string = ":".join(alias)
    api_key = api_key.lower()

    res = mydao.view('registered_items_by_alias/registered_items_by_alias')    
    matches = res[[alias_string, api_key]] 

    if matches.rows:
        #api_user_id = matches.rows[0]["id"]
        return True
    return False

def is_over_quota(api_key, mydao):
    if is_internal_key(api_key):
        return False

    api_user_id = get_api_user_id_by_api_key(api_key, mydao)
    api_user_doc = mydao.get(api_user_id)
    used_registration_spots = len(api_user_doc["registered_items"])
    remaining_registration_spots = api_user_doc["max_registered_items"] - used_registration_spots
    if remaining_registration_spots <= 0:
        return True
    return False

@Retry(6, ResourceConflict, 0.4)
def save_registration_data(api_user_id, alias_key, registration_dict, mydao):
    logger.debug("in save_registration_data with {alias_key}".format(
        alias_key=alias_key))
    api_user_doc = mydao.get(api_user_id)
    api_user_doc["registered_items"][alias_key] = registration_dict
    mydao.db.save(api_user_doc)
    return True

def add_registration_data(alias, tiid, api_key, mydao):
    if is_internal_key(api_key):
        return False

    logger.info("adding registration for {alias} for {tiid} and {api_key}".format(
        alias=alias, tiid=tiid, api_key=api_key))

    api_user_id = get_api_user_id_by_api_key(api_key, mydao)
    now = datetime.datetime.now().isoformat()
    registration_dict = {
        "registered_date": now,
        "tiid": tiid
    }

    alias_key = ":".join(alias)
    registered = False
    try:
        registered = save_registration_data(api_user_id, alias_key, registration_dict, mydao)
    except ResourceConflict:
        logger.error("Registration failed for {alias_key} for {tiid} and {api_key}".format(
            alias_key=alias_key, tiid=tiid, api_key=api_key))
    return registered


def get_api_user_id_by_api_key(api_key, mydao):
    if is_internal_key(api_key):
        return None

    logger.debug("In get_api_user_by_api_key with {api_key}".format(
        api_key=api_key))

    # for expl of notation, see http://packages.python.org/CouchDB/client.html#viewresults# for expl of notation, see http://packages.python.org/CouchDB/client.html#viewresults
    res = mydao.view('api_users_by_api_key/api_users_by_api_key')

    api_key = api_key.lower()
    
    matches = res[[api_key]] 

    api_user_id = None
    if matches.rows:
        api_user_id = matches.rows[0]["id"]
        logger.debug("found a match for {api_key}!".format(api_key=api_key))
    else:
        logger.debug("no match for api_key {api_key}!".format(api_key=api_key))
    return (api_user_id)


def register_item(alias, api_key, myredis, mydao):
    if not is_valid_key(api_key, mydao):
        raise InvalidApiKeyException
    if is_registered(alias, api_key, mydao):
        raise ItemAlreadyRegisteredToThisKey

    (namespace, nid) = alias
    tiid = item.get_tiid_by_alias(namespace, nid, mydao)
    if not tiid:
        if is_over_quota(api_key, mydao):
            raise ApiLimitExceededException
        else:
            tiid = item.create_item(namespace, nid, myredis, mydao)
    registered = add_registration_data(alias, tiid, api_key, mydao)
    if registered:
        mixpanel.track("Create:Register", {"Namespace":namespace, 
                                            "API Key":api_key})

    return tiid
