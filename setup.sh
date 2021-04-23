#!/usr/bin/env bash

# shellcheck disable=SC2016
if test "$BASH" = "" || "$BASH" -uc 'a=();true "${a[@]}"' 2>/dev/null; then
    # Bash 4.4, Zsh
    set -Eeuo pipefail
else
    # Bash 4.3 and older chokes on empty arrays with set -u.
    set -Eeo pipefail
fi
if shopt | grep globstar; then
    shopt -s nullglob globstar || true
fi

trap cleanup SIGINT SIGTERM ERR EXIT

cleanup() {
    trap - SIGINT SIGTERM ERR EXIT
}

# NOTE: Modify this to suite your PATH.
# NOTE: If you are not using the `sandbox`, you'll have to remove all `sandbox`
# invocations below and directly call `goal.`
SANDBOX_PATH=/Users/adriano/Work/sandbox

# NOTE: Fund this address with a few Algos.
ADDR_CREATOR="HDPT6HKL5JGEK5KKS35U746VYIZWYJVF5ECUQQINEF6NEURMX3EIFARD2A"

# NOTE: This is the `PRIME` you'll make an NFT of.
PRIME=17

PATH=$SANDBOX_PATH:$PATH

TEAL_APPROVAL_PROG="stateful_compiled.teal"
TEAL_CLEAR_PROG="clear_state_program.teal"
STATELESS_PROG="stateless_compiled.teal"

GLOBAL_BYTESLICES=0
GLOBAL_INTS=0
LOCAL_BYTESLICES=1
LOCAL_INTS=1

set -x

pipenv run python stateful.py
sed -i '' 's/version 2/version 3/g' $TEAL_APPROVAL_PROG
sed -i '' 's/version 2/version 3/g' $TEAL_CLEAR_PROG

sandbox copy $TEAL_APPROVAL_PROG
sandbox copy $TEAL_CLEAR_PROG
sandbox goal app create \
    --creator $ADDR_CREATOR \
    --approval-prog $TEAL_APPROVAL_PROG \
    --clear-prog $TEAL_CLEAR_PROG \
    --global-byteslices $GLOBAL_BYTESLICES \
    --global-ints $GLOBAL_INTS \
    --local-byteslices $LOCAL_BYTESLICES \
    --local-ints $LOCAL_INTS

# This fancy line extracts the higher application ID for the account.
APPLICATION_ID=$(sandbox goal account dump --address $ADDR_CREATOR | jq -c '.appp | [keys[] | tonumber] | max' | xargs)
echo "Application ID: $APPLICATION_ID"

STATELESS_ADDR=$(pipenv run python stateless.py "$APPLICATION_ID" "$PRIME" && goal clerk compile $STATELESS_PROG | cut -d " " -f 2)
echo "Stateless address is: ${STATELESS_ADDR}"
# sed -i '' 's/version 2/version 3/g' $STATELESS_PROG
sandbox copy $STATELESS_PROG

sandbox goal clerk send \
    --from=$ADDR_CREATOR \
    --to="$STATELESS_ADDR" \
    --fee=1000 \
    --amount=1000000 \
    --out=0.txn

sandbox goal app optin \
    --app-id="${APPLICATION_ID}" \
    --from="$STATELESS_ADDR" \
    --fee=1000 \
    --app-arg=int:$PRIME \
    --out=1.txn

# By default this sets also manager, reserve, freeze and clawback to $STATELESS_ADDR.
sandbox goal asset create \
    --creator "$STATELESS_ADDR" \
    --total 1 \
    --unitname $PRIME \
    --decimals 0 \
    --fee=1000 \
    --out=2.txn

docker-compose -f ~/Work/sandbox/docker-compose.yml exec algod /bin/sh -c "cat 0.txn 1.txn 2.txn > combined.txn"

sandbox goal clerk group \
    -i combined.txn \
    -o grouped.txn

sandbox goal clerk split \
    -i grouped.txn \
    -o split_txns

sandbox goal clerk sign \
    -i split_txns-0 \
    -o 0.txn.sig

sandbox goal clerk sign \
    -p $STATELESS_PROG \
    -i split_txns-1 \
    -o 1.txn.sig

sandbox goal clerk sign \
    -p $STATELESS_PROG \
    -i split_txns-2 \
    -o 2.txn.sig

docker-compose -f ~/Work/sandbox/docker-compose.yml exec algod /bin/sh -c "cat 0.txn.sig 1.txn.sig 2.txn.sig > combined.txn.sig"

# sandbox goal clerk dryrun -t combined.txn.sig --dryrun-dump -o dr.msgp
# sandbox tealdbg --listen 0.0.0.0 debug $TEAL_APPROVAL_PROG -d dr.msgp --group-index 0

sandbox goal clerk rawsend -f combined.txn.sig

ASSET_ID=$(sandbox goal asset info --unitname $PRIME --creator "$STATELESS_ADDR" | grep "Asset ID:" | tr -s ' ' | cut -d ' ' -f 3 | tr -d '\r')

sandbox goal asset send \
    -a 0 \
    --assetid "$ASSET_ID" \
    -f "$ADDR_CREATOR" \
    -t "$ADDR_CREATOR"

sandbox goal app call \
    --app-id="${APPLICATION_ID}" \
    --from="$STATELESS_ADDR" \
    --fee=1000 \
    --out=0.txn

sandbox goal asset send \
    -a 1 \
    --assetid "$ASSET_ID" \
    -f "$STATELESS_ADDR" \
    -t "$ADDR_CREATOR" \
    --fee=1000 \
    --out=1.txn

docker-compose -f ~/Work/sandbox/docker-compose.yml exec algod /bin/sh -c "cat 0.txn 1.txn > combined.txn"

sandbox goal clerk group \
    -i combined.txn \
    -o grouped.txn

sandbox goal clerk split \
    -i grouped.txn \
    -o split_txns

sandbox goal clerk sign \
    -p $STATELESS_PROG \
    -i split_txns-0 \
    -o 0.txn.sig

sandbox goal clerk sign \
    -p $STATELESS_PROG \
    -i split_txns-1 \
    -o 1.txn.sig

docker-compose -f ~/Work/sandbox/docker-compose.yml exec algod /bin/sh -c "rm combined.txn.sig*; cat 0.txn.sig 1.txn.sig > combined.txn.sig"

sandbox goal clerk dryrun -t combined.txn.sig --dryrun-dump -o dr.msgp
sandbox tealdbg --listen 0.0.0.0 debug $TEAL_APPROVAL_PROG -d dr.msgp --group-index 0

sandbox goal clerk rawsend -f combined.txn.sig
