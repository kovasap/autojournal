#!/bin/bash

(cd ~/autojournal; nohup /home/pi/.poetry/bin/poetry run gcal_aggregator --update all &> ~/autojournal.log &)
