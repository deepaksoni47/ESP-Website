import os
import tempfile
from importlib import import_module

from PIL import Image as _PILImage
from django.contrib import messages
from django.core.files import File as DjangoFile
from django.utils.translation import gettext_lazy as _lazy


_PATCH_APPLIED = False


def _preserve_basename_lowercase_extension(name, convert_fn):
    """Normalize filename: preserve basename case, lowercase extension only.

    Args:
        name: Original filename string
        convert_fn: Filebrowser's original convert_filename function

    Returns:
        Normalized filename with lowercased extension
    """
    raw_name = (name or '').strip()
    if not raw_name:
        return raw_name

    converted_name = convert_fn(raw_name)
    # If result contains path separators, it's a directory path - return as-is
    if '/' in converted_name:
        return converted_name

    # Split and lowercase only the extension, preserve basename
    filename_root, filename_ext = os.path.splitext(raw_name)
    if filename_ext:
        return filename_root + filename_ext.lower()

    return converted_name


def patch_filebrowser_transpose_and_clean_name():
    global _PATCH_APPLIED

    if _PATCH_APPLIED:
        return

    _fb_actions = import_module('filebrowser.actions')
    _fb_forms = import_module('filebrowser.forms')
    _fb_settings = import_module('filebrowser.settings')
    _fb_utils = import_module('filebrowser.utils')
    version_quality = _fb_settings.VERSION_QUALITY
    original_convert_filename = _fb_utils.convert_filename

    def _patched_convert_filename(value):
        return _preserve_basename_lowercase_extension(
            value, original_convert_filename)

    _fb_utils.convert_filename = _patched_convert_filename
    if hasattr(_fb_forms, 'convert_filename'):
        _fb_forms.convert_filename = _patched_convert_filename

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
                               quality=version_quality,
                               optimize=(ext_lower != '.gif'))
            except IOError:
                new_image.save(tmpfile, format=img_format,
                               quality=version_quality)

            original_path = fileobject.path
            try:
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

    def _patched_clean_name(self):
        if self.cleaned_data['name']:
            import re
            if not re.search(_fb_settings.FOLDER_REGEX, self.cleaned_data['name'], re.U):
                from django.forms import ValidationError
                raise ValidationError(
                    _lazy('Only letters, numbers, underscores, spaces '
                          'and hyphens are allowed.'))

            new_name = _patched_convert_filename(self.cleaned_data['name'])
            new_path = os.path.join(self.path, new_name)
            current_path = self.fileobject.path

            is_same = new_path.lower() == current_path.lower()

            if self.site.storage.isdir(new_path) and not is_same:
                from django.forms import ValidationError
                raise ValidationError(_lazy('The Folder already exists.'))
            elif self.site.storage.isfile(new_path) and not is_same:
                from django.forms import ValidationError
                raise ValidationError(_lazy('The File already exists.'))

            return new_name
        return self.cleaned_data['name']

    _fb_actions.transpose_image = _patched_transpose_image
    _fb_forms.ChangeForm.clean_name = _patched_clean_name
    _PATCH_APPLIED = True
