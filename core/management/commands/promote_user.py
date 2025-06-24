from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist

class Command(BaseCommand):
    help = 'Promotes a user to superuser status.'

    def add_arguments(self, parser):
        parser.add_argument('email', type=str, help='The email address of the user to promote.')

    def handle(self, *args, **options):
        User = get_user_model()
        email = options['email']

        try:
            user = User.objects.get(email__iexact=email)
            user.is_staff = True
            user.is_superuser = True
            user.save()
            self.stdout.write(self.style.SUCCESS(f'Successfully promoted user {user.email} to superuser.'))
        except ObjectDoesNotExist:
            self.stdout.write(self.style.ERROR(f'User with email {email} not found.')) 