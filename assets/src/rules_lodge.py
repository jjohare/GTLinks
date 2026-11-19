"""Validation rules for the lodge v2 set (schema as PROP_RULES in validate.py)."""
RULES = {
    'lodge': {'nodes': ['lodge', 'lodge_building', 'lodge_roof', 'lodge_balcony', 'lodge_terrace', 'lodge_railings', 'lodge_furniture',
                        'lodge_flowers', 'lodge_woodpile', 'lodge_skirack', 'lodge_sign', 'lodge_lanterns', 'chairlift_pylon',
                        'chairlift_cable', 'chairlift_station', 'chairlift_chairs', 'chair_a', 'chair_b'],
              'mats': [], 'tris': 40000},
    'chairlift_pylon': {'nodes': ['chairlift_pylon'], 'mats': [], 'tris': 6000, 'base0': True, 'h': (10.5, 11.6)},
    'chair': {'nodes': ['chair'], 'mats': [], 'tris': 2500},
}
