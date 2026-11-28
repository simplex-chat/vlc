#!/bin/bash

set -euo pipefail

repo=$1
run=$2
attempt=$3

read -r workflow branch event < <(gh api "repos/$repo/actions/runs/$run" --jq '"\(.workflow_id) \(.head_branch) \(.event)"')
latest=$(gh api "repos/$repo/actions/workflows/$workflow/runs?branch=$branch&event=$event&per_page=1" --jq '.workflow_runs[0].id')
if [ "$latest" != "$run" ]; then
  echo "run $run: $branch has the newer run $latest"
  exit 0
fi

unacquired=0
while read -r job runner; do
  if [ "$runner" != 0 ]; then
    echo "run $run: job $job ran on runner $runner"
    exit 0
  fi
  if gh api "repos/$repo/check-runs/$job/annotations" --jq '.[].message' | grep -qF 'was not acquired by Runner'; then
    unacquired=$((unacquired + 1))
  fi
done < <(gh api "repos/$repo/actions/runs/$run/attempts/$attempt/jobs?per_page=100" \
  --jq '.jobs[] | select(.conclusion == "failure" or .conclusion == "cancelled") | "\(.id) \(.runner_id // 0)"')

if [ "$unacquired" = 0 ]; then
  echo "run $run: no job is marked as not acquired by a runner"
  exit 0
fi
echo "run $run: $unacquired of its jobs got no runner"
echo "unacquired=true" >> "$GITHUB_OUTPUT"
