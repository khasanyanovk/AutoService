from django.core.management.base import BaseCommand
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = "Добавляет тестовых пользователей в БД"

    def handle(self, *args, **options):
        users_data = [
            {
                "username": "alexeypetrov",
                "first_name": "Алексей",
                "last_name": "Петров",
                "email": "petrov.aleksey@gmail.com",
                "password": "Petrov2024!",
            },
            {
                "username": "mariasmirn",
                "first_name": "Мария",
                "last_name": "Смирнова",
                "email": "smirnova.maria@mail.ru",
                "password": "MariaSmirnova_24",
            },
            {
                "username": "dmitriykozlov",
                "first_name": "Дмитрий",
                "last_name": "Козлов",
                "email": "kozlov.dmitriy@yandex.ru",
                "password": "KozlovDm2024",
            },
            {
                "username": "annanovikova",
                "first_name": "Анна",
                "last_name": "Новикова",
                "email": "novikova.anna@gmail.com",
                "password": "AnnaNovikova24!",
            },
            {
                "username": "sergeyvolkov",
                "first_name": "Сергей",
                "last_name": "Волков",
                "email": "volkov.sergey@mail.ru",
                "password": "VolkovSergey2024",
            },
        ]

        created_count = 0
        skipped_count = 0

        for user_data in users_data:
            username = user_data["username"]

            if User.objects.filter(username=username).exists():
                self.stdout.write(
                    self.style.WARNING(f"⚠️  Пользователь {username} уже существует")
                )
                skipped_count += 1
                continue

            if User.objects.filter(email=user_data["email"]).exists():
                self.stdout.write(
                    self.style.WARNING(
                        f'⚠️  Email {user_data["email"]} уже используется'
                    )
                )
                skipped_count += 1
                continue

            user = User.objects.create_user(
                username=user_data["username"],
                email=user_data["email"],
                password=user_data["password"],
                first_name=user_data["first_name"],
                last_name=user_data["last_name"],
            )

            self.stdout.write(
                self.style.SUCCESS(
                    f"✅ Создан пользователь: {user.get_full_name()} (@{username})"
                )
            )
            created_count += 1

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(f"Создано: {created_count} | Пропущено: {skipped_count}")
        )
