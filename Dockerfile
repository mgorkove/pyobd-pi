FROM python:2.7

COPY . ./

RUN pip install -r requirements.txt

CMD ["python", "obd_recorder.py"]