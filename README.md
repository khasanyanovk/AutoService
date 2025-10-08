# AutoService Manager - Streamlined Automotive Care

A full-stack web application designed for "Pochinim Vse" auto repair shop. This system modernizes the customer service experience and internal workflow management.

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-092E20?style=for-the-badge&logo=django&logoColor=white)
![HTML5](https://img.shields.io/badge/HTML5-E34F26?style=for-the-badge&logo=html5&logoColor=white)
![Bootstrap](https://img.shields.io/badge/Bootstrap-7952B3?style=for-the-badge&logo=bootstrap&logoColor=white)
![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?style=for-the-badge&logo=javascript&logoColor=black)

## Key Features

### For Clients
- Book diagnostic appointments online
- Track repair status in real-time
- Monitor parts order delivery status
- User-friendly customer portal

### For Managers
- Manage service schedule and appointments
- Resolve booking conflicts proactively
- Update parts shipment statuses
- Customer communication tools
- Administrative backend dashboard

## Project Goal

This project aims to enhance transparency, efficiency, and customer satisfaction for automotive service management.

## Usage

### 1. Clone a repository
```bash
git clone https://github.com/khasanyanovk/AutoService.git
cd AutoService
```
### 2. Create virtual environment
```bash
python -m venv venv

# For Windows:
venv\Scripts\activate

# For Linux/macOS:
source venv/bin/activate
```
### 3. Install dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```
### 4. Performing migrations
```bash
python manage.py makemigrations
python manage.py migrate
```
### 5. Set initial data
```bash
python manage.py runscript fill_car_data
python manage.py runscript seed_data
```
### 6. Run server
```bash
python manage.py runserver
```
### 7. Run tests
```bash
# Run
python manage.py test

# Debug
python manage.py test --verbosity=2

# Coverage
python manage.py test --coverage
```