# spark-appliance
Distributed Spark standalone cluster appliance for the [STUPS](https://stups.io) AWS environment.

A lot of our data analysis workflows are based on EMR, but there are many conflicts between EMR and STUPS-Policies, so Spark-Appliance will be an alternative to EMR.

Since we use AWS S3 as our data storage layer, so HDFS is not needed, and if we use Spark, MapReduce framework and YARN resource management toolbox as part of traditional Hadoop Ecosystem are not needed either.

Therefore we can use Spark standalone cluster without Hadoop stacks, so that it will be easier to make it work in STUPS AWS environment.

## EMRFS support

EMRFS is an Hadoop-compatible implementation that allows EMR clusters to access data on Amazon S3, which provides much more features than the native S3 implementation in Hadoop.

As mentioned we use AWS S3 as data storage, original Spark is working with Hadoop S3 implementation which is based on predefined AWS security credentials, not IAM role based.

Our [Senza](https://stups.io/senza/) appliances are running on the EC2 instances with appropriate IAM roles, we do not want to distribute or embed long-term AWS security credentials within an instance or application.

So we need to integrate the implementation of Amazon's EMRFS and Spark, we created [a branch for this](https://github.com/zalando/spark/tree/branch-1.5-zalando) in our github account.

## Usage

You can use the docker environment variables ```START_MASTER```, ```START_WORKER```, ```START_THRIFTSERVER``` to select the daemon to be started.

Notice that if you do not need the [thrift server](https://spark.apache.org/docs/1.5.0/sql-programming-guide.html#distributed-sql-engine), we suggest you to set the environment variable ```START_THRIFTSERVER=""```. Because the thrift server is not an external daemon process, it will be running as a Spark application and create some executors in the cluster and therefore will take up resources of the Spark cluster as well as other Spark applications submitted by ```spark-submit``` script. This resource consumption may cause your other Spark applications not getting enough resources to start when you use a small EC2 instance type like t2-series.

### Running with Docker locally

```
sudo docker build -t pierone.example.org/bi/spark:0.1-SNAPSHOT .

sudo docker run -e START_MASTER="true" \
                -e START_WORKER="true" \
                -e START_THRIFTSERVER="" \
                -e MASTER_STRING="" \
                -e ZOOKEEPER_STACK_NAME="" \
                -e HIVE_SITE_XML="" \
                --net=host \
                pierone.example.org/bi/spark:0.1-SNAPSHOT
```

### Deploying with Senza

#### Deploying on single node

```
senza create spark.yaml singlenode \
             DockerImage=pierone.example.org/bi/spark:0.1-SNAPSHOT \
             ApplicationID=spark \
             MintBucket=stups-mint-000000000-eu-west-1 \
             ScalyrKey=XXXYYYZZZ \
             StartMaster=true \
             StartWorker=true \
             StartThriftServer=true
```

#### Cluster mode

```
senza create spark.yaml master \
             DockerImage=pierone.example.org/bi/spark:0.1-SNAPSHOT \
             ApplicationID=spark \
             MintBucket=stups-mint-000000000-eu-west-1 \
             ScalyrKey=XXXYYYZZZ \
             StartMaster=true
```

then use ```senza instance spark``` to find the IP of stack spark-master, use this IP within the MasterString, like: ```spark://172.31.xxx.xxx:7077```

```
senza create spark.yaml worker \
             DockerImage=pierone.example.org/bi/spark:0.1-SNAPSHOT \
             ApplicationID=spark \
             MintBucket=stups-mint-000000000-eu-west-1 \
             ScalyrKey=XXXYYYZZZ \
             StartWorker=true \
             MasterString="spark://172.31.xxx.xxx:7077" \
             ClusterSize=3
```

### Build distribution package and try it out

Use branch: https://github.com/zalando/spark/tree/branch-1.5-zalando

Create distribution package

```./make-distribution.sh --tgz --mvn ./build/mvn -Phadoop-2.6 -Phive -Phive-thriftserver -DskipTests```

Then you will get a Spark distribution with EMRFS support. Put this package in to an EC2 instance with appropriate IAM role and try it out with:

```
cd $SPARK_HOME
mv conf/core-site.xml.zalando conf/core-site.xml
mv conf/emrfs-default.xml.zalando conf/emrfs-default.xml
mv conf/spark-env.sh.zalando conf/spark-env.sh

aws s3 cp README.md s3://some-bucket/
bin/spark-shell --master local[2]

scala> val textFile = sc.textFile("s3://some-bucket/README.md")
scala> textFile.count
```

## TODOs

* Spark HA with zookeeper
* Start Spark cluster with given hive-site.xml
* add more start/env variables such as -c (--cores) and -m (--memory)
* spark-submit wrapper with ssh-tunnel
* Spark sql wrapper with ssh-tunnel
* Appliance to deploy Spark cluster programmatically
* Add Kafka/[Buku](https://github.com/zalando/saiki-buku) support
* Add [Cassandra](https://github.com/zalando/stups-cassandra) support
* Add postgres/[Spilo](https://github.com/zalando/spilo) support
