import importlib.util
import pathlib
import tempfile
root = pathlib.Path(__file__).parent / 'fixtures'
def load(name):
    spec = importlib.util.spec_from_file_location(name, root/name/'app.py')
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod
m=load('catalog'); db=m.database()
assert (2,'unreleased book') in m.search(db,"' OR 1=1 --")
assert m.search_v2(db,"' OR 1=1 --")==[]
m=load('documents')
assert m.read_document('alice','b')=='bob private draft'
try: m.read_document_v2('alice','b'); raise AssertionError('safe control failed')
except PermissionError: pass
m=load('downloads')
with tempfile.TemporaryDirectory() as d:
    p=pathlib.Path(d); (p/'public').mkdir(); (p/'secret.txt').write_text('synthetic secret')
    assert m.download(p/'public','../secret.txt')==b'synthetic secret'
    try: m.download_v2(p/'public','../secret.txt'); raise AssertionError('safe control failed')
    except PermissionError: pass
print('Verified 3 exploitable fixtures and 3 safe controls with local synthetic data.')
