from django.apps import AppConfig
from django.db.models.signals import post_migrate

class HostelConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'hostel'

    def ready(self):
        from hostel.scripts.populate_rooms import run  # <- fix here
        post_migrate.connect(run_after_migrate, sender=self)

def run_after_migrate(sender, **kwargs):
    from hostel.scripts.populate_rooms import run  # <- fix here
    run()
