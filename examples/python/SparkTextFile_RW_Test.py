from __future__ import print_function

import sys
from operator import add

from pyspark import SparkContext


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: wordcount <input_file> [output_dir]", file=sys.stderr)
        exit(-1)
    sc = SparkContext(appName="PythonWordCount")
    lines = sc.textFile(sys.argv[1], 1)
    counts = lines.flatMap(lambda x: x.split(' ')) \
                  .map(lambda x: (x, 1)) \
                  .reduceByKey(add)
    output = counts.collect()
    for (word, count) in output:
        print("%s: %i" % (word, count))
    if len(sys.argv) > 2:
        print("Saving wordcount results to " + sys.argv[2])
        counts.saveAsTextFile(sys.argv[2])
    sc.stop()
