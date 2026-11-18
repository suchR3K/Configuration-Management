"""Verify the bundled release contains only the intended static assets."""
from pathlib import Path
import tarfile

archive = Path(__file__).resolve().parents[1] / 'files' / 'lab-portal.tar.gz'
expected = {'index.html', 'styles.css'}
with tarfile.open(archive, 'r:gz') as bundle:
    members = bundle.getmembers()
    assert len(members) == len(expected), 'Unexpected archive entries'
    assert {member.name for member in members} == expected, 'Unexpected paths'
    assert all(member.isfile() and member.size > 0 for member in members), 'Expected nonempty regular files'
    assert b'Small network.' in bundle.extractfile('index.html').read(), 'Wrong entry page'
print('Archive validation passed: two nonempty static files, no links or unexpected paths.')
