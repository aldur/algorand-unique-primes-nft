#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
`C_p` will:

- Have `p` hardcoded as a constant;
- Require any transaction from `C_p` to be in a group of transactions with a
  call to App.
"""

__author__ = "Adriano Di Luzio <adriano@algorand.com>"

import sys

from pyteal import (
    Cond,
    Int,
    Gtxn,
    compileTeal,
    Mode,
    OnComplete,
    And,
    TxnType,
    Global,
)

MAX_FEE = Int(1000)


def opt_in(application_id, p):
    return And(
        Int(int(p)),  # This is the constant representing the `p`

        Global.group_size() == Int(3),
        Gtxn[0].type_enum() == TxnType.Payment,
        Gtxn[0].receiver() == Gtxn[1].sender(),

        Gtxn[1].type_enum() == TxnType.ApplicationCall,
        Gtxn[1].on_completion() == OnComplete.OptIn,
        Gtxn[1].application_id() == Int(int(application_id)),
        Gtxn[1].application_args.length() == Int(1),
        Gtxn[1].sender() == Gtxn[2].sender(),
        Gtxn[1].fee() <= MAX_FEE,

        Gtxn[2].type_enum() == TxnType.AssetConfig,
        Gtxn[2].config_asset_total() == Int(1),
        Gtxn[2].config_asset_decimals() == Int(0),
        Gtxn[2].fee() <= MAX_FEE,
        # TODO: Add checks on asset type and configuration.
        # - Ensure that the creator, manager, reserve, freeze and clawback
        # addresses point here.
        # - Ensure that total supply is 1 and decimals are 0.
        # - [Optional]: Ensure a name / metadata hash.

        Gtxn[0].rekey_to() == Global.zero_address(),
        Gtxn[1].rekey_to() == Global.zero_address(),
        Gtxn[2].rekey_to() == Global.zero_address(),
    )


def call(application_id):
    return And(
        Global.group_size() == Int(2),

        Gtxn[0].type_enum() == TxnType.ApplicationCall,
        Gtxn[0].application_id() == Int(int(application_id)),
        Gtxn[0].fee() <= MAX_FEE,

        Gtxn[1].type_enum() == TxnType.AssetTransfer,
        Gtxn[1].fee() <= MAX_FEE,
        # TODO: Add checks on asset type and configuration.

        Gtxn[0].rekey_to() == Global.zero_address(),
        Gtxn[1].rekey_to() == Global.zero_address(),
    )


def stateless_p(application_id, p):
    return Cond(
        [Global.group_size() == Int(2), call(application_id)],
        [Global.group_size() == Int(3), opt_in(application_id, p)]
    )


def main():
    import os.path
    assert len(sys.argv) >= 2, "You need to provide `app_id` and `p`."

    fn = os.path.splitext(os.path.basename(__file__))[0]
    with open(f"{fn}_compiled.teal", "w") as f:
        compiled = compileTeal(stateless_p(sys.argv[1], sys.argv[2]), Mode.Signature)
        f.write(compiled)


if __name__ == "__main__":
    main()
