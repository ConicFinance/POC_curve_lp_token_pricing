from decimal import Decimal

from tests.constants import USD_ADDRESS


def downscale(value, decimals: int = 18):
    return Decimal(value) / Decimal(10**decimals)


def upscale(value, decimals: int = 18):
    return Decimal(value) * Decimal(10**decimals)


def get_price_usd(chainlink_feed_registry, asset: str):
    decimals = chainlink_feed_registry.functions.decimals(asset, USD_ADDRESS).call()
    _, answer, _, _, _ = chainlink_feed_registry.functions.latestRoundData(
        asset, USD_ADDRESS
    ).call()
    return downscale(answer, decimals)
