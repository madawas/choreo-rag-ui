FROM python:3.12.2-slim

WORKDIR /home

RUN mkdir app

COPY ./* /home/app

RUN mkdir uploads

RUN pip install -r /home/requirements.txt

RUN addgroup --gid 10016 choreo && \
    adduser --system --no-create-home --uid 10020 --ingroup choreo raguser
USER 10020

EXPOSE 8501

# HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

ENTRYPOINT [ "streamlit", "run", "/home/app/app.py", "--server.port=8501", "--server.address=0.0.0.0" ]