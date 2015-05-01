from django.core.cache import cache, InvalidCacheBackendError

from sorl.thumbnail.kvstores.base import KVStoreBase
from sorl.thumbnail.conf import settings
from sorl.thumbnail.models import KVStore as KVStoreModel
from sorl.thumbnail.compat import get_cache


class EMPTY_VALUE(object):
    pass


class KVStore(KVStoreBase):
    def __init__(self):
        super(KVStore, self).__init__()
        try:
            self.cache = get_cache(settings.THUMBNAIL_CACHE)
        except InvalidCacheBackendError:
            self.cache = cache

    def clear(self, delete_thumbnails=False):
        """
        We can clear the database more efficiently using the prefix here rather
        than calling :meth:`_delete_raw`.
        """
        prefix = settings.THUMBNAIL_KEY_PREFIX
        for key in self._find_keys_raw(prefix):
            self.cache.delete(key)
        KVStoreModel.objects.filter(key__startswith=prefix).delete()
        if delete_thumbnails:
            self.delete_all_thumbnail_files()

    def _get_raw(self, key):
        value = self.cache.get(key)
        if value is None:
            try:
                value = KVStoreModel.objects.get(key=key).value
            except KVStoreModel.DoesNotExist:
                # we set the cache to prevent further db lookups
                value = EMPTY_VALUE
            self.cache.set(key, value, settings.THUMBNAIL_CACHE_TIMEOUT)
        if value == EMPTY_VALUE:
            return None
        return value

    def _set_raw(self, key, value):
        KVStoreModel.objects.get_or_create(
            key=key, defaults={'value': value})
        self.cache.set(key, value, settings.THUMBNAIL_CACHE_TIMEOUT)

    def _delete_raw(self, *keys):
        KVStoreModel.objects.filter(key__in=keys).delete()
        for key in keys:
            self.cache.delete(key)

    def _find_keys_raw(self, prefix):
        qs = KVStoreModel.objects.filter(key__startswith=prefix)
        return qs.values_list('key', flat=True)
