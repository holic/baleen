import unittest

from StringIO import StringIO

from django.test import TestCase
from django.contrib.auth.models import User

from mock import Mock, patch

from baleen.action.ssh import RunCommandAction, FetchFileAction
from baleen.action.project import CreateAction

from baleen.action import (
        ExpectedActionOutput,
        ActionPlan,
        DockerActionPlan
        )

from baleen.project.models import Project, Hook
from baleen.job.models import Job
from baleen.artifact.models import output_types

class ActionPlanTest(TestCase):

    def setUp(self):
        self.project = Project(name='TestProject')
        self.project.save()
        self.action = RunCommandAction(project=self.project.name, index=0, name='TestAction',
                username='foo', command='echo "blah"')

        the_plan = ''
        self.job = Job(project=self.project, build_definition=the_plan)
        self.job.save()

    def test_job_action_plan(self):
        action_steps = self.job.action_plan()
        self.assertEqual(action_steps, [], 'no action steps for blank plan')

    def test_iterate_steps(self):
        ap = ActionPlan(self.job)
        ap.plan = [1, 2, 3]
        self.assertEqual([step for step in ap], [1, 2, 3])


class DockerActionPlanTest(TestCase):

    def setUp(self):
        self.project = Project(name='TestProject')
        self.project.save()
        self.action = RunCommandAction(project=self.project.name, index=0, name='TestAction',
                username='foo', command='echo "blah"')

    def create_plan(self, the_plan):
        self.job = Job(project=self.project, build_definition=the_plan)
        self.job.save()

    def user_and_login(self):
        self.user = User.objects.create_user('bob', 'bob@bob.com', 'bob')
        self.user.save()
        self.client.login(username='bob', password='bob')

    def test_formulate_blank_plan(self):
        self.create_plan('')
        ap = DockerActionPlan(self.job)
        action_steps = ap.formulate_plan()
        self.assertEqual(action_steps, [], 'no action steps for blank plan')

    @unittest.skip
    def test_formulate_plan(self):
        self.create_plan("""
depends:
    docker.example.com/db:
        src: git@github.com/docker-systems/example-db.git"
        minhash: "deedbeef"

build:
    docker.example.com/blah: .
"""
        )
        ap = DockerActionPlan(self.job)
        action_steps = ap.formulate_plan()
        # Will formulate plan to build dependency first.
        print action_steps
        self.assertEqual(action_steps, [
                {
                   'group': 'project',
                   'action': 'create',
                   'git': 'git@github.com/docker-systems/example-db.git',
                   'project': 'db'
                },
                {
                   'group': 'project',
                   'action': 'sync',
                   'project': 'db'
                },
                {
                   'group': 'project',
                   'action': 'build',
                   'project': 'db'
                }
                ], 'steps to build')
        # check that a Hook exists
        h = Hook.objects.get(trigger_build=self.project)
        self.assertTrue(h)


class ExpectedActionOutputTest(TestCase):

    def setUp(self):
        self.project = Project(name='TestProject')
        self.project.save()
        self.action = RunCommandAction(project=self.project.name, index=0, name='TestAction',
                username='foo', command='echo "blah"')

    def test_unicode(self):
        ea = ExpectedActionOutput(self.action, 'CH')
        self.assertEqual(unicode(ea), "Action 'TestAction' expects Coverage HTML report output")

    def test_output_type_display(self):
        ea = ExpectedActionOutput(self.action, 'CH')
        self.assertEqual(ea.get_output_type_display(), "Coverage HTML report")


class BaseActionTest(TestCase):

    def setUp(self):
        self.project = Project(name='TestProject')
        self.project.save()
        self.action = RunCommandAction(project=self.project.name, index=0, name='TestAction',
                username='foo', command='echo "blah"')

        self.user = User.objects.create_user('bob', 'bob@bob.com', 'bob')
        self.user.save()
        self.client.login(username='bob', password='bob')

class ActionTest(BaseActionTest):

    def test_statsd_name(self):
        self.assertEqual(self.action.statsd_name, 'testaction')
        self.action.name = 'test*(&#$*&*(@$#'
        self.assertEqual(self.action.statsd_name, 'test')
        self.action.name = 'test something    now'
        self.assertEqual(self.action.statsd_name, 'test_something_now')

    def test_get_action_object(self):
        from baleen.action.dispatch import get_action_object
        action = get_action_object({
            'group': 'project',
            'action': 'create',
            'project': 'TestProject',
            'name': 'build project',
            'index': 0
            })
        self.assertTrue(isinstance(action, CreateAction))


