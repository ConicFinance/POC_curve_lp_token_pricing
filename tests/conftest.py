import os

import pytest
from web3 import HTTPProvider, Web3

from tests.constants import ABIS, ADDRESSES


@pytest.fixture(scope="session")
def web3():
    return Web3(HTTPProvider(os.environ["WEB3_PROVIDER_URI"]))


@pytest.fixture(scope="session")
def chainlink_feed_registry(web3):
    return web3.eth.contract(
        address=ADDRESSES["chainlink_feed_registry"],
        abi=ABIS["chainlink_feed_registry"],
    )
