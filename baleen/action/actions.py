import time
import json
import os
import paramiko
import subprocess
import tempfile
import yaml
import gearman

from StringIO import StringIO
from stat import S_ISDIR

from django.conf import settings

from baleen.utils import (
        statsd_label_converter, generate_ssh_key,
        make_tarfile,
        mkdir_p
        )
from baleen.artifact.models import output_types, ActionOutput


def parse_build_definition(bd):
    plan_type = bd.detect_plan_type()
    if plan_type == 'docker':
        plan = DockerActionPlan(bd)
    else:
        return NotImplemented

    return plan.formulate_plan()


class ActionPlan(object):

    """Is an iterator that returns Actions """

    def __init__(self, build_definition):
        self.build_definition = build_definition
        self.current_index = -1

    def formulate_plan(self):
        return NotImplemented

    def next(self):
        self.current_index += 1
        return self.plan[self.current_index]


class DockerActionPlan(object):

    """Is an iterator that returns BuildSteps"""

    def formulate_plan(self):
        build_data = yaml.load(StringIO(self.build_definition))

        dependencies = build_data.get('depends', {})
        if dependencies:
            # Then check dependencies and create any missing projects.
            self.create_missing_projects()
            #self.trigger_dependency_builds
            #set up waiting_for if needed, and raise Exception
            pass

        containers_to_build_and_test = build_data['build']

        for c in containers_to_build_and_test:
            #DockerAction()
            pass

        return [{ 'name': 'action1' }]

    def wait_for_project(self, project):
        """
        Tracking when a project is waiting on another one to complete.

        Need to remove all temporary hooks for a given project when that
        project is synced with github (since dependencies may change).
        """
        pass

    def get_and_create_projects(self, deps):
        """
        Deals with this part of the build definition:

        depends:
           rabbitmq:
              src: "git@github.com:docker-systems/rabbitmq.git"
              minhash: "deedbeef" # must have this commit
              # image should be inferred from the baleen.yml of the src repo
              # image: "docker.example.com/rabbitmq"
              #tag: v0.1.1
        """
        projects = []
        for d in deps:
            src_repo = d.get('src')
            # Check it is actually a repo as opposed to just an image that can
            # be pulled from somewhere:
            if src_repo is None:
                continue

            # check if a project is already using the repo

            # create a new project if not
            projects.append((p, d.get('minhash')))
        return projects


    def trigger_dependency_builds(self, projects):
        # check which projects already have a successful build, and trigger builds
        # for those that don't
        for p, minhash in projects:
            j = p.last_successful_job()

            if j and p.commit_in_history(minhash, j.commit):
                # We already have a successful job that is new enough
                continue

            from baleen.job.models import manual_run
            manual_run(p)


class ExpectedActionOutput(object):
    """ Define expected output from action.

    All Actions produce stdout, stderr, and an exit code.

    Linking ExpectedActionOutput allows for an action to also provide output
    in files or by other mechanisms.

    - 'output_type' is a constant from baleen.action.models.output_types
      indicating the type of output.
    - 'location' indicates where the output is available. It's meaning depends
      on the action_type.
      
    """

    def __init__(self, action, output_type, location=None):
        self.action = action
        self.output_type = output_type
        self.location = location

    def __unicode__(self):
        return "Action '%s' expects %s output" % (
                self.action.name,
                self.get_output_type_display(), )

    def get_output_type_display(self):
        res = [x[1] for x in output_types.DETAILS if x[0] == self.output_type]
        if res:
            return res[0]


