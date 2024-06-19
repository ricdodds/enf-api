FROM python:3.9

ENV APP_HOME /app
WORKDIR $APP_HOME

COPY app/requirements.txt $APP_HOME/requirements.txt
RUN pip install -U pip && pip install -r $APP_HOME/requirements.txt

COPY app/ $APP_HOME/
