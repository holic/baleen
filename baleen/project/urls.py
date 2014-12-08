from django.conf.urls import patterns, url

urlpatterns = patterns('',
    url(r'^$', 'baleen.project.views.index', name='project_index'),
    url(r'^add$', 'baleen.project.views.add', name='add_project'),
    url(r'^(?P<project_id>\d+)$', 'baleen.project.views.show', name='show_project'),
    url(r'^(?P<project_id>\d+)/deploy$', 'baleen.project.views.manual_deploy', name='manual_deploy'),

    url(r'^(?P<project_id>\d+)/action$', 'baleen.project.views.add_action', name='add_action'),
    url(r'^(?P<project_id>\d+)/action/(?P<action_id>\d+)$',
        'baleen.project.views.edit_action', name='edit_action'),
    url(r'^(?P<project_id>\d+)/action-order$',
        'baleen.project.views.set_action_order', name='set_action_order'),
)

urlpatterns += patterns('',
    url(r'^(?P<project_id>\d+)/job/(?P<job_id>\d+)$',
        'baleen.job.views.view_job', name='view_job'),
    url(r'^(?P<project_id>\d+)/job/(?P<job_id>\d+)/done$',
        'baleen.job.views.mark_job_done', name='mark_job_done'),

    url(r'^(?P<project_id>\d+)/job/(?P<job_id>\d+)/htmlcov/(?P<filename>.+)$',
        'baleen.job.views.view_html_coverage', name='view_html_coverage'),
    url(r'^(?P<project_id>\d+)/job/(?P<job_id>\d+)/(?P<action_id>\d+)/htmlcov/(?P<filename>.+)$',
        'baleen.job.views.view_specific_action_html_coverage',
        name='view_specific_action_html_coverage'),
)
