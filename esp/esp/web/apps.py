from esp.utils.apps import InstallConfig

class WebConfig(InstallConfig):
    name = 'esp.web'

    def ready(self):
        super(WebConfig, self).ready()

        from esp.web.filebrowser_patches import patch_filebrowser_transpose_and_clean_name

        patch_filebrowser_transpose_and_clean_name()
