from typing import Dict, Any, Tuple, Iterable, List

Cache = Dict[str, Any]

def cache_get(cache: Cache, path: str, seperator: str = ".") -> Any:
    '''Retreives the subcache or value from a path string.'''
    # attr = cache
    for p in path.split(seperator):
        if isinstance(cache, list) and p.isnumeric():
            cache = cache[int(p)]
            continue

        if not isinstance(cache, dict):
            break

        cache = cache.get(p) #TODO: Potential flaw: If we're matching for None with a data structure that might not exist, we will return a correct match regardless, as get() defaults to none.

    return cache


def cache_get_multi(cache: Cache, paths: Iterable[str], seperator: str = ".") -> Iterable[Any]:
    '''Retreives the subcaches or values from any number of path strings.'''
    return type(paths)(cache_get(cache, p, seperator) for p in paths)


def cache_remove(cache: Cache, path_str: str, seperator: str = "."):
    '''Removes an entry from a cache in-place, by a string path.'''
    split_path = path_str.split(seperator)
    def _inner_cache_remove(cache: Cache, path: List[str]):
        if len(path) == 1:
            end_key = path[0]
            if isinstance(cache, list) and end_key.isnumeric():
                end_key = int(end_key)

            del cache[end_key]

        else:
            cur_key = split_path.pop(0)
            if isinstance(cache, list) and cur_key.isnumeric():
                cur_key = int(cur_key)

            _inner_cache_remove(cache[cur_key], split_path)

    _inner_cache_remove(cache, split_path)


def cache_modify(cache: Cache, new_value: Any, path_str: str, seperator: str = "."):
    '''Modifies an entry in a cache based on a string path.'''
    split_path = path_str.split(seperator)
    def _inner_cache_modify(cache: Cache, new_value: Any, path: List[str]):
        if len(path) == 1:
            end_key = path[0]
            if isinstance(cache, list) and end_key.isnumeric():
                end_key = int(end_key)

            cache[end_key] = new_value

        else:
            cur_key = split_path.pop(0)
            if isinstance(cache, list) and cur_key.isnumeric():
                cur_key = int(cur_key)

            _inner_cache_modify(cache[cur_key], new_value, split_path)

    _inner_cache_modify(cache, new_value, split_path)


def filter_caches(caches: Iterable[Cache], match: Dict[str, Any], exclusive: bool = False, either_or: bool = False) -> Tuple[List[Cache], List[int]]:
    '''Intakes an iterable of caches and a dict of path strings to values, and returns the same type of iterable but only the matches, along with their indices. Exclusive argument will only return mismatches when enabled.'''
    matches = []
    match_indices = []

    def _cache_match(cache: Cache, m_path: str, m_value: Any) -> bool:
        matched: bool = cache_get(cache, m_path) == m_value #Retreives the value we want to match against
        return not ((exclusive and matched) or (not exclusive and not matched))

    for i, cache in enumerate(caches):
        if either_or:
            match_minimum = any

        else:
            match_minimum = all

        if not match_minimum(_cache_match(cache, m_path, m_value) for m_path, m_value in match.items()):
            continue

        else:
            matches.append(cache)
            match_indices.append(i)

    return (matches, match_indices) #Returns the iterable of matched caches. Also returns indices of the matches within the origin list.
