from django.db import migrations, models

DESCRIPTIONS = {
    "SILVER": "Our starter tier — a modest number of toys at a time, ideal for trying out the library.",
    "PLATINUM": "Our mid tier — more toys at once, longer loans, and extra flexibility for growing families.",
    "DIAMOND": "Our premium tier — the most concurrent checkouts, longest loan periods, and best perks.",
}


def backfill_descriptions(apps, schema_editor):
    MembershipTier = apps.get_model("memberships", "MembershipTier")
    for code, description in DESCRIPTIONS.items():
        MembershipTier.objects.filter(code=code, description="").update(description=description)


class Migration(migrations.Migration):

    dependencies = [
        ("memberships", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="membershiptier",
            name="description",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.RunPython(backfill_descriptions, migrations.RunPython.noop),
    ]
