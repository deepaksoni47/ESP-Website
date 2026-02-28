__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2007 by the individual contributors
  (see AUTHORS file)

The ESP Web Site is free software; you can redistribute it and/or
modify it under the terms of the GNU Affero General Public License
as published by the Free Software Foundation; either version 3
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public
License along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.

Contact information:
MIT Educational Studies Program
  84 Massachusetts Ave W20-467, Cambridge, MA 02139
  Phone: 617-253-4882
  Email: esp-webmasters@mit.edu
Learning Unlimited, Inc.
  527 Franklin St, Cambridge, MA 02139
  Phone: 617-379-0178
  Email: web-team@learningu.org
"""

from django.conf.urls import include, handler500, handler404, url
from django.contrib import admin
from esp.admin import admin_site, autodiscover
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.views.generic import TemplateView
from django.views.generic.base import RedirectView
from filebrowser.sites import site as filebrowser_site


def _patch_filebrowser_transpose():
    """Patch filebrowser's transpose_image to properly handle file overwrites.

    The original transpose_image doesn't delete the original before saving,
    causing storage.save() to return a mangled filename. We delete first.

    Also patch ChangeForm.clean_name() to do case-insensitive comparison
    since filenames are normalized to lowercase but the form validation
    was doing case-sensitive string comparison.
    """
    import os
    import tempfile
    from PIL import Image as _PILImage
    from django.core.files import File as DjangoFile
    from django.contrib import messages
    from django.utils.translation import gettext_lazy as _lazy
    import filebrowser.actions as _fb_actions
    import filebrowser.forms as _fb_forms
    from filebrowser.settings import VERSION_QUALITY
    from filebrowser.utils import convert_filename

    def _patched_transpose_image(request, fileobjects, operation):
        for fileobject in fileobjects:
            _root, ext = os.path.splitext(fileobject.filename)
            ext_lower = ext.lower()

            with fileobject.site.storage.open(fileobject.path) as f:
                im = _PILImage.open(f)
                new_image = im.transpose(operation)

            tmpfile = DjangoFile(tempfile.NamedTemporaryFile())
            img_format = _PILImage.EXTENSION.get(ext_lower) or im.format
            try:
                new_image.save(tmpfile, format=img_format,
                               quality=VERSION_QUALITY,
                               optimize=(ext_lower != '.gif'))
            except IOError:
                new_image.save(tmpfile, format=img_format,
                               quality=VERSION_QUALITY)

            original_path = fileobject.path
            try:
                # Delete original before saving to avoid storage collision
                fileobject.site.storage.delete(original_path)
                saved_under = fileobject.site.storage.save(
                    original_path, tmpfile)
                if saved_under != original_path:
                    fileobject.site.storage.move(
                        saved_under, original_path, allow_overwrite=True)
                fileobject.delete_versions()
            finally:
                tmpfile.close()

            messages.add_message(
                request, messages.SUCCESS,
                _lazy("Action applied successfully to '%s'") %
                fileobject.filename)

    _fb_actions.transpose_image = _patched_transpose_image

    def _patched_clean_name(self):
        """Filebrowser's ChangeForm.clean_name with case-insensitive comparison.

        Files are normalized to lowercase, but the original validation did
        case-sensitive path comparison. This causes false "file exists" errors.
        """
        if self.cleaned_data['name']:
            from filebrowser.settings import FOLDER_REGEX
            import re
            if not re.search(FOLDER_REGEX, self.cleaned_data['name'], re.U):
                from django.forms import ValidationError
                raise ValidationError(
                    _lazy('Only letters, numbers, underscores, spaces '
                          'and hyphens are allowed.'))

            new_name = convert_filename(self.cleaned_data['name'])
            new_path = os.path.join(self.path, new_name)
            current_path = self.fileobject.path

            # Case-insensitive comparison to match normalized filenames
            is_same = new_path.lower() == current_path.lower()

            if self.site.storage.isdir(new_path) and not is_same:
                from django.forms import ValidationError
                raise ValidationError(_lazy('The Folder already exists.'))
            elif self.site.storage.isfile(new_path) and not is_same:
                from django.forms import ValidationError
                raise ValidationError(_lazy('The File already exists.'))

            return new_name
        return self.cleaned_data['name']

    _fb_forms.ChangeForm.clean_name = _patched_clean_name


_patch_filebrowser_transpose()
del _patch_filebrowser_transpose

# main list of apps
import argcache.urls
import debug_toolbar
import esp.accounting.urls
import esp.customforms.urls
import esp.formstack.urls
import esp.program.urls
import esp.qsdmedia.urls
import esp.random.urls
import esp.survey.urls
import esp.tests.urls
import esp.themes.urls
import esp.users.urls
import esp.varnish.urls

#TODO: move these out of the main urls.py
from esp.web.views import main
import esp.qsd.views
import esp.db.views
import esp.users.views
import esp.utils.views

autodiscover(admin_site)

# Override error pages
handler404 = 'esp.utils.web.error404'
handler500 = 'esp.utils.web.error500'

# Static media
urlpatterns = static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) + staticfiles_urlpatterns()

# Robots.txt
urlpatterns += [
    url('robots.txt', TemplateView.as_view(template_name="robots.txt", content_type="text/plain"))
]

# Admin stuff
urlpatterns += [
    url(r'^admin_tools/', include('admin_tools.urls')),
    url(r'^admin/doc/', include('django.contrib.admindocs.urls')),
    url(r'^admin/ajax_qsd/?$', esp.qsd.views.ajax_qsd),
    url(r'^admin/ajax_qsd_preview/?$', esp.qsd.views.ajax_qsd_preview),
    url(r'^admin/ajax_qsd_image_upload/?$', esp.qsd.views.ajax_qsd_image_upload),
    url(r'^admin/ajax_autocomplete/?', esp.db.views.ajax_autocomplete),
    url(r'^admin/filebrowser/', filebrowser_site.urls),
    url(r'^admin/', admin_site.urls),
    url(r'^accounts/login/$', esp.users.views.CustomLoginView.as_view()),
    url(r'^(?P<subsection>(learn|teach|program|help|manage|onsite))/?$', RedirectView.as_view(url='/%(subsection)s/index.html', permanent=True)),
]

# Adds missing trailing slash to any admin urls that haven't been matched yet.
urlpatterns += [
    url(r'^(?P<url>admin($|(.*[^/]$)))', RedirectView.as_view(url='/%(url)s/', permanent=True))]

# generic stuff
urlpatterns += [
    url(r'^$', main.home), # index
    url(r'^set_csrf_token', main.set_csrf_token), # tiny view used to set csrf token
]

# main list of apps (please consolidate more things into this!)
urlpatterns += [
    url(r'^cache/', include(argcache.urls)),
    url(r'^__debug__/', include(debug_toolbar.urls)),
    url(r'^accounting/', include(esp.accounting.urls)),
    url(r'^customforms', include(esp.customforms.urls)),
    url(r'^random', include(esp.random.urls)),
    url(r'^', include(esp.formstack.urls)),
    url(r'^',  include(esp.program.urls)),
    url(r'^download', include(esp.qsdmedia.urls)),
    url(r'^',  include(esp.survey.urls)),
    url('^javascript_tests', include(esp.tests.urls)),
    url(r'^themes', include(esp.themes.urls)),
    url(r'^myesp/', include(esp.users.urls)),
    url(r'^varnish/', include(esp.varnish.urls)),
]

urlpatterns += [
    # bios
    url(r'^(?P<tl>teach|learn)/teachers/', include('esp.web.urls')),
]

# Specific .html pages that have defaults
urlpatterns += [
    url(r'^(faq|faq\.html)$', main.FAQView.as_view(), name='FAQ'),
    url(r'^(contact|contact\.html)$', main.ContactUsView.as_view(), name='Contact Us'),
]

urlpatterns += [
    url(r'^(?P<url>.*)\.html$', esp.qsd.views.qsd),
]

# QSD Media
# aseering 8/14/2007: This ought to be able to be written in a simpler way...
urlpatterns += [
    # aseering - Is it worth consolidating these?  Two entries for the single "contact us! widget
    # Contact Us! pages
    url(r'^contact/contact/?$', main.contact),
    url(r'^contact/contact/(?P<section>[^/]+)/?$', main.contact),

    # Program stuff
    url(r'^(onsite|manage|teach|learn|volunteer|json)/([-A-Za-z0-9_ ]+)/([-A-Za-z0-9_ ]+)/([-A-Za-z0-9_ ]+)/([-A-Za-z0-9_ ]+)/?$', main.program),
    url(r'^(onsite|manage|teach|learn|volunteer|json)/([-A-Za-z0-9_ ]+)/([-A-Za-z0-9_ ]+)/([-A-Za-z0-9_ ]+)/?$', main.program),

    # all the archives
    url(r'^archives/([-A-Za-z0-9_ ]+)/?$', main.archives),
    url(r'^archives/([-A-Za-z0-9_ ]+)/([-A-Za-z0-9_ ]+)/?$', main.archives),
    url(r'^archives/([-A-Za-z0-9_ ]+)/([-A-Za-z0-9_ ]+)/([-A-Za-z0-9_ ]+)/?$', main.archives),

    url(r'^email/([0-9]+)/?$', main.public_email),
]

urlpatterns += [
url(r'^(?P<subsection>onsite|manage|teach|learn|volunteer)/(?P<program>[-A-Za-z0-9_ ]+)/?$', RedirectView.as_view(url='/%(subsection)s/%(program)s/index.html', permanent=True))]


urlpatterns += [
    url(r'^manage/templateoverride/(?P<template_id>[0-9]+)',
        esp.utils.views.diff_templateoverride),
]
