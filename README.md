# Curve LP Token Pricing POC

This repository contains a simple POC for the Conic LP token pricing methodology implemented in Python.
Note that this implementation works for the pools using StableSwap version 2.8.

The proposed method relies on two main components:

## Oracle Prices for the Assets in a Curve Pool

Since exchange rates (i.e. prices for the assets in a Curve pool) are not resistant to manipulation, we make use of oracles to obtain prices for the two assets in a Curve pool.

## Invariant Based Estimation of Assets in the Curve Pool

Using the Curve invariant $D$ and the oracle price of asset $A$ in the pool, we can calculate the amount of asset $A$ currently deposited in the pool using Newton's method (see: <code>calc_x_from_D(...)</code>).
Then, we can use the amount of asset $A$ just obtained and the invariant of the pool to calculate the amount of asset $B$ deposited in the pool, using the same method implemented in the Curve pool (see: <code>calc_y_from_x_crv(...)</code>).

Lastly, we compute the value of the pool's LP token using the previously obtained asset amounts and oracle prices to arrive at a manipulation resistant Lp token price.

The full functionality is explained in the Conic Whitepaper, which can be found here: https://ipfs.conic.finance/whitepaper.pdf

# Running the Tests

To run the tests, install the required packages (requirements.txt) and set you environment variable **WEB3_PROVIDER_URI** to a working infura link.
Then, run the test by running <code>pytest</code>.
