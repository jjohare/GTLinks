"""Validation rules for helicopter.py (schema = validate.PROP_RULES)."""
RULES = {
    'helicopter': {'nodes': ['heli', 'fuselage', 'rotor_main', 'rotor_tail', 'spotlight', 'skids', 'nav_red', 'nav_green', 'strobe'],
                   'mats': ['spot_lens', 'glass'], 'tris': 10500},
}
