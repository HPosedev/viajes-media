from datetime import date, timedelta
import hashlib
import random
from typing import Dict, List, Optional, Tuple
import unicodedata
import urllib.parse
from src.core.models import Accommodation, AccommodationType
from src.providers.base import AccommodationProvider


# Curated realistic accommodations for popular Spanish getaway destinations
CURATED_ACCOMMODATIONS: Dict[str, List[Dict]] = {
    "Santiago de Compostela": [
        {
            "name": "Parador de Santiago - Hostal Dos Reis Católicos",
            "type": AccommodationType.HOTEL,
            "price_per_night": 195.0,
            "rating": 9.4,
            "reviews_count": 2840,
            "address": "Praza do Obradoiro 1, Santiago de Compostela",
            "booking_url": "https://www.booking.com/hotel/es/parador-de-santiago-de-compostela.es.html",
            "image_url": "https://images.unsplash.com/photo-1566073771259-6a8506099945?w=500"
        },
        {
            "name": "Hotel San Bieito Boutique",
            "type": AccommodationType.HOTEL,
            "price_per_night": 78.0,
            "rating": 9.1,
            "reviews_count": 1120,
            "address": "Rúa de San Bieito 1, Casco Histórico",
            "booking_url": "https://www.booking.com/hotel/es/san-bieito.es.html",
            "image_url": "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?w=500"
        },
        {
            "name": "Apartamentos Compostela Real Obradoiro",
            "type": AccommodationType.APARTMENT,
            "price_per_night": 95.0,
            "rating": 8.9,
            "reviews_count": 640,
            "address": "Rúa do Vilar 42, Santiago de Compostela",
            "booking_url": "https://www.airbnb.es/s/Santiago-de-Compostela/homes",
            "image_url": "https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?w=500"
        },
        {
            "name": "Duplex Vintage con Vistas a la Catedral",
            "type": AccommodationType.APARTMENT,
            "price_per_night": 110.0,
            "rating": 9.3,
            "reviews_count": 410,
            "address": "Rúa da Caldeirería 18, Santiago de Compostela",
            "booking_url": "https://www.airbnb.es/s/Santiago-de-Compostela/homes",
            "image_url": "https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?w=500"
        },
        {
            "name": "Hotel Altaïr Eco-Chic",
            "type": AccommodationType.HOTEL,
            "price_per_night": 88.0,
            "rating": 9.0,
            "reviews_count": 920,
            "address": "Rúa dos Loureiros 12, Santiago de Compostela",
            "booking_url": "https://www.booking.com/hotel/es/altair-santiago.es.html",
            "image_url": "https://images.unsplash.com/photo-1590490360182-c33d57733427?w=500"
        }
    ],
    "A Coruña": [
        {
            "name": "Hotel Riazor Primera Línea",
            "type": AccommodationType.HOTEL,
            "price_per_night": 85.0,
            "rating": 8.7,
            "reviews_count": 1950,
            "address": "Andén de Riazor 25, A Coruña",
            "booking_url": "https://www.booking.com/hotel/es/riazor.es.html",
            "image_url": "https://images.unsplash.com/photo-1566073771259-6a8506099945?w=500"
        },
        {
            "name": "Apartamento Marítimo con Galerías de la Marina",
            "type": AccommodationType.APARTMENT,
            "price_per_night": 98.0,
            "rating": 9.2,
            "reviews_count": 530,
            "address": "Paseo da Dársena 8, A Coruña",
            "booking_url": "https://www.airbnb.es/s/A-Coruna/homes",
            "image_url": "https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?w=500"
        },
        {
            "name": "NH Collection A Coruña Finisterre",
            "type": AccommodationType.HOTEL,
            "price_per_night": 135.0,
            "rating": 9.0,
            "reviews_count": 2200,
            "address": "Paseo del Parrote 2-4, A Coruña",
            "booking_url": "https://www.booking.com/hotel/es/finisterre.es.html",
            "image_url": "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?w=500"
        },
        {
            "name": "Loft Moderno Plaza de Lugo",
            "type": AccommodationType.APARTMENT,
            "price_per_night": 75.0,
            "rating": 8.8,
            "reviews_count": 310,
            "address": "Rúa Compostela 9, A Coruña",
            "booking_url": "https://www.airbnb.es/s/A-Coruna/homes",
            "image_url": "https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?w=500"
        }
    ],
    "Vigo": [
        {
            "name": "Gran Hotel Nagari Boutique & Spa",
            "type": AccommodationType.HOTEL,
            "price_per_night": 140.0,
            "rating": 9.2,
            "reviews_count": 2150,
            "address": "Praza de Compostela 21, Vigo",
            "booking_url": "https://www.booking.com/hotel/es/gran-nagari-boutique-spa.es.html",
            "image_url": "https://images.unsplash.com/photo-1566073771259-6a8506099945?w=500"
        },
        {
            "name": "Apartamentos Casco Vello Ría de Vigo",
            "type": AccommodationType.APARTMENT,
            "price_per_night": 82.0,
            "rating": 8.9,
            "reviews_count": 480,
            "address": "Rúa Real 14, Casco Vello, Vigo",
            "booking_url": "https://www.airbnb.es/s/Vigo/homes",
            "image_url": "https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?w=500"
        },
        {
            "name": "Hotel Axis Vigo",
            "type": AccommodationType.HOTEL,
            "price_per_night": 74.0,
            "rating": 8.5,
            "reviews_count": 1600,
            "address": "Rúa María Berdiales 8, Vigo",
            "booking_url": "https://www.booking.com/hotel/es/axis-vigo.es.html",
            "image_url": "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?w=500"
        }
    ],
    "Pontevedra": [
        {
            "name": "Parador de Pontevedra - Casa del Barón",
            "type": AccommodationType.HOTEL,
            "price_per_night": 125.0,
            "rating": 9.1,
            "reviews_count": 1420,
            "address": "Rúa do Barón 19, Pontevedra",
            "booking_url": "https://www.booking.com/hotel/es/parador-de-pontevedra.es.html",
            "image_url": "https://images.unsplash.com/photo-1566073771259-6a8506099945?w=500"
        },
        {
            "name": "Apartamento Boutique Plaza de la Leña",
            "type": AccommodationType.APARTMENT,
            "price_per_night": 79.0,
            "rating": 9.3,
            "reviews_count": 390,
            "address": "Praza da Leña 5, Casco Vello, Pontevedra",
            "booking_url": "https://www.airbnb.es/s/Pontevedra/homes",
            "image_url": "https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?w=500"
        },
        {
            "name": "Hotel Rías Bajas Centro",
            "type": AccommodationType.HOTEL,
            "price_per_night": 68.0,
            "rating": 8.4,
            "reviews_count": 980,
            "address": "Rúa Daniel de la Sota 7, Pontevedra",
            "booking_url": "https://www.booking.com/hotel/es/rias-bajas.es.html",
            "image_url": "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?w=500"
        }
    ],
    "Vilagarcía de Arousa": [
        {
            "name": "Hotel Pazo O Rial Histórico",
            "type": AccommodationType.HOTEL,
            "price_per_night": 88.0,
            "rating": 8.8,
            "reviews_count": 670,
            "address": "Rúa do Rial 1, Vilagarcía de Arousa",
            "booking_url": "https://www.booking.com/hotel/es/pazo-o-rial.es.html",
            "image_url": "https://images.unsplash.com/photo-1566073771259-6a8506099945?w=500"
        },
        {
            "name": "Ático Ría de Arousa con Terraza Panorámica",
            "type": AccommodationType.APARTMENT,
            "price_per_night": 72.0,
            "rating": 9.2,
            "reviews_count": 280,
            "address": "Avenida da Mariña 45, Vilagarcía",
            "booking_url": "https://www.airbnb.es/s/Vilagarcia-de-Arousa/homes",
            "image_url": "https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?w=500"
        }
    ],
    "Ourense": [
        {
            "name": "Hotel Carrís Cardenal Quevedo",
            "type": AccommodationType.HOTEL,
            "price_per_night": 78.0,
            "rating": 8.9,
            "reviews_count": 1340,
            "address": "Rúa Cardenal Quevedo 28, Ourense",
            "booking_url": "https://www.booking.com/hotel/es/carris-cardenal-quevedo.es.html",
            "image_url": "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?w=500"
        },
        {
            "name": "Apartamentos Termas As Burgas",
            "type": AccommodationType.APARTMENT,
            "price_per_night": 69.0,
            "rating": 9.0,
            "reviews_count": 420,
            "address": "Rúa das Burgas 6, Ourense",
            "booking_url": "https://www.airbnb.es/s/Ourense/homes",
            "image_url": "https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?w=500"
        },
        {
            "name": "Hotel Princess Ourense",
            "type": AccommodationType.HOTEL,
            "price_per_night": 65.0,
            "rating": 8.3,
            "reviews_count": 1100,
            "address": "Avenida de La Habana 63, Ourense",
            "booking_url": "https://www.booking.com/hotel/es/princess-ourense.es.html",
            "image_url": "https://images.unsplash.com/photo-1566073771259-6a8506099945?w=500"
        }
    ],
    "Toledo": [
        {
            "name": "Parador de Toledo con Vistas Panorámicas",
            "type": AccommodationType.HOTEL,
            "price_per_night": 175.0,
            "rating": 9.3,
            "reviews_count": 3100,
            "address": "Cerro del Emperador s/n, Toledo",
            "booking_url": "https://www.booking.com/hotel/es/parador-de-toledo.es.html",
            "image_url": "https://images.unsplash.com/photo-1566073771259-6a8506099945?w=500"
        },
        {
            "name": "Boutique Hotel San Román Judería",
            "type": AccommodationType.HOTEL,
            "price_per_night": 89.0,
            "rating": 9.1,
            "reviews_count": 1250,
            "address": "Calle San Román 6, Casco Antiguo, Toledo",
            "booking_url": "https://www.booking.com/hotel/es/san-roman-toledo.es.html",
            "image_url": "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?w=500"
        },
        {
            "name": "Apartamento Alcázar Luxury Suites",
            "type": AccommodationType.APARTMENT,
            "price_per_night": 95.0,
            "rating": 9.0,
            "reviews_count": 680,
            "address": "Plaza de Zocodover 12, Toledo",
            "booking_url": "https://www.airbnb.es/s/Toledo/homes",
            "image_url": "https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?w=500"
        },
        {
            "name": "Cigarral Medieval con Patio Toledano",
            "type": AccommodationType.APARTMENT,
            "price_per_night": 115.0,
            "rating": 9.4,
            "reviews_count": 340,
            "address": "Paseo de la Rosa 34, Toledo",
            "booking_url": "https://www.airbnb.es/s/Toledo/homes",
            "image_url": "https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?w=500"
        }
    ],
    "Segovia": [
        {
            "name": "Hotel Real Segovia Acueducto",
            "type": AccommodationType.HOTEL,
            "price_per_night": 92.0,
            "rating": 9.0,
            "reviews_count": 1820,
            "address": "Calle Juan Bravo 38, Segovia",
            "booking_url": "https://www.booking.com/hotel/es/real-segovia.es.html",
            "image_url": "https://images.unsplash.com/photo-1566073771259-6a8506099945?w=500"
        },
        {
            "name": "Apartamento Mirador del Acueducto",
            "type": AccommodationType.APARTMENT,
            "price_per_night": 85.0,
            "rating": 9.2,
            "reviews_count": 520,
            "address": "Plaza del Azoguejo 7, Segovia",
            "booking_url": "https://www.airbnb.es/s/Segovia/homes",
            "image_url": "https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?w=500"
        },
        {
            "name": "Hotel Áurea Convento Capuchinos",
            "type": AccommodationType.HOTEL,
            "price_per_night": 130.0,
            "rating": 9.4,
            "reviews_count": 2100,
            "address": "Plazuela Capuchinos 2, Segovia",
            "booking_url": "https://www.booking.com/hotel/es/eurostars-convento-capuchinos.es.html",
            "image_url": "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?w=500"
        }
    ],
    "Ávila": [
        {
            "name": "Parador de Ávila - Palacio Piedras Albas",
            "type": AccommodationType.HOTEL,
            "price_per_night": 115.0,
            "rating": 9.0,
            "reviews_count": 1640,
            "address": "Marqués de Canales y Chozas 2, Ávila",
            "booking_url": "https://www.booking.com/hotel/es/parador-de-avila.es.html",
            "image_url": "https://images.unsplash.com/photo-1566073771259-6a8506099945?w=500"
        },
        {
            "name": "Apartamentos Muralla Medieval",
            "type": AccommodationType.APARTMENT,
            "price_per_night": 68.0,
            "rating": 8.9,
            "reviews_count": 420,
            "address": "Calle San Segundo 15, Ávila",
            "booking_url": "https://www.airbnb.es/s/Avila/homes",
            "image_url": "https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?w=500"
        }
    ],
    "Córdoba": [
        {
            "name": "Hospes Palacio del Bailío Histórico",
            "type": AccommodationType.HOTEL,
            "price_per_night": 180.0,
            "rating": 9.3,
            "reviews_count": 2240,
            "address": "Ramírez de las Casas Deza 10, Córdoba",
            "booking_url": "https://www.booking.com/hotel/es/palacio-del-bailio.es.html",
            "image_url": "https://images.unsplash.com/photo-1566073771259-6a8506099945?w=500"
        },
        {
            "name": "Apartamento Patio de los Naranjos Judería",
            "type": AccommodationType.APARTMENT,
            "price_per_night": 79.0,
            "rating": 9.1,
            "reviews_count": 610,
            "address": "Calle Judería 8, Córdoba",
            "booking_url": "https://www.airbnb.es/s/Cordoba/homes",
            "image_url": "https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?w=500"
        },
        {
            "name": "Hotel Boutique Madinat",
            "type": AccommodationType.HOTEL,
            "price_per_night": 96.0,
            "rating": 9.4,
            "reviews_count": 1380,
            "address": "Calle Cabezas 17, Córdoba",
            "booking_url": "https://www.booking.com/hotel/es/hotel-madinat.es.html",
            "image_url": "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?w=500"
        }
    ],
    "Cádiz": [
        {
            "name": "Parador de Cádiz Hotel Atlántico",
            "type": AccommodationType.HOTEL,
            "price_per_night": 165.0,
            "rating": 9.2,
            "reviews_count": 2980,
            "address": "Avenida Duque de Nájera 9, Cádiz",
            "booking_url": "https://www.booking.com/hotel/es/parador-de-cadiz.es.html",
            "image_url": "https://images.unsplash.com/photo-1566073771259-6a8506099945?w=500"
        },
        {
            "name": "Ático Caleta con Terraza al Océano",
            "type": AccommodationType.APARTMENT,
            "price_per_night": 95.0,
            "rating": 9.3,
            "reviews_count": 520,
            "address": "Barrio de la Viña 12, Cádiz",
            "booking_url": "https://www.airbnb.es/s/Cadiz/homes",
            "image_url": "https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?w=500"
        },
        {
            "name": "Hotel Casa de las Cuatro Torres",
            "type": AccommodationType.HOTEL,
            "price_per_night": 89.0,
            "rating": 9.1,
            "reviews_count": 1150,
            "address": "Plaza de España 13, Cádiz",
            "booking_url": "https://www.booking.com/hotel/es/casa-de-las-cuatro-torres.es.html",
            "image_url": "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?w=500"
        }
    ],
    "Girona": [
        {
            "name": "Hotel Nord 1901 Superior Casco Antiguo",
            "type": AccommodationType.HOTEL,
            "price_per_night": 120.0,
            "rating": 9.2,
            "reviews_count": 1780,
            "address": "Carrer Nord 19, Girona",
            "booking_url": "https://www.booking.com/hotel/es/nord-1901.es.html",
            "image_url": "https://images.unsplash.com/photo-1566073771259-6a8506099945?w=500"
        },
        {
            "name": "Apartament Onyar River Views",
            "type": AccommodationType.APARTMENT,
            "price_per_night": 92.0,
            "rating": 9.4,
            "reviews_count": 640,
            "address": "Rambla de la Llibertat 22, Girona",
            "booking_url": "https://www.airbnb.es/s/Girona/homes",
            "image_url": "https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?w=500"
        }
    ],
    "Benicarló": [
        {
            "name": "Parador de Benicarló",
            "type": AccommodationType.HOTEL,
            "price_per_night": 65.0,
            "rating": 8.8,
            "reviews_count": 1820,
            "address": "Avinguda del Papa Luna 5, Benicarló",
            "booking_url": "https://www.booking.com/hotel/es/parador-de-benicarlo.es.html",
            "image_url": "https://images.unsplash.com/photo-1566073771259-6a8506099945?w=500"
        },
        {
            "name": "Hotel Iberflat Marynton",
            "type": AccommodationType.HOTEL,
            "price_per_night": 52.0,
            "rating": 8.3,
            "reviews_count": 950,
            "address": "Passeig Marítim 32, Puerto Pesquero, Benicarló",
            "booking_url": "https://www.booking.com/hotel/es/marynton.es.html",
            "image_url": "https://images.unsplash.com/photo-1590490360182-c33d57733427?w=500"
        },
        {
            "name": "Hotel Rosi",
            "type": AccommodationType.HOTEL,
            "price_per_night": 48.0,
            "rating": 8.8,
            "reviews_count": 850,
            "address": "Carrer del Doctor Fleming 50, Benicarló",
            "booking_url": "https://www.booking.com/hotel/es/hotel-rosi.es.html",
            "image_url": "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?w=500"
        },
        {
            "name": "Gran Hotel Peñíscola & Spa",
            "type": AccommodationType.HOTEL,
            "price_per_night": 49.0,
            "rating": 8.2,
            "reviews_count": 2150,
            "address": "Avinguda del Papa Luna 132, Playa Norte, Benicarló-Peñíscola",
            "booking_url": "https://www.booking.com/hotel/es/gran-peniscola.es.html",
            "image_url": "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?w=500"
        },
        {
            "name": "Hotel RH Portocristo & Wellness",
            "type": AccommodationType.HOTEL,
            "price_per_night": 55.0,
            "rating": 8.9,
            "reviews_count": 1340,
            "address": "Avinguda del Papa Luna 2, Benicarló-Peñíscola",
            "booking_url": "https://www.booking.com/hotel/es/rh-portocristo.es.html",
            "image_url": "https://images.unsplash.com/photo-1590490360182-c33d57733427?w=500"
        },
        {
            "name": "Hotel Boutique El Pinche de Oro",
            "type": AccommodationType.HOTEL,
            "price_per_night": 38.0,
            "rating": 8.5,
            "reviews_count": 690,
            "address": "Paseo Marítimo 46, Centro Histórico, Benicarló",
            "booking_url": "https://www.booking.com/hotel/es/el-pinche-de-oro.es.html",
            "image_url": "https://images.unsplash.com/photo-1566073771259-6a8506099945?w=500"
        },
        {
            "name": "Iberflat Apartamentos Marynton",
            "type": AccommodationType.APARTMENT,
            "price_per_night": 55.0,
            "rating": 8.4,
            "reviews_count": 520,
            "address": "Carrer del Port 14, Puerto Pesquero, Benicarló",
            "booking_url": "https://www.booking.com/hotel/es/apartamentos-marynton.es.html",
            "image_url": "https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?w=500"
        },
        {
            "name": "Apartamentos Leman",
            "type": AccommodationType.APARTMENT,
            "price_per_night": 46.0,
            "rating": 8.7,
            "reviews_count": 410,
            "address": "Avinguda de Méndez Núñez 44, Benicarló",
            "booking_url": "https://www.booking.com/hotel/es/apartamentos-lago-leman.es.html",
            "image_url": "https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?w=500"
        },
        {
            "name": "Las Cebras Apartamentos Turísticos",
            "type": AccommodationType.APARTMENT,
            "price_per_night": 50.0,
            "rating": 8.9,
            "reviews_count": 330,
            "address": "Passeig Marítim 104, Benicarló",
            "booking_url": "https://www.booking.com/hotel/es/las-cebras-hostel.es.html",
            "image_url": "https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?w=500"
        },
        {
            "name": "Apartamentos Turísticos Jardines del Plaza",
            "type": AccommodationType.APARTMENT,
            "price_per_night": 64.0,
            "rating": 8.2,
            "reviews_count": 890,
            "address": "Avenida Papa Luna 156, Benicarló-Peñíscola",
            "booking_url": "https://www.booking.com/hotel/es/jardines-del-plaza.es.html",
            "image_url": "https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?w=500"
        },
        {
            "name": "Mas del Rey Boutique B&B",
            "type": AccommodationType.HOTEL,
            "price_per_night": 75.0,
            "rating": 9.3,
            "reviews_count": 340,
            "address": "Partida Mas del Rey s/n, Benicarló",
            "booking_url": "https://www.booking.com/hotel/es/mas-del-rey-benicarlo.es.html",
            "image_url": "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?w=500"
        },
        {
            "name": "Pensión Belmonte II",
            "type": AccommodationType.HOTEL,
            "price_per_night": 36.0,
            "rating": 8.3,
            "reviews_count": 290,
            "address": "Carrer de Sant Francesc 45, Benicarló",
            "booking_url": "https://www.booking.com/hotel/es/pension-belmonte.es.html",
            "image_url": "https://images.unsplash.com/photo-1566073771259-6a8506099945?w=500"
        },
        {
            "name": "Pensión Casa Mika",
            "type": AccommodationType.HOTEL,
            "price_per_night": 38.0,
            "rating": 8.6,
            "reviews_count": 240,
            "address": "Carrer de Cristo del Mar 28, Benicarló",
            "booking_url": "https://www.booking.com/hotel/es/casa-mika.es.html",
            "image_url": "https://images.unsplash.com/photo-1590490360182-c33d57733427?w=500"
        },
        {
            "name": "Apartamentos Benicarló Playa 3000",
            "type": AccommodationType.APARTMENT,
            "price_per_night": 48.0,
            "rating": 8.1,
            "reviews_count": 420,
            "address": "Avenida Papa Luna 34, Benicarló",
            "booking_url": "https://www.booking.com/hotel/es/apartamentos-benicarlo-playa-3000.es.html",
            "image_url": "https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?w=500"
        }
    ],
    "Castellón de la Plana": [
        {
            "name": "NH Castellón Mindoro",
            "type": AccommodationType.HOTEL,
            "price_per_night": 79.0,
            "rating": 8.5,
            "reviews_count": 2450,
            "address": "Calle Moyano 4, Centro, Castellón",
            "booking_url": "https://www.booking.com/hotel/es/nhmindoro.es.html",
            "image_url": "https://images.unsplash.com/photo-1566073771259-6a8506099945?w=500"
        },
        {
            "name": "Hotel Civis Jaime I",
            "type": AccommodationType.HOTEL,
            "price_per_night": 62.0,
            "rating": 8.3,
            "reviews_count": 1820,
            "address": "Ronda Mijares 67, Castellón",
            "booking_url": "https://www.booking.com/hotel/es/jaimei.es.html",
            "image_url": "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?w=500"
        },
        {
            "name": "Hotel Castellón Center Affiliated by Meliá",
            "type": AccommodationType.HOTEL,
            "price_per_night": 74.0,
            "rating": 8.4,
            "reviews_count": 1650,
            "address": "Ronda Mijares 86-88, Castellón",
            "booking_url": "https://www.booking.com/hotel/es/hotel-castellon-center-affiliated-by-melia.es.html",
            "image_url": "https://images.unsplash.com/photo-1590490360182-c33d57733427?w=500"
        },
        {
            "name": "Hotel Luz Castellón",
            "type": AccommodationType.HOTEL,
            "price_per_night": 78.0,
            "rating": 8.6,
            "reviews_count": 2100,
            "address": "Pintor Oliet 3, Estación Renfe, Castellón",
            "booking_url": "https://www.booking.com/hotel/es/hotel-luz-castellon.es.html",
            "image_url": "https://images.unsplash.com/photo-1566073771259-6a8506099945?w=500"
        },
        {
            "name": "Apartamentos Castellón Centro Histórico (Airbnb)",
            "type": AccommodationType.APARTMENT,
            "price_per_night": 58.0,
            "rating": 9.1,
            "reviews_count": 280,
            "address": "Plaza Mayor 8, Castellón",
            "booking_url": "https://www.airbnb.es/s/Castellon-de-la-Plana/homes",
            "image_url": "https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?w=500"
        }
    ],
    "Sagunto": [
        {
            "name": "Exe Puerto de Sagunto",
            "type": AccommodationType.HOTEL,
            "price_per_night": 68.0,
            "rating": 8.4,
            "reviews_count": 1940,
            "address": "Avenida Ojos Negros 53, Puerto de Sagunto",
            "booking_url": "https://www.booking.com/hotel/es/exe-puerto-de-sagunto.es.html",
            "image_url": "https://images.unsplash.com/photo-1566073771259-6a8506099945?w=500"
        },
        {
            "name": "Hotel Domus Atilia",
            "type": AccommodationType.HOTEL,
            "price_per_night": 54.0,
            "rating": 8.5,
            "reviews_count": 820,
            "address": "Calle Periodista Azzati 18, Sagunto",
            "booking_url": "https://www.booking.com/hotel/es/domus-atilia.es.html",
            "image_url": "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?w=500"
        },
        {
            "name": "Apartamentos Sagunto Puerto & Playa (Airbnb)",
            "type": AccommodationType.APARTMENT,
            "price_per_night": 52.0,
            "rating": 9.0,
            "reviews_count": 310,
            "address": "Paseo Marítimo 15, Puerto de Sagunto",
            "booking_url": "https://www.airbnb.es/s/Sagunto/homes",
            "image_url": "https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?w=500"
        }
    ],
    "Gandía": [
        {
            "name": "Hotel RH Bayren Parc",
            "type": AccommodationType.HOTEL,
            "price_per_night": 74.0,
            "rating": 8.6,
            "reviews_count": 2180,
            "address": "Calle Mallorca 19, Playa de Gandía",
            "booking_url": "https://www.booking.com/hotel/es/rh-bayren-parc.es.html",
            "image_url": "https://images.unsplash.com/photo-1566073771259-6a8506099945?w=500"
        },
        {
            "name": "Hotel Safari",
            "type": AccommodationType.HOTEL,
            "price_per_night": 56.0,
            "rating": 8.2,
            "reviews_count": 1390,
            "address": "Calle Legazpi 17, Gandía",
            "booking_url": "https://www.booking.com/hotel/es/safari-gandia.es.html",
            "image_url": "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?w=500"
        },
        {
            "name": "Apartamentos Sol y Playa Gandía",
            "type": AccommodationType.APARTMENT,
            "price_per_night": 59.0,
            "rating": 8.5,
            "reviews_count": 480,
            "address": "Paseo Marítimo Neptuno 42, Playa de Gandía",
            "booking_url": "https://www.booking.com/hotel/es/apartamentos-sol-y-playa-gandia.es.html",
            "image_url": "https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?w=500"
        }
    ],
    "Xàtiva": [
        {
            "name": "Hotel Mont-Sant",
            "type": AccommodationType.HOTEL,
            "price_per_night": 95.0,
            "rating": 9.0,
            "reviews_count": 1150,
            "address": "Subida al Castillo s/n, Xàtiva",
            "booking_url": "https://www.booking.com/hotel/es/mont-sant.es.html",
            "image_url": "https://images.unsplash.com/photo-1566073771259-6a8506099945?w=500"
        },
        {
            "name": "Hotel Vernisa",
            "type": AccommodationType.HOTEL,
            "price_per_night": 52.0,
            "rating": 8.2,
            "reviews_count": 1420,
            "address": "Carrer d'Acàcies 5, Xàtiva",
            "booking_url": "https://www.booking.com/hotel/es/hotel-vernisa.es.html",
            "image_url": "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?w=500"
        },
        {
            "name": "Apartamento Boutique Muralla de Xàtiva (Airbnb)",
            "type": AccommodationType.APARTMENT,
            "price_per_night": 60.0,
            "rating": 9.2,
            "reviews_count": 270,
            "address": "Calle Corretgeria 12, Casco Histórico, Xàtiva",
            "booking_url": "https://www.airbnb.es/s/Xativa/homes",
            "image_url": "https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?w=500"
        }
    ],
    "Benicàssim": [
        {
            "name": "Hotel Voramar",
            "type": AccommodationType.HOTEL,
            "price_per_night": 88.0,
            "rating": 9.0,
            "reviews_count": 1780,
            "address": "Paseo Marítimo Pilar Coloma 1, Benicàssim",
            "booking_url": "https://www.booking.com/hotel/es/voramar.es.html",
            "image_url": "https://images.unsplash.com/photo-1566073771259-6a8506099945?w=500"
        },
        {
            "name": "Hotel Bersoca",
            "type": AccommodationType.HOTEL,
            "price_per_night": 58.0,
            "rating": 8.3,
            "reviews_count": 1240,
            "address": "Avenida Ferrandis Salvador 48, Benicàssim",
            "booking_url": "https://www.booking.com/hotel/es/bersoca.es.html",
            "image_url": "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?w=500"
        },
        {
            "name": "Palasiet Thalasso Clinic & Hotel",
            "type": AccommodationType.HOTEL,
            "price_per_night": 125.0,
            "rating": 8.8,
            "reviews_count": 1390,
            "address": "Calle Pontatge 6, Benicàssim",
            "booking_url": "https://www.booking.com/hotel/es/hotel-palasiet.es.html",
            "image_url": "https://images.unsplash.com/photo-1590490360182-c33d57733427?w=500"
        },
        {
            "name": "Apartamentos Voramar Costa Azahar (Airbnb)",
            "type": AccommodationType.APARTMENT,
            "price_per_night": 65.0,
            "rating": 9.2,
            "reviews_count": 290,
            "address": "Paseo Bernat Artola 20, Benicàssim",
            "booking_url": "https://www.airbnb.es/s/Benicassim/homes",
            "image_url": "https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?w=500"
        }
    ]
}



