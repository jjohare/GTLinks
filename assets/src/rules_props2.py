"""Validation rules for props2.py (schema: PROP_RULES in validate.py)."""
RULES = {
    'grandstand': dict(nodes=['grandstand'], mats=['steel_frame', 'seat_slat', 'seat_red', 'seat_blue', 'seat_yellow', 'canopy_a', 'canopy_b', 'deck_timber'],
                       tris=13000, base0=True, h=(4.8, 7.6)),
    'leaderboard': dict(nodes=['leaderboard'], mats=['panel_title', 'panel_1', 'panel_2', 'panel_3', 'panel_4', 'panel_5', 'panel_6', 'frame_dark', 'lamp_glow'],
                        tris=3000, base0=True, h=(2.9, 3.2)),
    'bench': dict(nodes=['bench'], mats=['cast_iron', 'bench_slat'], tris=3000, base0=True, h=(0.8, 0.98)),
    'sprinkler': dict(nodes=['sprinkler'], mats=['turf_cap', 'nozzle_brass', 'riser_steel'], tris=1500, base0=True, h=(0.27, 0.33)),
    'yardage_post': dict(nodes=['yardage_post'], mats=['marker', 'plate', 'post_paint'], tris=600, base0=True, h=(0.85, 0.95)),
    'ob_stake': dict(nodes=['ob_stake'], mats=['stake_white', 'stake_band'], tris=500, base0=True, h=(1.15, 1.25)),
    'ball_washer': dict(nodes=['ball_washer'], mats=['washer_green', 'plate', 'chrome'], tris=2000, base0=True, h=(1.05, 1.15)),
    'halfway_hut': dict(nodes=['halfway_hut'], mats=['log_a', 'shingle_a', 'stone_a', 'awning_a', 'sign_board', 'lantern_glow'], tris=12000, base0=True),
    'bunker_rake': dict(nodes=['bunker_rake'], mats=['rake_handle', 'tine_steel'], tris=800, base0=True),
    'parasol': dict(nodes=['parasol'], mats=['parasol_a', 'parasol_b', 'pole_steel'], tris=3000, base0=True, h=(2.4, 2.6)),
    'footbridge': dict(nodes=['footbridge'], mats=['plank', 'rail_wood', 'post_wood'], tris=1600),
}
