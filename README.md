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

Note that if you do not need the [thrift server](https://spark.apache.org/docs/1.5.0/sql-programming-guide.html#distributed-sql-engine), we suggest you to set the environment variable ```START_THRIFTSERVER=""```. Because the thrift server is not an external daemon process, it will be running as a Spark application and create some executors in the cluster and therefore will take up resources of the Spark cluster as well as other Spark applications submitted by ```spark-submit``` script. This resource consumption may cause your other Spark applications not getting enough resources to start when you use a small EC2 instance type like t2-series.

Now you can use following deploy mode
  * [Docker locally](#running-with-docker-locally)
  * [Deploying with Senza](#deploying-with-senza)
    * [Single node (all in one)](#deploying-on-single-node)
    * [Cluster mode](#cluster-mode)
    * [HA mode with ZooKeeper](#ha-mode)
  * [Build distribution package from source code](build-distribution-package-and-try-it-out)
  * [Loading hive-site xml config file from S3](loading-hive-site-xml-config-file-from-s3)

### Running with Docker locally

```
sudo docker build -t pierone.example.org/bi/spark:0.1-SNAPSHOT .

sudo docker run -e START_MASTER="true" \
                -e START_WORKER="true" \
                -e START_THRIFTSERVER="" \
                -e MASTER_URI="" \
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

then use ```senza instance spark``` to find the IP of stack spark-master, use this IP within the MasterURI, like: ```spark://172.31.xxx.xxx:7077```

```
senza create spark.yaml worker \
             DockerImage=pierone.example.org/bi/spark:0.1-SNAPSHOT \
             ApplicationID=spark \
             MintBucket=stups-mint-000000000-eu-west-1 \
             ScalyrKey=XXXYYYZZZ \
             StartWorker=true \
             MasterURI="spark://172.31.xxx.xxx:7077" \
             ClusterSize=3
```

#### HA mode

Spark uses ZooKeeper for master process failure recovery in cluster mode. In STUPS AWS environment to run Spark in High Availability, you need to start a ZooKeeper appliance, we suggest you to use [exhibitor-appliance](https://github.com/zalando/exhibitor-appliance).

Sample senza create script for creating exhibitor-appliance:
```
senza create exhibitor-appliance.yaml spark \
             DockerImage=pierone.example.org/teamid/exhibitor:0.1-SNAPSHOT \
             ExhibitorBucket=exhibitor \
             ApplicationID=exhibitor \
             MintBucket=stups-mint-000000000-eu-west-1 \
             ScalyrAccountKey=XXXYYYZZZ \
             HostedZone=example.org.
```

After the deployment finished, you will have a Route53 record for this stack, like ```exhibitor-spark.example.org```, use this as ```ZookeeperConnString```, you can create a HA Spark cluster:
```
senza create spark.yaml ha \
             DockerImage=pierone.stups.zalan.do/bi/spark:0.1-SNAPSHOT \
             ApplicationID=spark \
             MintBucket=zalando-stups-mint-000000000-eu-west-1 \
             ScalyrKey=XXXYYYZZZ \
             StartMaster=true \
             StartWorker=true \
             ClusterSize=3 \
             ZookeeperConnString="exhibitor-spark.example.org:2181"
```

This command with ```StartMaster=true``` and ```StartWorker=true``` will start both master daemon process and worker daemon on each node, if you would like to deploy master instances and worker instances separately like by [cluster mode](#cluster-mode), then the senza create script should be:
```
senza create spark.yaml master \
             DockerImage=pierone.stups.zalan.do/bi/spark:0.1-SNAPSHOT \
             ApplicationID=spark \
             MintBucket=zalando-stups-mint-000000000-eu-west-1 \
             ScalyrKey=XXXYYYZZZ \
             StartMaster=true \
             ClusterSize=3 \
             ZookeeperConnString="exhibitor-spark.example.org:2181"
```
(only different is, here you do not set ```StartWorker=true```. Moreover, the thrift server must be started on one of master instances, so if you want to use thrift server, you should set ```StartThriftServer=true``` here.)

And you will get the master IPs from senza command: ```senza instance spark master```, use them as MasterURI, like: ```spark://172.31.xxx.xxx:7077,172.31.yyy.yyy:7077,172.31.zzz.zzz:7077```, and create workers:
```
senza create spark.yaml worker \
             DockerImage=pierone.stups.zalan.do/bi/spark:0.1-SNAPSHOT \
             ApplicationID=spark \
             MintBucket=zalando-stups-mint-000000000-eu-west-1 \
             ScalyrKey=XXXYYYZZZ \
             MasterURI="spark://172.31.xxx.xxx:7077,172.31.yyy.yyy:7077,172.31.zzz.zzz:7077" \
             StartWorker=true \
             ClusterSize=5 \
             ZookeeperConnString="saiki-exhibitor-spark.saiki.zalan.do:2181"
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

* ~~Spark HA with zookeeper~~ done by PR [#2](https://github.com/zalando/spark-appliance/pull/2), doc: [HA mode with ZooKeeper](#ha-mode)
* Start Spark cluster with given hive-site.xml
* add more start/env variables such as -c (--cores) and -m (--memory)
* spark-submit wrapper with ssh-tunnel
* Spark sql wrapper with ssh-tunnel
* Appliance to deploy Spark cluster programmatically
* Add Kafka/[Buku](https://github.com/zalando/saiki-buku) support
* Add [Cassandra](https://github.com/zalando/stups-cassandra) support
* Add postgres/[Spilo](https://github.com/zalando/spilo) support
