#!/bin/bash

(cd ~/autojournal; nohup poetry run gcal_aggregator --update all &> ~/autojournal.log &)
