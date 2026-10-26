# eCom/management/commands/setup_groups.py

from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission

'''
This command script is used to create groups and permissions for the eCom app.
This script can be run from the command prompt during installation of the app
and will ensure that groups and permissions are loaded to the database before
the app can be used.

IMPORTANT: Please ensure to run migrations first before running this script to
ensure that custom model permissions are loaded to the database before group
creation can take place.
'''


class Command(BaseCommand):
    help = "Creates custom user groups and assigns model permissions."

    def handle(self, *args, **options):
        '''
        This function will handle custom group creation and assign the required
        permissions. Standard Django permissions will be cleared to prevent
        duplications of permissions.
        '''

        # Define groups with permissions:
        group_permissions = {
            "Vendor": [
                "add_stores",
                "change_stores",
                "delete_stores",
                "view_stores",
                "add_products",
                "change_products",
                "delete_products",
            ],
            "Buyer": [
                "view_products",
            ],
        }

        self.stdout.write(self.style.WARNING("Setting up groups..."))

        for group, permissions in group_permissions.items():
            group, created = Group.objects.get_or_create(name=group)

            if created:
                self.stdout.write(
                    self.style.SUCCESS(f"Created group: '{group}'")
                )
            else:
                self.stdout.write(
                    f"Group {group} already exists. Updating permissions..."
                )

            # Clear default permissions to prevent duplication
            group.permissions.clear()

            # Assign new permissions to the correct groups
            for perm in permissions:
                try:
                    permission = Permission.objects.get(codename=perm)
                    group.permissions.add(permission)
                except Permission.DoesNotExist:
                    self.stdout.write(
                        self.style.ERROR(
                            f"Permission {perm} not found."
                            "Enusre migrations have run."
                        )
                    )

        self.stdout.write(
            self.style.SUCCESS(
                "Group and permissions setup completed."
            )
        )
