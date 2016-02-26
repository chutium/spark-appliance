FROM zalando/python:3.4.0-4
MAINTAINER Teng Qiu <teng.qiu@zalando.de>

ENV SPARK_VERSION="1.6.1-SNAPSHOT" HADOOP_VERSION="2.6.0"
ENV SPARK_PACKAGE="spark-${SPARK_VERSION}-bin-${HADOOP_VERSION}"
ENV SPARK_DIR="/opt/${SPARK_PACKAGE}"

RUN apt-get update && apt-get install wget openjdk-8-jdk -y --force-yes
RUN pip3 install --upgrade kazoo boto3 connexion gevent uwsgi

RUN apt-get install -yq --force-yes --no-install-recommends build-essential python3-dev r-base r-base-dev libzmq3-dev \
 && pip3 install --upgrade zmq py4j jupyter \
 && echo 'options("repos"="http://cran.rstudio.com")' >> /usr/lib/R/etc/Rprofile.site \
 && Rscript -e "install.packages(c('rzmq','repr','IRkernel','IRdisplay'), repos = c('http://irkernel.github.io/', getOption('repos')))" -e "IRkernel::installspec()"

RUN wget https://s3-eu-west-1.amazonaws.com/zalando-spark/toree-kernel-0.1.0-SNAPSHOT.tar.gz -O /tmp/toree-kernel-0.1.0-SNAPSHOT.tar.gz \
 && tar zxf /tmp/toree-kernel-0.1.0-SNAPSHOT.tar.gz -C /opt \
 && rm  -rf /tmp/toree-kernel-0.1.0-SNAPSHOT.tar.gz

RUN pip3 install --upgrade numpy \
 && apt-get install -y --force-yes python3-scipy python3-matplotlib

RUN wget https://s3-eu-west-1.amazonaws.com/zalando-spark/${SPARK_PACKAGE}.tgz -O /tmp/${SPARK_PACKAGE}.tgz \
 && tar zxf /tmp/${SPARK_PACKAGE}.tgz -C /opt \
 && rm -rf /tmp/${SPARK_PACKAGE}.tgz \
 && chmod -R 777 $SPARK_DIR

RUN mv $SPARK_DIR/conf/core-site.xml.zalando $SPARK_DIR/conf/core-site.xml \
 && mv $SPARK_DIR/conf/emrfs-default.xml.zalando $SPARK_DIR/conf/emrfs-default.xml \
 && mv $SPARK_DIR/conf/spark-defaults.conf.zalando $SPARK_DIR/conf/spark-defaults.conf \
 && mv $SPARK_DIR/conf/spark-env.sh.zalando $SPARK_DIR/conf/spark-env.sh \
 && mkdir /tmp/s3 && mkdir /tmp/spark-events && chmod -R 777 /tmp

COPY beeline.tar.gz /tmp/
RUN tar zxf /tmp/beeline.tar.gz -C /opt

COPY swagger.yaml /opt/
COPY webapp.py /opt/

COPY utils.py /opt/
COPY start_all.py /opt/
RUN chmod 777 /opt/start_all.py

COPY kernel.json /tmp/
COPY start_notebook.sh /opt/
RUN chmod 777 /opt/start_notebook.sh

COPY scm-source.json /

WORKDIR /opt

CMD /opt/start_all.py
