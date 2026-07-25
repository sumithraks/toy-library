from django.core.management.base import BaseCommand

from apps.inventory import services
from apps.inventory.models import Toy


class Command(BaseCommand):
    help = (
        "Generate description embeddings for toys missing one (e.g. toys created "
        "before semantic search was added, or after a Voyage AI outage skipped "
        "an intake). Use --all to regenerate every toy's embedding instead."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--all",
            action="store_true",
            help="Regenerate embeddings for every toy with a description, not just missing ones.",
        )

    def handle(self, *args, **options):
        qs = Toy.objects.exclude(description="")
        if not options["all"]:
            qs = qs.filter(description_embedding__isnull=True)

        total = qs.count()
        self.stdout.write(f"Embedding {total} toy(s)...")
        succeeded = 0
        for toy in qs.iterator():
            was_missing = toy.description_embedding is None
            services.embed_toy_description(toy)
            if toy.description_embedding is not None and (was_missing or options["all"]):
                succeeded += 1

        self.stdout.write(self.style.SUCCESS(f"Embedded {succeeded}/{total} toy(s)."))
