# spark-appliance
Distributed Spark standalone cluster appliance for the [STUPS](https://stups.io) AWS environment.

A lot of our data analysis workflows are based on EMR, but there are many conflicts between EMR and STUPS-Policies, so Spark-Appliance will be an alternative to EMR.

Since we use AWS S3 as our data storage layer, HDFS is not needed, and if we use Spark, MapReduce framework and YARN resource management toolbox as part of traditional Hadoop Ecosystem are not needed either.

Therefore we can use Spark standalone cluster without Hadoop stacks, so that it will be easier to make it work in STUPS AWS environment.

## EMRFS support

EMRFS is a Hadoop-compatible implementation that allows EMR clusters to access data on Amazon S3, which provides much more features than the native S3 implementation in Hadoop.

As mentioned we use AWS S3 as data storage, original Spark is working with Hadoop S3 implementation which is based on predefined AWS security credentials, not IAM role based.

Our [Senza](https://stups.io/senza/) appliances are running on the EC2 instances with appropriate IAM roles, we do not want to distribute or embed long-term AWS security credentials within an instance or application.

So we need to integrate the implementation of Amazon's EMRFS and Spark, we created [a branch for this](https://github.com/zalando/spark/tree/branch-1.5-zalando) in our github account.

# Usage

* [Deployment with Docker and/or Senza](#deployment)
  * [Docker locally](#running-with-docker-locally)
  * [Deploying with Senza](#deploying-with-senza)
    * [Single node (all in one)](#deploying-on-single-node)
    * [Cluster mode](#cluster-mode)
    * [HA mode with ZooKeeper](#ha-mode)
  * [(Spark SQL user only) Creating hive metastore and loading hive-site.xml config file from S3](#creating-hive-metastore-and-loading-hive-site-xml-config-file-from-s3)
  * [Build spark distribution package from source code](#build-distribution-package-and-try-it-out)
* [How To Use -- HTTP REST Call examples](#how-to-use)
  * [Get cluster info (e.g. master URI, JDBC server URI)](#getting-spark-cluster-info)
  * [submit Spark SQL query via beeline](#submitting-spark-sql-query-via-beeline)
  * [submit Spark SQL query via REST API (for robot user for example)](#submitting-spark-sql-query-via-rest-api)
  * [submit Spark Jar or Python script via spark-submit](#submitting-spark-jar-or-python-script-via-spark-submit)
  * [submit Spark Jar or Python script via REST API](#submitting-spark-jar-or-python-script-via-rest-api)
* [TODOs](#todos)

## Deployment

You can use the docker environment variables ```START_MASTER```, ```START_WORKER```, ```START_THRIFTSERVER```, ```START_WEBAPP``` to select the daemon to be started.

Note that if you do not need the [thrift server](https://spark.apache.org/docs/1.5.0/sql-programming-guide.html#distributed-sql-engine), we suggest you to set the environment variable ```START_THRIFTSERVER=""```. Because the thrift server is not an external daemon process, it will be running as a Spark application and create some executors in the cluster and therefore will take up resources of the Spark cluster as well as other Spark applications submitted by ```spark-submit``` script. This resource consumption may cause your other Spark applications not getting enough resources to start when you use a small EC2 instance type like t2-series.

### Running with Docker locally

```
sudo docker build -t pierone.example.org/bi/spark:1.5.2-SNAPSHOT .

sudo docker run -e START_MASTER="true" \
                -e START_WORKER="true" \
                -e START_THRIFTSERVER="" \
                -e START_WEBAPP="true" \
                -e MASTER_STACK_NAME="" \
                -e CLUSTER_SIZE="1" \
                -e ZOOKEEPER_STACK_NAME="" \
                -e HIVE_SITE_XML="" \
                --net=host \
                pierone.example.org/bi/spark:1.5.2-SNAPSHOT
```

### Deploying with Senza

#### Deploying on single node

```
senza create spark.yaml singlenode \
             DockerImage=pierone.example.org/bi/spark:1.5.2-SNAPSHOT \
             ApplicationID=spark \
             MintBucket=stups-mint-000000000-eu-west-1 \
             ScalyrKey=XXXYYYZZZ \
             StartMaster=true \
             StartWorker=true \
             StartThriftServer=true \
             StartWebApp=true \
             HostedZone="teamid.example.org." \
             SSLCertificateId="ARN_of_your_SSL_Certificate"
```

```SSLCertificateId``` needed by WebApp to enable HTTPS, and ```HostedZone``` is used for creating Route53 DNS record.

To enable OAuth2 you need to specify ```AuthURL``` and ```TokenInfoURL``` as well.


#### Cluster mode

```
senza create spark.yaml master \
             DockerImage=pierone.example.org/bi/spark:1.5.2-SNAPSHOT \
             ApplicationID=spark \
             MintBucket=stups-mint-000000000-eu-west-1 \
             ScalyrKey=XXXYYYZZZ \
             StartMaster=true \
             StartWebApp=true \
             HostedZone="teamid.example.org." \
             SSLCertificateId="ARN_of_your_SSL_Certificate"
```

then wait until ```senza list spark``` shows that CloudFormation stack ```spark-master``` with status ```CREATE_COMPLETE```.

```
senza create spark.yaml worker \
             DockerImage=pierone.example.org/bi/spark:1.5.2-SNAPSHOT \
             ApplicationID=spark \
             MintBucket=stups-mint-000000000-eu-west-1 \
             ScalyrKey=XXXYYYZZZ \
             MasterStackName="spark-master" \
             StartWorker=true \
             ClusterSize=3 \
             HostedZone="teamid.example.org." \
             SSLCertificateId="ARN_of_your_SSL_Certificate"
```

With above commands, one spark master node will running with ```WebApp```, and 3 spark worker node will be registered to this spark master node.

You can run a ```WebApp``` node separately with following senza command:

```
senza create spark.yaml webapp \
             DockerImage=pierone.example.org/bi/spark:1.5.2-SNAPSHOT \
             ApplicationID=spark \
             MintBucket=stups-mint-000000000-eu-west-1 \
             ScalyrKey=XXXYYYZZZ \
             MasterStackName="spark-master" \
             StartWebApp=true \
             HostedZone="teamid.example.org." \
             SSLCertificateId="ARN_of_your_SSL_Certificate"
```

That means, just change ```StartWorker=true``` to ```StartWebApp=true```, and remove the ```ClusterSize``` setting, then you should be able to access the WebApp with an URL like: ```https://spark-webapp.teamid.example.org```.

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
             HostedZone=teamid.example.org.
```

After the deployment finished, you will have a CloudFormation stack ```exhibitor-spark```, use this as ```ZookeeperStackName```, you can create a HA Spark cluster:
```
senza create spark.yaml ha \
             DockerImage=pierone.stups.zalan.do/bi/spark:1.5.2-SNAPSHOT \
             ApplicationID=spark \
             MintBucket=zalando-stups-mint-000000000-eu-west-1 \
             ScalyrKey=XXXYYYZZZ \
             StartMaster=true \
             StartWorker=true \
             StartWebApp=true \
             ClusterSize=3 \
             HostedZone="teamid.example.org." \
             SSLCertificateId="ARN_of_your_SSL_Certificate" \
             ZookeeperStackName="exhibitor-spark"
```

Now you get a spark cluster with 3 master and 3 worker nodes.

This senza create command with ```StartMaster=true``` and ```StartWorker=true``` will start both master daemon process and worker daemon process on each node, if you would like to deploy master instances and worker instances separately like by [cluster mode](#cluster-mode), then you need to use two senza create commands.

First, create spark master + webapp stack:
```
senza create spark.yaml master \
             DockerImage=pierone.stups.zalan.do/bi/spark:0.1-SNAPSHOT \
             ApplicationID=spark \
             MintBucket=zalando-stups-mint-000000000-eu-west-1 \
             ScalyrKey=XXXYYYZZZ \
             StartMaster=true \
             StartWebApp=true \
             ClusterSize=3 \
             HostedZone="teamid.example.org." \
             SSLCertificateId="ARN_of_your_SSL_Certificate" \
             ZookeeperStackName="exhibitor-spark"
```
(only different is, here you do not set ```StartWorker=true```. Moreover, the thrift server must be started on one of master instances, so if you want to use thrift server, you should set ```StartThriftServer=true``` here.)

And wait until CloudFormation stack ```spark-master``` completely deployed, then create workers:
```
senza create spark.yaml worker \
             DockerImage=pierone.stups.zalan.do/bi/spark:0.1-SNAPSHOT \
             ApplicationID=spark \
             MintBucket=zalando-stups-mint-000000000-eu-west-1 \
             ScalyrKey=XXXYYYZZZ \
             StartWorker=true \
             ClusterSize=5 \
             HostedZone="teamid.example.org." \
             SSLCertificateId="ARN_of_your_SSL_Certificate" \
             ZookeeperStackName="exhibitor-spark" \
             MasterStackName="spark-master"
```

### Creating hive metastore and loading hive-site xml config file from S3

To use [Spark SQL](http://spark.apache.org/sql/), we suggest you create a [hive metastore](https://cwiki.apache.org/confluence/display/Hive/Design#Design-Metastore), and put the DB connection settings in a hive-site.xml file, there are a lot of good documents for creating hive metastore and hive-site.xml, since we are using AWS environment, we can use RDS service and you can take a look the document from AWS for [creating hive metastore located in Amazon RDS](http://docs.aws.amazon.com/ElasticMapReduce/latest/DeveloperGuide/emr-dev-create-metastore-outside.html).

Currently the spark appliance support MySQL or PostgreSQL database as hive metastore, and due to security policies, make sure that you created the RDS instance with ```Subnet Group: internal```, ```Publicly Accessible: no```, and right Security groups.

Once you have this hive-site.xml, you can pack it into your own docker image, and push this docker image into PierOne repo. Or you upload this hive-site.xml to S3, and use ```HiveSite``` parameter by senza create, such as:
```
senza create spark.yaml singlenode \
             DockerImage=pierone.example.org/bi/spark:0.1-SNAPSHOT \
             ApplicationID=spark \
             MintBucket=stups-mint-000000000-eu-west-1 \
             ScalyrKey=XXXYYYZZZ \
             StartMaster=true \
             StartWorker=true \
             StartWebApp=true \
             StartThriftServer=true \
             HostedZone="teamid.example.org." \
             SSLCertificateId="ARN_of_your_SSL_Certificate"
             HiveSite="s3://hive-configs/hive-site.xml"
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

## How to use

### getting spark cluster info

If you send the HTTP call from an EC2 instance in the same AWS account for spark-webapp stack, such as on the [Odd](https://stups.io/odd/) server, you can use the REST API of spark-webapp directly:

```
host=172.31.xxx.xxx
curl http://$host:8000/get_master_ip
curl http://$host:8000/get_master_uri
curl http://$host:8000/get_thrift_server_uri
```

In case if you enabled OAuth2, then you need to add a header info with valid oauth2_token (currently we just use the ```uid``` scope) by the curl call:

```
oauth_token=xxxxx-xxx-xxx-xxx-xxxxx
host=172.31.xxx.xxx
curl --insecure --request GET --header "Authorization: Bearer $oauth_token" http://$host:8000/get_master_ip
curl --insecure --request GET --header "Authorization: Bearer $oauth_token" http://$host:8000/get_master_uri
curl --insecure --request GET --header "Authorization: Bearer $oauth_token" http://$host:8000/get_thrift_server_uri
```

### from outside using ssh tunnel or internet-facing ELB

There are two ways to send HTTP call outside of AWS account:

a) create a ssh tunnel to the port 8000 on spark-webapp node via Odd server, then send HTTP call to localhost:
```
ssh -L 8000:web_app_node_ip:8000 username@odd-server
curl http://localhost:8000/get_master_ip
curl http://localhost:8000/get_master_uri
```

or

b) create an internet-facing ELB, then you can send HTTPS call to the webapp stack's domain name from anywhere with a valid OAuth2 token
```
oauth_token=xxxxx-xxx-xxx-xxx-xxxxx
host=spark-webapp.teamid.example.org
curl --insecure --request GET --header "Authorization: Bearer $oauth_token" https://$host/get_master_ip
curl --insecure --request GET --header "Authorization: Bearer $oauth_token" https://$host/get_master_uri
```

### submitting Spark SQL query via beeline

To send Spark SQL query directly to the spark-appliance created by senza, you need to create a ssh tunnel to the port 10000 on thrift server node via Odd server at first, after that you can connect to localhost:10000 using beeline:

```
ssh -L 10000:thrift_server_ip:10000 username@odd-server
beeline -u jdbc:hive2://localhost:10000/ -f some-hive-query.sql
```

Or if you use beeline on an EC2 instance in your AWS account, such as on the Odd server, you can use beeline with spark-appliance's URI directly:

```
beeline -u $(curl http://$host:8000/get_thrift_server_uri) -f some-hive-query.sql
```

### submitting Spark SQL query via REST API

```
oauth_token=xxxxx-xxx-xxx-xxx-xxxxx
host=172.31.xxx.xxx

### assume you have a table my_tbl created in db_test in hive
### then create a simple Hive count SQL script for this table
echo "select count(*) from db_test.my_tbl;" > count.sql

job_id=$(curl --insecure --request POST --header "Authorization: Bearer $oauth_token" -F file=@count.sql http://$host:8000/send_query)
curl --insecure --request GET --header "Authorization: Bearer $oauth_token" http://$host:8000/get_job_status/$job_id
curl --insecure --request GET --header "Authorization: Bearer $oauth_token" http://$host:8000/get_job_output/$job_id
```

If you created an internet-facing ELB, you can submit a Spark SQL query to the webapp stack's domain name from anywhere with a valid OAuth2 token.


### submitting Spark JAR or Python script via spark-submit

For Spark JAR, you need to specify a main class name:

```spark-submit --class your.main.class --master $(curl http://$host:8000/get_master_uri) your.jar```

For python script, no main class needed:

```spark-submit --master $(curl http://$host:8000/get_master_uri) your.py```


### submitting Spark JAR or Python script via REST API

see https://github.com/zalando/spark-appliance/pull/10#issue-112365605


## TODOs

* ~~Spark HA with zookeeper~~ done by PR [#2](https://github.com/zalando/spark-appliance/pull/2), doc: [HA mode with ZooKeeper](#ha-mode)
* ~~Start Spark cluster with given hive-site.xml~~ done by PR [#3](https://github.com/zalando/spark-appliance/pull/3), doc: [hive metastore and hive-site.xml](#creating-hive-metastore-and-loading-hive-site-xml-config-file-from-s3)
* ~~WebApp to get MasterURI (in order to use ```spark-submit```)~~ done by PR [#5](https://github.com/zalando/spark-appliance/pull/5)
* ~~WebApp to get connection string to ThriftServer (in order to use ```spark-sql``` or ```beeline```)~~ done by PR [#7](https://github.com/zalando/spark-appliance/pull/7)
* ~~WebApp to run Spark SQL queries~~ done by PR [#9](https://github.com/zalando/spark-appliance/pull/9), doc see comment in this PR
* ~~WebApp to run Spark jars~~ done by [commit in PR #10](https://github.com/zalando/spark-appliance/pull/10/files#diff-e3c098dce5f8e4cc400b229d92ecf24cR74), example jar committed: [spark-textfile-example](https://github.com/zalando/spark-appliance/tree/master/examples/scala/spark-textfile-example), doc see comment in this PR
* ~~WebApp to run Spark python scripts~~ done by [commit in PR #10](https://github.com/zalando/spark-appliance/pull/10/files#diff-e3c098dce5f8e4cc400b229d92ecf24cR82), doc see comment in this PR
* WebApp to run Spark R -- is this possible? seems not in current version (1.5.2)
* Add more start/env variables such as -c (--cores) and -m (--memory)
* Appliance to deploy Spark cluster programmatically
* Add code sample for Kafka/[Buku](https://github.com/zalando/saiki-buku) support
* Add code sample for [Cassandra](https://github.com/zalando/stups-cassandra) support
* Add code sample for postgres/[Spilo](https://github.com/zalando/spilo) support
* Web interface to Spark shell
