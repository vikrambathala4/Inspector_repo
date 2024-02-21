#!/usr/bin/env python3

import json
import logging
import sys

def main():
    input_file = sys.argv[1]
    logging.info("reading file: ", input_file)
    f = open(sys.argv[1], "r")
    data = json.load(f)
    print(json.dumps(data, indent=4))
    logging.info("finished")


if __name__ == "__main__":
    main()
