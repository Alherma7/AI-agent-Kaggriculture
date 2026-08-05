"""Single source of truth for game constants.

Re-exported directly from the installed `kaggle_environments` package
(confirmed present in kaggle-environments' kaggriculture module — no need to
hand-transcribe the README tables, which can drift from the actual engine).
Strategy code should import constants from here, not from
`kaggle_environments` directly, so there is one place to update if the
import path ever changes.
"""

from kaggle_environments.envs.kaggriculture.kaggriculture import (
    ANIMALS,
    CROPS,
    FARM_HAND_COST_MULT,
    LAND_PRICES,
    MARKET_I0,
    MARKET_PARAMS,
    PRICE_FLOOR,
    PRODUCTS,
    SHOPS,
    TOWN_CENTER_DEMAND_SCHEDULE,
)

RANDOM_STATE = 0