def calculate_price_for_dates(
    base_price: float,
    item_name: str,
    checkin: date,
    checkout: date
) -> Tuple[float, float, int]:
    """
    Computes realistic pricing for exact dates taking into account:
    - Nights count (checkout - checkin)
    - Seasonal calendar patterns in Spain (Summer peak, Spring, Winter)
    - Weekend pricing (Friday and Saturday nights)
    - Deterministic subtle property variation
    Returns: (average_price_per_night, total_price, nights_count)
    """
    if checkout <= checkin:
        checkout = checkin + timedelta(days=1)

    nights = max(1, (checkout - checkin).days)
    total_price = 0.0

    month_multipliers = {
        1: 0.85, 2: 0.85, 3: 0.95,
        4: 1.10, 5: 1.10, 6: 1.20,
        7: 1.35, 8: 1.40, 9: 1.15,
        10: 1.00, 11: 0.85, 12: 1.05
    }

    for i in range(nights):
        night_date = checkin + timedelta(days=i)
        season_factor = month_multipliers.get(night_date.month, 1.0)

        # Friday (4) and Saturday (5) nights have weekend peak demand
        weekday = night_date.weekday()
        if weekday in (4, 5):
            dow_factor = 1.22
        elif weekday == 6:
            dow_factor = 0.92
        else:
            dow_factor = 0.95

        # Micro variation per property and specific date
        h = int(hashlib.md5(f"{item_name}:{night_date.isoformat()}".encode("utf-8")).hexdigest()[:6], 16)
        variation = 0.96 + (h % 9) * 0.01  # range ~0.96 to ~1.04

        night_price = round(base_price * season_factor * dow_factor * variation, 0)
        total_price += night_price

    avg_price = round(total_price / nights, 0)
    return avg_price, total_price, nights