class Action(object):
    """ Represents one of a series of actions that may be performed after a commit.

    """
    def __init__(self, project, name, index, *arg, **kwarg):
        self.project = project
        self.name = name
        self.index = index
        self.outputs = {}

    def __unicode__(self):
        return "Action: %s" % self.name

    @property
    def statsd_name(self):
        return statsd_label_converter(self.name)

    def execute(self, stdoutlog, stderrlog, action_result):
        return NotImplemented

    def set_output(self, output):
        self.outputs[output.output_type] = output

    def fetch_output(self, o, sftp):
        return NotImplemented

    def as_form_data(self):
        output = {
                'id': self.id,
                'name': self.name,
                'project': self.project.id,
                'index': self.index,
                }
        for output_type, output_full_name in output_types.DETAILS:
            if output_type in output_types.IMPLICIT:
                continue
            output['output_' + output_type] = ''
            o = self.outputs.get(output_type)
            if o:
                output['output_' + output_type] = o.location
        return output

    def values_without_keys(self):
        data = dict(self.values)
        for k in ['public_key', 'private_key', 'response']:
            if k in data:
                del data[k]
        return data


class RemoteSSHAction(Action):
    """
    Run a command on a remote host.

    Output locations are presumed to be accessable via scp.

    scp -v -f -- src_file

    Output also includes ssh key pair to allow scp to work.

    TODO: There are some less than stellar security issues here:
    - the input from user is not sanitised, and it is used to
      construct entires for authorized_keys.
    - when executing the action, it auto accepts and allows unknown and
      missing host keys.
    - when we expect an 'output' file from the action, we need to relax
      the permissions on that host so that baleen has general shell access
      to the host. See the authorized_keys_entry property for more info and
      a possible way to restrict access while still allowing scp to function.
    """

    def __init__(self, project, name, index, *arg, **kwarg):
        super(RemoteSSHAction, self).__init__(project, name, index)

        self.username = kwarg.get('username')
        self.host = kwarg.get('host')
        self.command = kwarg.get('command')

        self.private_key, self.public_key = self.get_key_pair()

    def __unicode__(self):
        return "RemoteSSHAction: %s" % self.name

    def get_key_pair(self):
        from baleen.project.models import Credential

        name = '%s@%s' % (self.username, self.host)
        try:
            priv = Credential.objects.get(project=self.project, name=name + '_private')
            public = Credential.objects.get(project=self.project, name=name + '_public')
        except Credential.DoesNotExist:
            priv_key, public_key= generate_ssh_key()
            priv = Credential(project=self.project, name=name + '_private', value=priv_key)
            priv.save()
            public = Credential(project=self.project, name=name + '_public', value=public_key)
            public.save()
        return priv, public

    @property
    def authorized_keys_entry(self):
        # We limit this action to a single command on the destination
        # host.
        #
        # TODO Need to escape double quotes!
        action_command = '# ' + (self.name or '')
        action_command += '\ncommand="%s",' % self.command
        action_command += 'no-agent-forwarding,no-port-forwarding,no-pty,no-X11-forwarding %s' % self.public_key.value
        return action_command

    @property
    def host_address(self):
        """
        This is a wrapper to extract the current lxc container ip lease
        """
        if self.host and self.host.startswith('lxc:'):
            # This doesn't check that the LXC is actually running
            # Translate lxc name into ip addr
            lxc_name = self.host[(self.host.index(':') + 1):]
            p = subprocess.Popen(
                    "cat /var/lib/misc/dnsmasq.leases | grep ' %s ' | awk '{print $3}'" % lxc_name,
                    shell=True,
                    stdout=subprocess.PIPE
                    )
            stdout, stderr = p.communicate()
            if stdout:
                return stdout.strip()
        return self.host

    def execute(self, stdoutlog, stderrlog, action_result):
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        ssh.connect(
            self.host_address,
            username = self.username,
            pkey = paramiko.RSAKey.from_private_key(StringIO(self.private_key.value)),
            allow_agent = False,
            look_for_keys = False,
        )

        transport = ssh.get_transport()
        response = self._run_command(self.command, transport,
                stdoutlog, stderrlog,
                action_result)

        response['hooks'] = self.send_event_hooks(response['code'], transport)

        if len(self.outputs.keys()) > 0:
            sftp = paramiko.SFTPClient.from_transport(transport)
            response['output'] = {}
            for o in self.expectedactionoutput_set.all():
                response['output'][o.output_type] = self.fetch_output(o, sftp)

        ssh.close()

        return response

    def _copy_dir(self, sftp, src, dest):
        file_list = sftp.listdir(path=src)
        for f in file_list:
            src_f = os.path.join(src,f)
            dest_f = os.path.join(dest,f)
            if S_ISDIR(sftp.stat(src_f).st_mode):
                os.mkdir(os.path.join(dest,f))
                self._copy_dir(sftp, src_f, dest_f)
            sftp.get(remotepath=src_f, localpath=dest_f)

    def fetch_output(self, o, sftp):
        # Assume that default directory is home of the login user
        location = o.location.replace('~', sftp.normalize('.'))

        stat = sftp.stat(location)
        if not stat:
            return None

        if o.output_type == output_types.COVERAGE_HTML:
            assert S_ISDIR(stat.st_mode)
            dest = tempfile.mkdtemp(prefix=os.path.split(location)[-1], dir=settings.HTMLCOV_DIR)
            self._copy_dir(sftp, location, dest)
            # create an archive in LXC's temp directory.
            # Then the baleen webapp LXC uses watchdog to extract the archive to somewhere
            # the webapp can serve them from.

            # make staging dir if it doesn't exist, assumes worker will have permissions
            mkdir_p(settings.HTMLCOV_LXC_STAGING_DIR)
            # make archive
            archive_path = os.path.join(
                    settings.HTMLCOV_LXC_STAGING_DIR,
                    os.path.basename(dest) + ".tar.gz")
            make_tarfile(archive_path, dest)

            return os.path.split(dest)[-1]
        else:
            if S_ISDIR(stat.st_mode):
                return None
            # to copy file from remote to local
            f = sftp.open(location)
            content = f.read()
            f.close()
            return content

    def _run_command(self, command, transport, stdoutlog=None, stderrlog=None, action_result=None):
        response = {'stdout': '', 'stderr': '', 'code': None}

        chan = transport.open_session()
        chan.exec_command(command)

        buff_size = 1048576

        a_stdout = ActionOutput(action_result=action_result,
                output_type=output_types.STDOUT) if action_result else None
        a_stderr = ActionOutput(action_result=action_result,
                output_type=output_types.STDERR) if action_result else None

        def save_stream(data, action_output, log):
            if log:
                log.write(data)
                log.flush()
            if action_output:
                if action_output.output is None:
                    action_output.output = ''

                action_output.output += data
                action_output.save()
            return data

        while not chan.exit_status_ready():
            time.sleep(1)
            if chan.recv_ready():
                response['stdout'] += save_stream(chan.recv(buff_size), a_stdout, stdoutlog)
            if chan.recv_stderr_ready():
                response['stderr'] += save_stream(chan.recv_stderr(buff_size), a_stderr, stderrlog)

        # Read any remaining data in the streams
        while chan.recv_ready():
            response['stdout'] += save_stream(chan.recv(buff_size), a_stdout, stdoutlog)
        while chan.recv_stderr_ready():
            response['stderr'] += save_stream(chan.recv_stderr(buff_size), a_stderr, stderrlog)

        response['code'] = chan.recv_exit_status()
        return response

    def send_event_hooks(self, status_code, transport):
        event = {
            'type': 'action',
            'name': self.name,
            'status': status_code
        }
        gearman_client = gearman.GearmanClient([settings.GEARMAN_SERVER])
        gearman_client.submit_job(settings.GEARMAN_JOB_LABEL, json.dumps({'event': event}), background=True)

    def as_form_data(self):
        output = super(RemoteSSHAction, self).as_form_data()

        output.update({
                'username': self.username,
                'command': self.command,
                'host': self.host,
                'authorized_keys_entry': self.authorized_keys_entry,
                })
        return output


class FigAction(Action):

    def __init__(self, project, name, index, *arg, **kwarg):
        super(RemoteSSHAction, self).__init__(project, name, index)
        self.fig_file = kwarg.get('fig_file')

    def __unicode__(self):
        return "FigAction: %s" % self.name

    def execute(self, stdoutlog, stderrlog, action_result):
        pass


