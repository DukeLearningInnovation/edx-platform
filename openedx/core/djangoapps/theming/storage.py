"""
Comprehensive Theming support for Django's collectstatic functionality.
See https://docs.djangoproject.com/en/1.8/ref/contrib/staticfiles/
"""

import os.path
import re

from django.core.exceptions import ImproperlyConfigured
from django.contrib.staticfiles.storage import StaticFilesStorage, CachedFilesMixin
from django.utils._os import safe_join
from django.conf import settings
from django.utils.six.moves.urllib.parse import (  # pylint: disable=no-name-in-module, import-error
    unquote, urlsplit,
)

from openedx.core.djangoapps.theming.helpers import (
    get_base_theme_dir,
    get_project_root_name,
    get_current_site_theme_dir,
)


class ComprehensiveThemingStorageMixin(object):
    """
    Mixin for Django storage system to make it aware of the currently-active
    comprehensive theme, so that it can generate theme-scoped URLs for themed
    static assets.
    """
    def __init__(self, *args, **kwargs):
        super(ComprehensiveThemingStorageMixin, self).__init__(*args, **kwargs)
        themes_dir = get_base_theme_dir()
        if not themes_dir:
            self.themes_location = None
            return

        if not isinstance(themes_dir, basestring):
            raise ImproperlyConfigured("Your COMPREHENSIVE_THEME_DIR setting must be a string")

        self.themes_location = themes_dir

    def themed(self, name, theme_dir):
        """
        Given a name, return a boolean indicating whether that name exists
        as a themed asset in the comprehensive theme.
        """
        # Nothing can be themed if we don't have a theme location or required params.
        if not all((self.themes_location, theme_dir, name)):
            return False

        themed_path = "/".join([
            self.themes_location,
            theme_dir,
            get_project_root_name(),
            "static/"
        ])
        name = name[1:] if name.startswith("/") else name
        path = safe_join(themed_path, name)
        return os.path.exists(path)

    def path(self, name):
        """
        Get the path to the real asset on disk
        """
        try:
            theme_dir, asset_path = name.split("/", 1)
            if self.themed(asset_path, theme_dir):
                name = asset_path
                base = self.themes_location + "/" + theme_dir + "/" + get_project_root_name() + "/static/"
            else:
                base = self.location
        except ValueError:
            # in case we don't '/' in name
            base = self.location
        if base == settings.STATIC_ROOT:
            name = re.sub(r"/?(?P<theme>[^/]+)/(?P<system>lms|cms)/static/", r"\g<theme>/", name)
        path = safe_join(base, name)
        return os.path.normpath(path)

    def url(self, name):
        """
        Add the theme prefix to the asset URL
        """
        theme_dir = get_current_site_theme_dir()
        if self.themed(name, theme_dir):
            name = theme_dir + "/" + name
        return super(ComprehensiveThemingStorageMixin, self).url(name)


class ComprehensiveThemingCachedFilesMixin(CachedFilesMixin):
    """
    Comprehensive theming aware CachedFilesMixin.
    """

    def url(self, name, force=False):
        """
        Returns themed url for the given asset.
        """
        parsed_name = urlsplit(unquote(name))
        clean_name = parsed_name.path.strip()
        pattern = r"/?(?P<theme>[^/]+)/(?P<system>lms|cms)/static/"
        asset_name = name
        if not self.exists(clean_name):
            # remove 'lms/static' from url to get correct asset path inside theme directory
            asset_name = re.sub(pattern, r"\g<theme>/", name)
            parsed_name = urlsplit(unquote(name))
            clean_name = parsed_name.path.strip()

            # if themed asset does not exists then use default asset
            if not self.exists(clean_name):
                asset_name = re.sub(pattern, r"", name)
        return super(ComprehensiveThemingCachedFilesMixin, self).url(asset_name, force)


class ComprehensiveThemingStorage(
        ComprehensiveThemingStorageMixin,
        StaticFilesStorage,
):
    """
    Used by the ComprehensiveThemeFinder class. Mixes in support for cached
    files and comprehensive theming in static files.
    """
    pass