def _normalize_name(name: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", name.lower())
        if unicodedata.category(c) != "Mn"
    ).replace("-", " ").strip()


CITY_ALIASES: Dict[str, str] = {
    "castello": "Castellón de la Plana",
    "castello de la plana": "Castellón de la Plana",
    "sagunt": "Sagunto",
    "gandia": "Gandía",
    "xativa": "Xàtiva",
    "benicasim": "Benicàssim",
    "benicassim": "Benicàssim",
    "benicarlo peniscola": "Benicarló",
    "peniscola": "Benicarló",
    "coruna": "A Coruña",
    "santiago": "Santiago de Compostela",
    "vilagarcia": "Vilagarcía de Arousa",
    "avila": "Ávila",
    "cordoba": "Córdoba",
    "cadiz": "Cádiz",
}


class MockAccommodationProvider(AccommodationProvider):
    """
    Offline realistic accommodation provider.
    Serves curated high-quality hotel/apartment data for major towns and
    generates deterministic, consistent data for any other Spanish destination.
    """

    def search(
        self,
        destination_name: str,
        acc_type: AccommodationType = AccommodationType.BOTH,
        min_rating: Optional[float] = None,
        max_price: Optional[float] = None,
        checkin_date: Optional[date] = None,
        checkout_date: Optional[date] = None,
    ) -> List[Accommodation]:
        # Normalize city name
        clean_name = destination_name.split("-")[0].strip()
        norm_input = _normalize_name(clean_name)
        norm_full = _normalize_name(destination_name)

        target_curated_key = CITY_ALIASES.get(norm_input) or CITY_ALIASES.get(norm_full)

        # Find matching curated dataset or generate synthetic realistic items
        raw_items = []
        if target_curated_key and target_curated_key in CURATED_ACCOMMODATIONS:
            raw_items = CURATED_ACCOMMODATIONS[target_curated_key]
        else:
            for key, items in CURATED_ACCOMMODATIONS.items():
                norm_key = _normalize_name(key)
                if norm_key in norm_input or norm_input in norm_key or norm_key in norm_full:
                    raw_items = items
                    break

        if not raw_items:
            raw_items = self._generate_synthetic_items(clean_name)

        results: List[Accommodation] = []
        for idx, item in enumerate(raw_items):
            # Check type filter
            if acc_type != AccommodationType.BOTH and item["type"] != acc_type:
                continue

            base_price = float(item["price_per_night"])

            if checkin_date and checkout_date:
                price_per_night, total_price, nights_count = calculate_price_for_dates(
                    base_price=base_price,
                    item_name=item["name"],
                    checkin=checkin_date,
                    checkout=checkout_date,
                )
            else:
                price_per_night = base_price
                total_price = base_price
                nights_count = 1

            # Check price filter
            if max_price is not None and price_per_night > max_price:
                continue

            # Check rating filter
            if min_rating is not None and item["rating"] < min_rating:
                continue

            booking_url = item.get("booking_url")
            if not booking_url:
                quoted = urllib.parse.quote_plus(clean_name)
                booking_url = f"https://www.booking.com/searchresults.es.html?ss={quoted}"

            # Guard against invalid airbnb room slugs causing 404
            if "airbnb.es/rooms/" in booking_url:
                room_slug = booking_url.split("airbnb.es/rooms/")[-1].split("?")[0].strip("/")
                if not room_slug.isdigit():
                    city_slug = urllib.parse.quote(clean_name.replace(" ", "-"))
                    booking_url = f"https://www.airbnb.es/s/{city_slug}/homes"

            if checkin_date and checkout_date:
                cin = checkin_date.isoformat()
                cout = checkout_date.isoformat()
                sep = "&" if "?" in booking_url else "?"
                if "booking.com" in booking_url:
                    booking_url = f"{booking_url}{sep}checkin={cin}&checkout={cout}&group_adults=2&no_rooms=1"
                else:
                    booking_url = f"{booking_url}{sep}checkin={cin}&checkout={cout}"

            acc_id = f"acc_{clean_name[:4].lower()}_{idx}_{hashlib.md5(item['name'].encode()).hexdigest()[:6]}"
            results.append(
                Accommodation(
                    id=acc_id,
                    name=item["name"],
                    destination_city=clean_name,
                    type=item["type"],
                    price_per_night=price_per_night,
                    currency="EUR",
                    rating=float(item["rating"]),
                    reviews_count=int(item["reviews_count"]),
                    address=item.get("address", f"Centro de {clean_name}"),
                    booking_url=booking_url,
                    image_url=item.get("image_url", "https://images.unsplash.com/photo-1566073771259-6a8506099945?w=500"),
                    checkin_date=checkin_date,
                    checkout_date=checkout_date,
                    nights_count=nights_count,
                    total_price=total_price,
                )
            )

        return results

    def _generate_synthetic_items(self, city: str) -> List[Dict]:
        """Generates deterministic realistic hotels and apartments using city hash as seed."""
        seed_val = int(hashlib.md5(city.encode("utf-8")).hexdigest()[:8], 16)
        rng = random.Random(seed_val)
        quoted_city = urllib.parse.quote_plus(city)

        hotel_names = [
            f"Gran Hotel {city} Spa & Boutique",
            f"Hotel Histórico Plaza Mayor de {city}",
            f"Parador Real de {city}",
            f"Hotel Boutique {city} Centro"
        ]
        apartment_names = [
            f"Apartamentos Con Encanto {city} Old Town",
            f"Ático Panorámico {city} Catedral",
            f"Loft Moderno Centro Histórico {city}",
            f"Suites Urbanas {city} Alameda"
        ]

        items = []
        for name in hotel_names:
            price = round(rng.uniform(65.0, 160.0), 0)
            rating = round(rng.uniform(8.1, 9.5), 1)
            reviews = rng.randint(180, 2200)
            items.append({
                "name": name,
                "type": AccommodationType.HOTEL,
                "price_per_night": price,
                "rating": rating,
                "reviews_count": reviews,
                "address": f"Calle Principal {rng.randint(1, 40)}, {city}",
                "booking_url": f"https://www.booking.com/searchresults.es.html?ss={quoted_city}",
                "image_url": "https://images.unsplash.com/photo-1566073771259-6a8506099945?w=500"
            })

        for name in apartment_names:
            price = round(rng.uniform(55.0, 130.0), 0)
            rating = round(rng.uniform(8.4, 9.7), 1)
            reviews = rng.randint(90, 850)
            items.append({
                "name": name,
                "type": AccommodationType.APARTMENT,
                "price_per_night": price,
                "rating": rating,
                "reviews_count": reviews,
                "address": f"Plaza de la Constitución {rng.randint(1, 20)}, {city}",
                "booking_url": f"https://www.airbnb.es/s/{urllib.parse.quote(city)}/homes",
                "image_url": "https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?w=500"
            })

        return items

