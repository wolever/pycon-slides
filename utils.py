import os
import time
import errno
import urllib
import random
import shutil
import hashlib
import logging

cache_log = logging.getLogger("cache.fscache")

def to_str(s):
    if isinstance(s, str):
        return s
    return s.encode("utf-8")

def mkdir(*parts):
    dirname = os.path.join(*parts)
    try:
        os.mkdir(dirname)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise
        return False, dirname
    return True, dirname


def ctime(path):
    try:
        return os.path.getctime(path)
    except OSError:
        return float('nan')


class CacheTimeout(Exception):
    pass


class FSCache(object):
    def __init__(self, basedir, grouper, key_prefix="", timeout=60):
        self.basedir = basedir
        self.grouper = grouper
        self.key_prefix = key_prefix
        self.timeout = timeout
        mkdir(basedir)

    def hash(self, s):
        result = hashlib.md5(to_str(s)).hexdigest()
        return result

    def get_or_create(self, fname, raw_cache_key, create_func):
        cache_key = "%s:%s:%s" %(
            self.grouper,
            self.hash(self.key_prefix + raw_cache_key),
            fname,
        )
        if "/" in cache_key:
            cache_key = urllib.quote(cache_key, safe=":")

        log_info = {
            "cache_key": cache_key,
            "cache_hit": True,
        }
        start_time = time.time()
        try:
            data_file = os.path.join(self.basedir, cache_key)
            if not os.path.exists(data_file):
                self.acquire_and_create(data_file, create_func, log_info)
            return data_file
        except Exception as e:
            log_info["cache_exception"] = repr(e)
            raise
        finally:
            log_info["duration"] = time.time() - start_time
            cache_log.info(log_info)

    def acquire_and_create(self, data_file, create_func, log_info=None):
        log_info = log_info or {}
        should_create = False
        try:
            should_create, working_dir = mkdir(data_file + ":in-progress")
            if not should_create:
                log_info["cache_polling"] = True
                log_info["cache_lock_age"] = time.time() - ctime(working_dir)
                poll_start = time.time()
                while not os.path.exists(data_file):
                    if time.time() > poll_start + self.timeout:
                        try:
                            shutil.rmtree(working_dir)
                        except Exception:
                            pass
                        raise CacheTimeout("Timeout waiting for cache in %r"
                                          %(working_dir, ))
                    time.sleep(0.1)
                return
            log_info["cache_hit"] = False
            _, ext = os.path.splitext(data_file)
            output_file = os.path.join(working_dir, "output" + ext)
            create_func(working_dir, output_file)
            if not os.path.exists(output_file):
                raise OSError(2, "Output file %r was not created by %s"
                              %(output_file, create_func))
            os.rename(output_file, data_file)
        finally:
            if should_create:
                shutil.rmtree(working_dir)

def to_base(number, alphabet):
    if not isinstance(number, (int, long)):
        raise TypeError('number must be an integer')
    if number < 0:
        raise ValueError('number must be nonnegative')

    # Special case for zero
    if number == 0:
        return '0'

    in_base = []
    while number != 0:
        number, i = divmod(number, len(alphabet))
        in_base.append(alphabet[i])
    return "".join(reversed(in_base))

ALPHABET_36 =  "0123456789abcdefghijklmnopqrstuvwxyz"

def to36(number):
    return to_base(number, ALPHABET_36)

def from36(str):
    return int(str, 36)

def mk_random_id():
    """ Returns a unique 64 bit ID which is based on a random number and
        the current time. """
    # Truncate the current unix time to 32 bits...
    curtime = int(time.time()) & ((1<<32)-1)
    # ... then slap some random bits on the end.
    # Do this to help the database maintain temporal locality.
    # (it's possible that these should be swapped - with the
    # random bits coming first and the time bits coming second)
    return to36((curtime << 32) | random.getrandbits(32))

def fname_safe(s):
    return to_str(s.lstrip(".").replace("/", " ").replace(":", " "))

