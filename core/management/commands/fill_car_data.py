from django.core.management.base import BaseCommand
from core.models import CarBrand, CarModel


class Command(BaseCommand):
    help = "Заполняет базу данных марками и моделями автомобилей"

    def handle(self, *args, **options):
        car_data = {
            "Toyota": ["Corolla", "Camry", "RAV4", "Land Cruiser", "Hilux"],
            "Honda": [
                "Accord",
                "Civic",
                "CR-V",
                "Pilot",
                "Fit",
                "Legend",
                "Odyssey",
                "Vigor",
            ],
            "Ford": ["Focus", "Fiesta", "Mustang", "Explorer", "F-150"],
            "Chevrolet": [
                "Cruze",
                "Malibu",
                "Equinox",
                "Tahoe",
                "Silverado",
                "Avalanche",
                "Lacetti",
                "Camaro",
            ],
            "Volkswagen": ["Golf", "Passat", "Tiguan", "Jetta", "Polo"],
            "BMW": ["3 Series", "5 Series", "X5", "X3", "X6", "7 Series"],
            "Mercedes-Benz": [
                "C-Class",
                "E-Class",
                "S-Class",
                "GL-Class",
                "GLE",
                "A-Class",
            ],
            "Audi": ["A4", "A6", "Q5", "Q7", "A3"],
            "Nissan": [
                "Altima",
                "Sentra",
                "Rogue",
                "Pathfinder",
                "Maxima",
                "Primera",
                "XTrail",
                "Quashkai",
            ],
            "Hyundai": [
                "Elantra",
                "Sonata",
                "Tucson",
                "Santa Fe",
                "Accent",
                "Terracan",
            ],
            "Kia": ["Rio", "Optima", "Sportage", "Sorento", "Soul"],
            "Volvo": ["S60", "S90", "XC60", "XC90", "V60"],
            "Mazda": ["3", "6", "CX-5", "CX-9", "MX-5", "RX-8", "CX-7"],
            "Subaru": ["Impreza", "Outback", "Forester", "Legacy", "Crosstrek"],
            "Lexus": ["ES", "RX300", "NX", "LS430", "GX", "GS430", "LS300"],
            "Jeep": ["Grand Cherokee", "Cherokee", "Wrangler", "Compass", "Renegade"],
            "Renault": ["Logan", "Sandero", "Duster", "Kaptur", "Arkana"],
            "Peugeot": ["208", "308", "3008", "5008", "2008"],
            "Skoda": ["Octavia", "Superb", "Kodiaq", "Karoq", "Fabia", "Roomster"],
            "Mitsubishi": [
                "Lancer",
                "Outlander",
                "Pajero",
                "ASX",
                "Eclipse Cross",
                "Galant",
                "Spider",
            ],
            "Citroen": ["C4", "C5", "Berlingo", "C3", "DS4", "Jumpy", "Xm"],
            "Opel": [
                "Astra",
                "Corsa",
                "Insignia",
                "Mokka",
                "Crossland",
                "GT",
                "Tigra",
                "Vectra",
            ],
            "Suzuki": [
                "Swift",
                "Grand Vitara",
                "S-Cross",
                "Jimny",
                "Ignis",
                "Vitara",
                "Kizashi",
            ],
            "Land Rover": ["Range Rover", "Discovery", "Defender", "Evoque", "Sport"],
            "Porsche": [
                "911",
                "Cayenne",
                "Panamera",
                "Macan",
                "Taycan",
                "964",
                "Carrera",
            ],
            "Fiat": ["500", "Panda", "Tipo", "Doblo", "500X"],
            "Seat": ["Leon", "Ibiza", "Ateca", "Arona", "Tarraco"],
            "Dacia": ["Sandero", "Duster", "Logan", "Spring", "Jogger"],
            "Alfa Romeo": ["147", "Alfasud", "Giulietta", "Canguro"],
            "Lada": ["Granta", "Vesta", "Niva", "XRAY", "Largus"],
        }

        for brand_name, models in car_data.items():
            brand, created = CarBrand.objects.get_or_create(name=brand_name)
            for model_name in models:
                CarModel.objects.get_or_create(brand=brand, name=model_name)
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Добавлена модель {model_name} для марки {brand_name}"
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(
                "База данных успешно заполнена марками и моделями автомобилей"
            )
        )
