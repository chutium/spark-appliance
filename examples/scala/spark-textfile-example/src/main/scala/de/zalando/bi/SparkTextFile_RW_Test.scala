package de.zalando.bi

import org.apache.spark._


object SparkTextFile_RW_Test {

  /** Usage: SparkTextFile_RW_Test <input_file> [output_dir] */
  def main(args: Array[String]) {
    if (args.length < 1) {
      System.err.println("Usage: SparkTextFile_RW_Test <file> [output_dir]")
      System.exit(1)
    }
    val sparkConf = new SparkConf().setAppName("SparkTextFile")
    val sc = new SparkContext(sparkConf)
    val file = sc.textFile(args(0))
    val mapped = file.map(s => s.length).cache()
    for (iter <- 1 to 10) {
      val start = System.currentTimeMillis()
      for (x <- mapped) { x + 2 }
      val end = System.currentTimeMillis()
      println("Iteration " + iter + " took " + (end-start) + " ms")
    }
    if (args.length == 2) {
      mapped.saveAsTextFile(args(1))
      println("Results saved to " + args(1))
    } else {
      mapped.saveAsTextFile(args(0) + ".mapped")
      println("Results saved to " + args(0) + ".mapped")
    }
    sc.stop()
  }
}