class RunCommandActionTest(BaseActionTest):

    def test_authorized_keys_entry(self):
        keys = self.action.authorized_keys_entry
        self.assertTrue('no-agent-forwarding' in keys)

        self.action.set_output(ExpectedActionOutput(self.action, output_types.XUNIT, 'here'))
        keys = self.action.authorized_keys_entry
        self.assertEqual(keys.split('\n')[0], '# TestAction')


    @patch('paramiko.SSHClient')
    @patch('paramiko.SFTPClient')
    @patch('gearman.GearmanClient')
    @patch('baleen.action.ssh.RunCommandAction._run_command')
    def test_execute(self, run_mock, gearman_mock, sftp_mock, ssh_mock):
        stdout = StringIO()
        stderr = StringIO()
        run_mock.return_value = {'code': 0}

        self.action.execute(stdout, stderr, None)

        ExpectedActionOutput(action=self.action, output_type=output_types.XUNIT, location='xunit.xml')

        self.action.execute(stdout, stderr, None)

    def test_run_command(self):
        stdout = StringIO()
        stderr = StringIO()
        m = Mock()
        chan = Mock()

        m.open_session.return_value = chan
        chan.exit_status_ready.side_effect = [False, False, True]
        chan.recv.side_effect = ['blah', 'blah']
        chan.recv_ready.side_effect = [True, True, False]
        chan.recv_stderr.side_effect = ['argh', 'argh', 'argh']
        chan.recv_stderr_ready.side_effect = [True, True, True, False]

        self.action._run_command('test', m, stdout, stderr)

        self.assertEqual(stdout.getvalue(), 'blah'*2)
        self.assertEqual(stderr.getvalue(), 'argh'*3)


class FetchFileActionTest(BaseActionTest):

    def setUp(self):
        super(FetchFileActionTest, self).setUp()
        self.action = FetchFileAction(project=self.project.name, index=0, name='TestAction',
                username='foo', path='/rightnow')

        self.dir_action = FetchFileAction(project=self.project.name, index=0, name='TestAction',
                username='foo', path='/rightnow/', is_dir=True)

    @patch('baleen.action.ssh.S_ISDIR')
    @patch('baleen.action.ssh.tempfile')
    def test_fetch_output(self, tempfile_mock, ISDIR):
        sftp_mock = Mock()
        sftp_mock.normalize.return_value = 'robots'
        tempfile_mock.mkdtemp.return_value = 'blahtempdir'
        path = '/rightnow'

        ISDIR.return_value = False
        self.assertEqual(self.action.fetch_output(path, False, sftp_mock), 'blahtempdir/rightnow')

        sftp_mock.stat.return_value = None
        self.assertEqual(self.action.fetch_output(path, False, sftp_mock), None)

    @patch('baleen.action.ssh.S_ISDIR')
    @patch('os.mkdir')
    def test_copy_dir(self, mkdir, ISDIR):
        sftp_mock = Mock()
        sftp_mock.listdir.return_value = ['file1', 'file2']
        ISDIR.return_value = False
        self.action._copy_dir(sftp_mock, 'a', 'b')
        self.assertTrue(sftp_mock.get.called)

    @patch('baleen.action.ssh.S_ISDIR')
    @patch('os.mkdir')
    def test_fetch_dir(self, mkdir, ISDIR):
        sftp_mock = Mock()
        sftp_mock.normalize.return_value = 'robots'
        sftp_mock.listdir.return_value = ['file1', 'file2']
        path = '/rightnow'

        ISDIR.return_value = False
        with self.assertRaises(AssertionError):
            self.action.fetch_output(path, True, sftp_mock)

        ISDIR.side_effect = [True, True, False, False, False]
        self.assertTrue(self.action.fetch_output(path, True, sftp_mock).startswith(
                '/usr/local/baleen/baleen/../build_artifacts/rightnow'))


class TestWithFigActionTest(BaseActionTest):

    def setUp(self):
        super(TestWithFigActionTest, self).setUp()
        self.action = TestWithFigActionTest(project=self.project.name, index=0, name='TestAction',
                username='foo', path='/rightnow')