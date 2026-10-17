"""Reference contract for the equivalent native scheduled reconciliation search."""
def complete(expected,actual):
    return bool(expected) and all(n>=0 and len(set(actual.get(key,[])))==n for key,n in expected.items())
