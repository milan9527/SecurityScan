"""Synthetic document API. actor comes from verified session middleware; doc_id from URL."""
DOCUMENTS = {'a': {'owner': 'alice', 'body': 'alice private draft'}, 'b': {'owner': 'bob', 'body': 'bob private draft'}}

def read_document(actor, doc_id):
    if not actor:
        raise PermissionError('login required')
    return DOCUMENTS[doc_id]['body']

def read_document_v2(actor, doc_id):
    if not actor or DOCUMENTS[doc_id]['owner'] != actor:
        raise PermissionError('not allowed')
    return DOCUMENTS[doc_id]['body']
