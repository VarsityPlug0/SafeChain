from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

class Command(BaseCommand):
    help = 'Displays all users and their staff/superuser status.'

    def handle(self, *args, **options):
        User = get_user_model()
        users = User.objects.all()

        if not users:
            self.stdout.write(self.style.WARNING('No users found in the database.'))
            return

        self.stdout.write(self.style.SUCCESS('--- User Permissions Report ---'))
        for user in users:
            self.stdout.write(f"Email: {user.email}, Username: {user.username}")
            self.stdout.write(f"  Is Staff: {user.is_staff}")
            self.stdout.write(f"  Is Superuser: {user.is_superuser}")
            self.stdout.write("-" * 20) 