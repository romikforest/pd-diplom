import sys

from coverage import Coverage
from django.core.management.commands.test import Command as BaseCommand


class Command(BaseCommand):
    def handle(self, *args, **kwargs):  # pragma: no cover
        self.stdout.write('Run test with coverage..')
        cov = Coverage(branch=True, )
        cov.erase()
        cov.start()

        super().handle(*args, **kwargs)

        cov.stop()
        cov.save()
        covered = cov.report(skip_covered=True)
        if covered < 90:
            sys.exit(1)
