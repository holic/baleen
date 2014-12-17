import os
import sys
import traceback
import gearman
import json
import functools

from optparse import make_option
from signal import signal, SIGTERM, SIGINT
from paramiko import AuthenticationException

from django.conf import settings
from django.core.management.base import BaseCommand

from baleen.job.models import Job
from baleen.project.models import Project
from baleen.action import ActionFailure
from baleen.action.dispatch import get_action_object

import statsd
from statsd.counter import Counter
from statsd import Timer

statsd.Connection.set_defaults(host='localhost', port=8125, sample_rate=1, disabled=True)

gearman_worker = gearman.GearmanWorker([settings.GEARMAN_SERVER])


class Command(BaseCommand):
    help = """
"""
    option_list = BaseCommand.option_list + (
            make_option('-p', '--procnum',
                default='0',
                action='store',
                dest='worker_number',
                help="Worker number"
            ),
            make_option('-c', '--clear',
                default=False,
                action='store_true',
                dest='clear_jobs',
                help="Clear all jobs in queue, don't run them."
            ),
            make_option('-r', '--raw-plan',
                default=None,
                action='store',
                dest='raw_plan',
                help="Take a json file as the action plan, run it and exit"
            ),
        )

    def _reset_jobs(self):
        self.current_gearman_job = None
        self.current_baleen_job = None
        self.current_action = None

    def _get_statsd_counters(self, project):
        return {
                'project': {
                    'deploys': Counter('baleen.%s.deploy_count' % project.statsd_name),
                    'success': Counter('baleen.%s.success_count' % project.statsd_name),
                },
                'all': {
                    'deploys': Counter('baleen.all.deploy_count'),
                    'success': Counter('baleen.all.success_count'),
                }
                # TODO: can't track correctly by user until github names are connected to baleen
                # users
                #'user': { 
                    #'deploys': Counter('baleen.all.deploy_count' % project.statsd_name),
                    #'success': Counter('baleen.all.failure_count' % project.statsd_name),
                #}
        }


    def run_task(self, worker, gm_job):
        try:
            self.current_gearman_job = gm_job
            task_data = json.loads(gm_job.data)
            if task_data.get('job'):
                job_id = task_data.get('job')
                return self.run_job(job_id)
            elif task_data.get('project'):
                project_id = task_data.get('project')
                return self.sync_project(project_id)
            else:
                return "Unknown task type"
        except Exception, e:
            print "Unexpected error:", sys.exc_info()[0]
            print str(e)
            traceback.print_tb(sys.exc_info()[2])
            # Usually raising an exception sends a job failure to gearman
            # and this will presumedly restart the job on another worker.

            # If that happens, then things are probably pretty bad, so it's
            # better if we just forget about it.
            self.clean_up()
        return ''


    def sync_project(self, project_id):
        project = Project.objects.get(id=project_id)

        try:
            project.sync_repo()
        except AssertionError:
            print "failed to sync repo"
            raise
        return ''
        

    def run_job(self, job_id):
        worker_pid = os.getpid()
        job = Job.objects.get(id=job_id)

        self.current_baleen_job = job

        actions = job.project.action_plan
        print "Running job %s" % job_id

        # Only one job per project!  Until we have per-project queues,
        # just reject this job if there's already another one running
        # for the same project.
        if job.project.current_job():
            print "Job already in progress!"
            job.reject()
            self._reset_jobs()
            return ''

        # Get statsd connections
        project_t = Timer('baleen.%s.duration' % job.project.statsd_name)
        all_t = Timer('baleen.all.duration')

        counters = self._get_statsd_counters(job.project)
        counters['project']['deploys'] += 1
        counters['all']['deploys'] += 1

        project_t.start()
        all_t.start()
        job.record_start(worker_pid)

        for action in actions:
            try:
                # record this process id so that we can kill it via the web interface
                # supervisord will automatically create a replacement process.
                self.current_action = action
                response = action.run(job)
                self.current_action = None

                if response['code']:
                    # If we got a non-zero exit status, then don't run any more actions
                    raise ActionFailure()

                project_t.intermediate(action.statsd_name)
            except ActionFailure:
                self._reset_jobs()
                return ''

        job.record_done()
        all_t.stop()
        project_t.stop()
        counters['project']['success'] += 1
        counters['all']['success'] += 1
        self._reset_jobs()

        # Return empty string since this is always invoked in background mode, so
        # no-one would see the response anyway
        return ''

    def process_plan(self, plan):
        for step in plan:
            action = get_action_object(step)

            action.run()


    def handle(self, *args, **options):
        self.current_gearman_job = None
        self.current_baleen_job = None
        self.current_action = None

        self.worker_process_number = options['worker_number']

        if options['raw_plan']:
            with open(options['raw_plan']) as f:
                plan_data = json.load(f)
            self.process_plan(plan_data)
        elif options['clear_jobs']:
            print "Removing all jobs in queue..."
            gearman_worker.register_task(settings.GEARMAN_JOB_LABEL, functools.partial(self.clear_job))
        else:
            # Default is to wait for jobs
            gearman_worker.register_task(settings.GEARMAN_JOB_LABEL, functools.partial(self.run_task))

        signal(SIGTERM, self.clean_up)
        signal(SIGINT, self.clean_up)

        print "baleen worker reporting for duty, sir/m'am!"
        gearman_worker.work()

    def clear_job(self, worker, gm_job):
        job_id = json.loads(gm_job.data).get('job_id', None)
        result = "Clearing job for job_id %d" % str(job_id)
        return result

    def clean_up(self, *args):
        print "Exiting, please wait while we update job status"
        if self.current_baleen_job:
            if self.current_action:
                self.current_baleen_job.record_action_response(self.current_action, {
                    'success': False,
                    'message': "Action was interrupted by kill/term signal.",
                })
            else:
                self.current_baleen_job.record_done(success=False)
        if self.current_gearman_job:
            # We need to tell gearman to forget about this job
            gearman_worker.send_job_complete(self.current_gearman_job, data='')
        self._reset_jobs()
        sys.exit(1)
