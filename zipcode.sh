#!/bin/bash

mkdir -p build/functions build/layers

for dir in src/functions/*
do
    function=$(basename $dir)
    zip -j "build/functions/$function.zip" src/functions/$function/*
done

for dir in src/layers/*
do
    layer=$(basename $dir)

    rm -rf .tmp
    mkdir -p .tmp/python
    cp $dir/* .tmp/python
    
    cd .tmp
    zip $layer.zip python/*
    cd ..
    mv .tmp/$layer.zip build/layers
    rm -rf .tmp
done