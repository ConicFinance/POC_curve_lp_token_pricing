from decimal import Decimal

from hypothesis import given, strategies as st
import pytest
from eth_typing.encoding import HexStr
from eth_typing.evm import ChecksumAddress, HexAddress
from web3 import Web3

from conic.curve_token_pricing.token_pricing import (
    calc_x_from_D,
    calc_y_from_x_crv,
    get_v1_lp_token_price,
)
from conic.curve_pool_v1 import CurvePool


from tests.constants import CURVE_ABIS, POOLS
from tests.utils import downscale, get_price_usd, upscale

ETH_ADDRESS = "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE"


def address_from_str(raw_address: str) -> ChecksumAddress:
    return ChecksumAddress(HexAddress(HexStr(raw_address)))


def get_decimals(token_address: str, web3: Web3) -> int:
    if token_address == ETH_ADDRESS:
        return 18
    return (
        web3.eth.contract(
            abi=CURVE_ABIS["lp_token"], address=address_from_str(token_address)
        )
        .functions.decimals()
        .call()
    )


def get_pool_and_token(name: str, web3: Web3):
    pool_address = address_from_str(POOLS[name]["pool"])
    lp_token_address = address_from_str(POOLS[name]["lp_token"])
    pool = web3.eth.contract(abi=CURVE_ABIS["pool"], address=pool_address)
    lp_token = web3.eth.contract(abi=CURVE_ABIS["lp_token"], address=lp_token_address)
    return pool, lp_token


def get_D(pool, lp_token):
    virtual_price = downscale(pool.functions.get_virtual_price().call())
    total_supply = downscale(lp_token.functions.totalSupply().call())
    return virtual_price * total_supply


@pytest.mark.parametrize("pool", list(POOLS))
def test_calc_y_from_x_crv(web3, pool):
    pool, lp_token = get_pool_and_token(pool, web3)

    A = Decimal(pool.functions.A_precise().call())
    D = get_D(pool, lp_token)

    decimals_a = get_decimals(pool.functions.coins(0).call(), web3)
    decimals_b = get_decimals(pool.functions.coins(1).call(), web3)

    amount_asset_a = downscale(pool.functions.balances(0).call(), decimals_a)
    expected_amount_asset_b = downscale(pool.functions.balances(1).call(), decimals_b)
    amount_asset_b = calc_y_from_x_crv(amount_asset_a, A, D)

    assert amount_asset_b == pytest.approx(expected_amount_asset_b)


# NOTE: no chainlink price for crvCVX
@pytest.mark.parametrize("pool", ["steth"])
def test_calc_y_from_D(web3, chainlink_feed_registry, pool):
    print(pool)
    pool, lp_token = get_pool_and_token(pool, web3)

    A = Decimal(pool.functions.A_precise().call())
    D = get_D(pool, lp_token)

    token_a = pool.functions.coins(0).call()
    token_b = pool.functions.coins(1).call()

    price_token_a = get_price_usd(chainlink_feed_registry, token_a)
    price_token_b = get_price_usd(chainlink_feed_registry, token_b)
    print(price_token_a, price_token_b)
    price = price_token_a / price_token_b
    curve_price = pool.functions.get_dy(0, 1, 10**18).call() / Decimal(10**18)
    print("curve price", curve_price * 10**12)
    print("our price", price)

    expected_amount_asset_a = downscale(pool.functions.balances(0).call())
    amount_token_a = calc_x_from_D(D, A, curve_price)
    assert amount_token_a == pytest.approx(expected_amount_asset_a, rel=Decimal("0.05"))


@given(
    x=st.integers(min_value=1_000, max_value=10_000_000),
    y=st.integers(min_value=1_000, max_value=10_000_000),
)
def test_calc_y_from_D_fuzz(x, y):
    curve_pool = CurvePool(100)

    curve_pool.add_liquidity([int(upscale(x)), int(upscale(y))], 0)

    D = curve_pool.get_D_direct() / Decimal(10**18)

    curve_price = curve_pool.get_dy(0, 1, 10**18) / Decimal(10**18)

    amount_token_a_computed = calc_x_from_D(D, Decimal(curve_pool.A), curve_price)
    assert amount_token_a_computed == pytest.approx(x, abs=1)


@given(
    x=st.integers(min_value=1_000, max_value=10_000_000),
    y=st.integers(min_value=1_000, max_value=10_000_000),
)
def test_calc_token_price_fuzz(x, y):
    curve_pool = CurvePool(100)

    curve_pool.add_liquidity([int(upscale(x)), int(upscale(y))], 0)

    total_token_supply = Decimal(curve_pool.token_supply) / Decimal(10**18)

    D = curve_pool.get_D_direct() / Decimal(10**18)

    curve_price_a = curve_pool.get_dy(0, 1, 10**18) / Decimal(10**18)
    curve_price_b = curve_pool.get_dy(1, 0, 10**18) / Decimal(10**18)

    lp_token_price = get_v1_lp_token_price(
        D, total_token_supply, Decimal(curve_pool.A), curve_price_a, curve_price_b
    )

    balances = curve_pool._xp()
    balance_asset_a = balances[0] / Decimal(10**18)
    balance_asset_b = balances[1] / Decimal(10**18)
    lp_token_price_expected = (
        curve_price_a * balance_asset_a + curve_price_b * balance_asset_b
    ) / total_token_supply

    assert lp_token_price == pytest.approx(lp_token_price_expected, rel=Decimal("0.01"))


# NOTE: no chainlink price for crvCVX
@pytest.mark.parametrize("pool", ["steth"])
def test_calc_lp_token_price(web3, chainlink_feed_registry, pool):
    print(pool)
    pool, lp_token = get_pool_and_token(pool, web3)

    A = Decimal(pool.functions.A_precise().call())
    D = get_D(pool, lp_token)
    token_supply = downscale(lp_token.functions.totalSupply().call())

    token_a = pool.functions.coins(0).call()
    token_b = pool.functions.coins(1).call()

    price_token_a = get_price_usd(chainlink_feed_registry, token_a)
    price_token_b = get_price_usd(chainlink_feed_registry, token_b)
    print(price_token_a, price_token_b)
    price_a = price_token_a / price_token_b
    price_b = price_token_b / price_token_a
    curve_price_a = pool.functions.get_dy(0, 1, 10**18).call() / Decimal(10**18)
    curve_price_b = pool.functions.get_dy(1, 0, 10**18).call() / Decimal(10**18)
    print("curve price_a", curve_price_a * 10**12)
    print("curve price_b", curve_price_b * 10**12)

    expected_amount_asset_a = downscale(pool.functions.balances(0).call())
    expected_amount_asset_b = downscale(pool.functions.balances(1).call())

    lp_token_price = get_v1_lp_token_price(D, token_supply, A, price_a, price_b)
    lp_token_price_expected = (
        curve_price_a * expected_amount_asset_a
        + curve_price_b * expected_amount_asset_b
    ) / token_supply

    assert lp_token_price == pytest.approx(lp_token_price_expected, rel=Decimal("0.03"))
