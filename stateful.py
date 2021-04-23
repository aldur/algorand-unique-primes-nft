#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
App will check that `C_p` was not already opt-in.

If not, it will store in the local storage of `C_p` two variables:
`p` <- `p` and `creator` <- `Alice`
"""

__author__ = "Adriano Di Luzio <adriano@algorand.com>"

from pyteal import (
    Btoi,
    Seq,
    Return,
    Int,
    OnComplete,
    Txn,
    Gtxn,
    Cond,
    compileTeal,
    Mode,
    App,
    Assert,
    Bytes,
    And,
    TxnType,
    Global,
)

# First:
# Atomic Transfer Group
#
# 0. Alice sends 1 Algo to C_p
# 1. C_p opts-in to App
# 2. C_p creates the NFT
#
# Second:
# Alice opts-in to the NFT.
#
# Third:
# Atomic Transfer Group
# 0. C_p calls App.
# 1. C_p sends the NFT to Alice

AMOUNT = int(10 ** 6)  # 1 Algo
CREATOR_KEY = "creator"
PRIME_KEY = "p"


def handle_optin():
    precondition = And(
        Global.group_size() == Int(3),
        Gtxn[0].type_enum() == TxnType.Payment,
        Gtxn[0].amount() == Int(AMOUNT),
        Gtxn[0].receiver() == Gtxn[1].sender(),
        Gtxn[1].type_enum() == TxnType.ApplicationCall,
        Gtxn[1].application_args.length() == Int(1),
        Gtxn[1].sender() == Gtxn[2].sender(),
        Gtxn[2].type_enum() == TxnType.AssetConfig,
        Gtxn[0].rekey_to() == Global.zero_address(),
        Gtxn[1].rekey_to() == Global.zero_address(),
        Gtxn[2].rekey_to() == Global.zero_address(),
    )

    # TODO: Verify that `p` gets only passed from the correct `C_p`.
    # To do this, let's assume that the assembly of `C_p` has a shape as follows:
    # `Program` || prefix || p || suffix
    # 1. We will hard-code prefix and suffix within this contract.
    # 2. We will concatenate prefix, p, and suffix.
    # 3. We will perform SHA512_256 hash of the concatenation.
    # 4. Compare the result with Gtxn[1].sender().

    # NOTE: I originally wanted to check that the user did not opt-in before.
    # This is not required as the protocol enforces that users can opt-in only
    # once.
    # has_not_opted_in = Not(App.optedIn(Int(0), Global.current_application_id()))

    # TODO: This has to be changed to Go's binary encoding format for
    # integers and then stored as bytes.
    p = Btoi(Txn.application_args[0])
    creator = Gtxn[0].sender()

    return Seq(
        [
            Assert(precondition),
            App.localPut(Int(0), Bytes(PRIME_KEY), p),
            App.localPut(Int(0), Bytes(CREATOR_KEY), creator),
            Return(Int(1)),
        ]
    )


def handle_call():
    precondition = And(
        Global.group_size() == Int(2),
        # NOTE: This is redundant as it is checked below.
        # Gtxn[0].type_enum() == TxnType.ApplicationCall,
        # Gtxn[0].on_completion() == OnComplete.OptIn,
        # Gtxn[0].application_id() == Int(0),
        # Check that the second transaction tansfers to Alice.
        Gtxn[1].type_enum() == TxnType.AssetTransfer,
        App.localGet(Int(0), Bytes(CREATOR_KEY)) == Gtxn[1].asset_receiver(),
        # TODO: Add checks on asset being transferred.
        Gtxn[0].rekey_to() == Global.zero_address(),
        Gtxn[1].rekey_to() == Global.zero_address(),
    )

    sequence = Seq(
        [
            Assert(precondition),
            App.localDel(Int(0), Bytes(CREATOR_KEY)),
            Return(Int(1)),
        ]
    )

    return Cond(
        [Global.group_size() == Int(1), Return(Int(1))],
        [Global.group_size() == Int(2), sequence],
    )


def approval_program():
    # handle_call_ = Seq([Return(Int(1))])
    handle_closeout = Seq([Return(Int(1))])

    # Err() would cause an immediate panic, so we just return 0.
    handle_updateapp = Seq([Return(Int(0))])
    handle_deleteapp = Seq([Return(Int(0))])

    return Cond(
        [Txn.on_completion() == OnComplete.NoOp, handle_call()],
        [Txn.on_completion() == OnComplete.OptIn, handle_optin()],
        [Txn.on_completion() == OnComplete.CloseOut, handle_closeout],
        [Txn.on_completion() == OnComplete.UpdateApplication, handle_updateapp],
        [Txn.on_completion() == OnComplete.DeleteApplication, handle_deleteapp],
    )


def main():
    import os.path

    fn = os.path.splitext(os.path.basename(__file__))[0]
    with open(f"{fn}_compiled.teal", "w") as f:
        compiled = compileTeal(approval_program(), Mode.Application)
        f.write(compiled)


if __name__ == "__main__":
    main()
