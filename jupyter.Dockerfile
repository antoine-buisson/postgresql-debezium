FROM jupyter/base-notebook:x86_64-python-3.11.6

COPY jupyter/requirements.txt /tmp/requirements.txt

RUN pip install --no-cache-dir -r /tmp/requirements.txt