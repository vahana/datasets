import logging
import os
import urllib3

from slovar import slovar

import prf
from prf.request import PRFRequest, Request
import prf.exc as prf_exc
from prf.utils import rextract

import datasets

log = logging.getLogger(__name__)

def auth_url(params):
    auth = slovar()
    auth_param = params.get('auth')
    if isinstance(auth_param, str):
        if '@' in auth_param:
            return urllib3.util.parse_url(auth_param).url

        auth = datasets.Settings.extract('%s.*' % auth_param)
        if not auth:
            raise prf.exc.HTTPBadRequest('auth name `%s` is wrong or missing in config file' % auth_param)

    else: # passed as separate fields
        auth.login = params.get('auth.login')
        auth.password = params.get('auth.password')
        auth.url = params.get('auth.url')

    auth.pop_by_values([None, ''])

    if auth:
        parts = urllib3.util.parse_url(auth.url)
        return parts._replace(auth='%s:%s' % (auth.login,auth.password)).url


class prf_api(object):
    def __init__(self, ds):
        self.api = PRFRequest(params.name, auth=auth_url(params), _raise=True)

    def get_collection(self, **params):
        resp = self.api.get(params=params)
        return self.api.get_data(resp)

    def get_collection_paged(self, page_size, **params):
        for resp in self.api.get_paginated(page_size, params=params):
            yield self.api.get_data(resp)


class request_api(object):

    def __init__(self, ds):
        if ds.ns != 'NA':
            self.ns = ds.ns
        else:
            self.ns = None

        self.api = Request(_raise=False)

    def get_data(self, resp):
        try:
            dataset = resp.json()
        except Exception as e:
            raise prf_exc.HTTPBadRequest('Data does not seem to be json format')

        if self.ns and isinstance(dataset, dict):
            dataset = dataset[self.ns]

        if not isinstance(dataset, list):
            dataset = [dataset]

        return [slovar(it) for it in dataset]

    def validate_url(self, params):
        url = params.get('_url')

        if not url:
            raise prf_exc.HTTPBadRequest('`_url` params is missing')

        return url

    def get_collection(self, **params):
        params = slovar(params).unflat()
        params.aslist('_ignore_codes', default=[], itype=int)

        headers = params.extract('h.*')
        qparams = params.extract('qs.*')

        if headers:
            self.api.session.headers.update(headers)

        resp = self.api.get(self.validate_url(params), params=qparams)
        data = []

        if resp.ok:
            data = self.get_data(resp)
        else:
            self.api.raise_or_log(resp,
                _raise=resp.status_code not in params._ignore_codes)

        if params.get('_count'):
            return len(data)

        return data

    def get_collection_paged(self, page_size, **params):
        yield self.get_collection(**params)


class HTTPBackend(object):
    @classmethod
    def get_dataset(cls, ds, define=None):
        return request_api(ds)

