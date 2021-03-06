# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Project'
        db.create_table(u'project_project', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=255)),
            ('site_url', self.gf('django.db.models.fields.URLField')(max_length=255, null=True, blank=True)),
            ('repo_url', self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True)),
            ('creator', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], null=True)),
            ('github_token', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('github_data_received', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('branch', self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True)),
            ('manual_config', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('public_key', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='public_key_for', null=True, on_delete=models.SET_NULL, to=orm['project.Credential'])),
            ('private_key', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='private_key_for', null=True, on_delete=models.SET_NULL, to=orm['project.Credential'])),
        ))
        db.send_create_signal(u'project', ['Project'])

        # Adding model 'Credential'
        db.create_table(u'project_credential', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('project', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['project.Project'], null=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], null=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('value', self.gf('django.db.models.fields.TextField')(max_length=255)),
            ('environment', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal(u'project', ['Credential'])

        # Adding unique constraint on 'Credential', fields ['project', 'name']
        db.create_unique(u'project_credential', ['project_id', 'name'])

        # Adding unique constraint on 'Credential', fields ['user', 'name']
        db.create_unique(u'project_credential', ['user_id', 'name'])

        # Adding model 'Hook'
        db.create_table(u'project_hook', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('project', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['project.Project'])),
            ('watch_for', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('email_user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], null=True, blank=True)),
            ('email_address', self.gf('django.db.models.fields.EmailField')(max_length=255, null=True, blank=True)),
            ('email_author', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('post_url', self.gf('django.db.models.fields.URLField')(default=None, max_length=200, null=True, blank=True)),
            ('trigger_build', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='triggered_by', null=True, to=orm['project.Project'])),
            ('one_off', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal(u'project', ['Hook'])

        # Adding model 'ActionResult'
        db.create_table(u'project_actionresult', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('action', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('action_slug', self.gf('django.db.models.fields.CharField')(max_length=255, blank=True)),
            ('index', self.gf('django.db.models.fields.IntegerField')()),
            ('started_at', self.gf('django.db.models.fields.DateTimeField')()),
            ('finished_at', self.gf('django.db.models.fields.DateTimeField')(null=True)),
            ('status_code', self.gf('django.db.models.fields.IntegerField')(null=True)),
            ('message', self.gf('django.db.models.fields.TextField')(blank=True)),
        ))
        db.send_create_signal(u'project', ['ActionResult'])


    def backwards(self, orm):
        # Removing unique constraint on 'Credential', fields ['user', 'name']
        db.delete_unique(u'project_credential', ['user_id', 'name'])

        # Removing unique constraint on 'Credential', fields ['project', 'name']
        db.delete_unique(u'project_credential', ['project_id', 'name'])

        # Deleting model 'Project'
        db.delete_table(u'project_project')

        # Deleting model 'Credential'
        db.delete_table(u'project_credential')

        # Deleting model 'Hook'
        db.delete_table(u'project_hook')

        # Deleting model 'ActionResult'
        db.delete_table(u'project_actionresult')


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Group']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Permission']"}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'project.actionresult': {
            'Meta': {'object_name': 'ActionResult'},
            'action': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'action_slug': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'finished_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'index': ('django.db.models.fields.IntegerField', [], {}),
            'message': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'started_at': ('django.db.models.fields.DateTimeField', [], {}),
            'status_code': ('django.db.models.fields.IntegerField', [], {'null': 'True'})
        },
        u'project.credential': {
            'Meta': {'unique_together': "(('project', 'name'), ('user', 'name'))", 'object_name': 'Credential'},
            'environment': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['project.Project']", 'null': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']", 'null': 'True'}),
            'value': ('django.db.models.fields.TextField', [], {'max_length': '255'})
        },
        u'project.hook': {
            'Meta': {'object_name': 'Hook'},
            'email_address': ('django.db.models.fields.EmailField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'email_author': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'email_user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'one_off': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'post_url': ('django.db.models.fields.URLField', [], {'default': 'None', 'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'project': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['project.Project']"}),
            'trigger_build': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'triggered_by'", 'null': 'True', 'to': u"orm['project.Project']"}),
            'watch_for': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        u'project.project': {
            'Meta': {'object_name': 'Project'},
            'branch': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'creator': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']", 'null': 'True'}),
            'github_data_received': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'github_token': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'manual_config': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'private_key': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'private_key_for'", 'null': 'True', 'on_delete': 'models.SET_NULL', 'to': u"orm['project.Credential']"}),
            'public_key': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'public_key_for'", 'null': 'True', 'on_delete': 'models.SET_NULL', 'to': u"orm['project.Credential']"}),
            'repo_url': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'site_url': ('django.db.models.fields.URLField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['project']