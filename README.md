# spark-appliance
Distributed Spark standalone cluster appliance for the [STUPS](https://stups.io) AWS environment.

A lot of our data analysis workflows are based on EMR, but there are many conflicts between EMR and STUPS-Policies, so Spark-Appliance will be an alternative to EMR.

Since we use AWS S3 as our data storeage layer, so HDFS is not needed, and if we use Spark, MapReduce framework and YARN resource management toolbox as part of traditional Hadoop Ecosystem are not needed either.

Therefore we can use Spark standalone cluster without Hadoop stacks, so that it will be easier to make it work in STUPS AWS environment.

## EMRFS support

As mentioned we use AWS S3 as data storeage, original Spark is working with Hadoop S3 implementation which is based on predefined AWS security credentials, not IAM role based.

Our [Senza](https://stups.io/senza/) appliances are running on the EC2 instances with appropriate IAM roles, we do not want to distribute or embed long-term AWS security credentials within an instance or application.

So we need to integrate the implementation of Amazon's EMRFS and Spark, we created a branch for this in our github account: https://github.com/zalando/spark/tree/branch-1.5-zalando

## Usage

TBA

### local test

TBA

### build distribution package and try it out

use branch: https://github.com/zalando/spark/tree/branch-1.5-zalando

create distribution package

```./make-distribution.sh --tgz --mvn ./build/mvn -Phadoop-2.6 -Phive -Phive-thriftserver -DskipTests```

then you will get a spark distribution with EMRFS support, put this package in to an EC2 instance with appropriate IAM role, and you can try it like:

```
cd $SPARK_HOME
aws s3 cp README.md s3://some-bucket/
bin/spark-shell --master local[2]

scala> val textFile = sc.textFile("s3://some-bucket/README.md")
scala> textFile.count
```

## TODOs

* spark-submit wrapper with ssh-tunnel
* spark sql wrapper with ssh-tunnel
* Appliance to deploy Spark cluster programmatically
* add Kafka support
* add [Cassandra](https://github.com/zalando/stups-cassandra) support
* add postgres/[spilo](https://github.com/zalando/spilo) support
