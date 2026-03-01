from esp.utils.apps import InstallConfig


class WebConfig(InstallConfig):
    name = 'esp.web'

    def ready(self):
        super(WebConfig, self).ready()
        # Monkey patches removed: File extension lowercasing is handled by
        # LowercaseExtensionStorage backend (see esp.web.storage
        # and django_settings.py DEFAULT_FILE_STORAGE)
