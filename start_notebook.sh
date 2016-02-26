#!/usr/bin/env bash

export SPARK_HOME=$SPARK_DIR
export PYTHONPATH=$SPARK_HOME/python:$SPARK_HOME/python/lib/py4j-0.9-src.zip:$PYTHONPATH

sed -i "s%\${SPARK_MASTER}%$1%g" /tmp/kernel.json
sed -i "s%\${SPARK_HOME}%$SPARK_HOME%g" /tmp/kernel.json
sed -i "s%\${PYTHONPATH}%$PYTHONPATH%g" /tmp/kernel.json
mkdir -p /root/.local/share/jupyter/kernels/spark
mv /tmp/kernel.json /root/.local/share/jupyter/kernels/spark/kernel.json

mkdir /opt/jupyter
cd /opt/jupyter
jupyter-notebook --ip 0.0.0.0 --port 8888 --no-browser
