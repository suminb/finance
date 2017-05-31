#!/bin/bash

TARGET_REPO="git@github.com:suminb/finance-web.git"
BUILD_DIR=dist
LAST_COMMIT_MESSAGE=$(git log -1 --pretty=%B)

rm -rf $BUILD_DIR
ng build
pushd $BUILD_DIR
git init
git remote add origin $TARGET_REPO
git add .
git commit -m "$LAST_COMMIT_MESSAGE"
git push -f origin master
popd

