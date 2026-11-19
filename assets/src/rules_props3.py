"""Validation rules for props3.py (new props) and the budgets of the upgraded props in props.py.

Schema = validate.PROP_RULES; validate.load_extra_rules() merges RULES over the defaults.
"""
RULES = {
    # ---- new props (root node named after the file)
    'golfer': dict(nodes=['golfer'], mats=['shirt', 'skin', 'trousers', 'cap', 'shoes', 'glove', 'shaft', 'head', 'grip'],
                   tris=600, base0=True, h=(1.6, 1.9)),
    'golf_bag': dict(nodes=['golf_bag'], mats=['bag_body', 'bag_hood', 'shaft', 'head'], tris=3000, base0=True,
                     h=(0.9, 1.3)),
    'golf_club': dict(nodes=['golf_club'], mats=['shaft', 'head', 'grip'], tris=600, h=(1.0, 1.2)),
    'cow': dict(nodes=['cow'], mats=['hide', 'patch', 'bell', 'horn', 'hoof', 'leather'], tris=3000, base0=True, h=(1.2, 1.6)),
    'tree_larch': dict(nodes=['tree_larch'], mats=['bark', 'needles'], tris=800, base0=True, h=(8.5, 9.5)),
    # ---- upgraded props: new budgets and sanity heights
    'stein': dict(nodes=['stein'], mats=['lager', 'foam'], tris=2000, h=(0.18, 0.22), base0=True),
    'table': dict(nodes=['table'], mats=[], tris=3000, base0=True),
    'tree_pine': dict(nodes=['tree_pine'], mats=['bark', 'needles'], tris=800, base0=True, h=(8.0, 8.8)),
    'tree_broadleaf': dict(nodes=['tree_broadleaf'], mats=['bark', 'leaves'], tris=800, base0=True, h=(6.5, 7.5)),
    'spectator': dict(nodes=['spectator'], mats=['shirt'], tris=600, base0=True, h=(1.7, 1.9)),
    'flag': dict(nodes=['flag'], mats=['pole', 'flag'], tris=800, h=(2.1, 2.4), base0=True),
    'tee_marker': dict(nodes=['tee_marker'], mats=['marker', 'peg'], tris=900),
    'golf_cart': dict(nodes=['golf_cart'], mats=['cart_body', 'cart_trim', 'seat', 'glass', 'tyre', 'rim'], tris=5000, base0=True),
    'sign': dict(nodes=['sign'], mats=[], tris=1500, base0=True),
    'rock': dict(nodes=['rock'], mats=['rock'], tris=1500, base0=True),
    'drone': dict(nodes=['drone', 'rotor_fl', 'rotor_fr', 'rotor_rl', 'rotor_rr'], mats=['rotor'], tris=2500),
}
