from flask import Flask
from flask_restful import reqparse, abort, Api, Resource

from pytz import utc
from datetime import datetime, timedelta
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.executors.pool import ThreadPoolExecutor, ProcessPoolExecutor

# required logging for apscheduler errors, need to make fancier
import logging
logging.basicConfig()

import requests

# configure APScheduler runtime details
jobstores = {
    'default': SQLAlchemyJobStore(url='sqlite:///jobs.sqlite')
}
executors = {
    'default': ThreadPoolExecutor(20),
    'processpool': ProcessPoolExecutor(5)
}
job_defaults = {
    'coalesce': False,
    'max_instances': 3
}

# configure scheduler object, then let it rip
scheduler = BackgroundScheduler(jobstores=jobstores, executors=executors, job_defaults=job_defaults, timezone=utc)
scheduler.start()

# configure reqparse for flask, filter wanted variables
parser = reqparse.RequestParser()
parser.add_argument('url')
parser.add_argument('data')
parser.add_argument('time')

def unpackjob(input):
    output = {}
    output['id'] = str(input.id)
    output['name'] = str(input.name)
    output['next_run_time'] = str(input.next_run_time)
    output['args'] = str(input.args)
    return output

# Job
class Job(Resource):
    def get(self, job_id):
        return unpackjob(scheduler.get_job(job_id))

    def delete(self, job_id):
        scheduler.remove_job(job_id)
        return '', 204


# JobList
class JobList(Resource):
    # get list of jobs
    def get(self):
        return [unpackjob(job) for job in scheduler.get_jobs()]

    # add a new job to the list
    def post(self):
        args = parser.parse_args()
        url = args['url']
        data = args['data']
        time = args['time']
        temp = unpackjob(scheduler.add_job(curl, 'date', run_date=time, args=[url, data]))
        return temp, 201


class Test(Resource):
    def get(self):
        print "response received", datetime.utcnow()
        return 200

def curl(url, data):
    response = requests.get(url, data=data)
    print url, response, datetime.utcnow()

# let flask rip
app = Flask(__name__)
api = Api(app)

# configure api routing
api.add_resource(JobList, '/jobs')
api.add_resource(Job, '/jobs/<job_id>')
api.add_resource(Test, '/test')

if __name__ == '__main__':
    app.run(debug=True)