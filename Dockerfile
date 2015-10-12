FROM zalando/python:3.4.0-4
MAINTAINER Teng Qiu <teng.qiu@zalando.de>

ENV SPARK_VERSION="1.5.2-SNAPSHOT" HADOOP_VERSION="2.6.0"
ENV SPARK_PACKAGE="spark-${SPARK_VERSION}-bin-${HADOOP_VERSION}"
ENV SPARK_DIR="/opt/${SPARK_PACKAGE}"

RUN apt-get update && apt-get install wget openjdk-8-jdk -y --force-yes
RUN pip3 install --upgrade kazoo boto3 connexion gevent uwsgi

RUN wget https://s3-eu-west-1.amazonaws.com/zalando-spark/${SPARK_PACKAGE}.tgz -O /tmp/${SPARK_PACKAGE}.tgz \
 && tar zxf /tmp/${SPARK_PACKAGE}.tgz -C /opt && rm -rf /tmp/${SPARK_PACKAGE}.tgz \
 && chmod -R 777 $SPARK_DIR \
 && mv $SPARK_DIR/conf/core-site.xml.zalando $SPARK_DIR/conf/core-site.xml \
 && mv $SPARK_DIR/conf/emrfs-default.xml.zalando $SPARK_DIR/conf/emrfs-default.xml \
 && mv $SPARK_DIR/conf/spark-env.sh.zalando $SPARK_DIR/conf/spark-env.sh \
 && mkdir /tmp/s3 && chmod -R 777 /tmp/s3

COPY swagger.yaml /opt/
COPY webapp.py /opt/

COPY utils.py /opt/
COPY start_all.py /opt/
RUN chmod 777 /opt/start_all.py

WORKDIR /opt

CMD /opt/start_all.py
