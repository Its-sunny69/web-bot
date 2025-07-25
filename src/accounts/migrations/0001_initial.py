# Generated by Django 5.2.4 on 2025-07-13 09:36

import django.contrib.auth.models
import django.contrib.auth.validators
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('is_superuser', models.BooleanField(default=False, help_text='Designates that this user has all permissions without explicitly assigning them.', verbose_name='superuser status')),
                ('username', models.CharField(error_messages={'unique': 'A user with that username already exists.'}, help_text='Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.', max_length=150, unique=True, validators=[django.contrib.auth.validators.UnicodeUsernameValidator()], verbose_name='username')),
                ('first_name', models.CharField(blank=True, max_length=150, verbose_name='first name')),
                ('last_name', models.CharField(blank=True, max_length=150, verbose_name='last name')),
                ('email', models.EmailField(blank=True, max_length=254, verbose_name='email address')),
                ('is_staff', models.BooleanField(default=False, help_text='Designates whether the user can log into this admin site.', verbose_name='staff status')),
                ('is_active', models.BooleanField(default=True, help_text='Designates whether this user should be treated as active. Unselect this instead of deleting accounts.', verbose_name='active')),
                ('date_joined', models.DateTimeField(default=django.utils.timezone.now, verbose_name='date joined')),
                ('github_id', models.BigIntegerField(unique=True)),
                ('chat_id', models.BigIntegerField(blank=True, null=True)),
                ('github_login', models.CharField(max_length=255)),
                ('avatar', models.URLField(blank=True, null=True)),
                ('access_token', models.CharField(max_length=255)),
                ('sso_token_expiry', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('bio', models.TextField(blank=True, null=True)),
                ('public_repos', models.IntegerField(default=0)),
                ('followers', models.IntegerField(default=0)),
                ('following', models.IntegerField(default=0)),
                ('groups', models.ManyToManyField(blank=True, help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.', related_name='user_set', related_query_name='user', to='auth.group', verbose_name='groups')),
                ('user_permissions', models.ManyToManyField(blank=True, help_text='Specific permissions for this user.', related_name='user_set', related_query_name='user', to='auth.permission', verbose_name='user permissions')),
            ],
            options={
                'verbose_name': 'user',
                'verbose_name_plural': 'users',
                'abstract': False,
            },
            managers=[
                ('objects', django.contrib.auth.models.UserManager()),
            ],
        ),
        migrations.CreateModel(
            name='Repository',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('repo_id', models.BigIntegerField(unique=True)),
                ('node_id', models.CharField(max_length=50)),
                ('name', models.CharField(max_length=255)),
                ('full_name', models.CharField(max_length=255)),
                ('private', models.BooleanField(default=False)),
                ('description', models.TextField(blank=True, null=True)),
                ('fork', models.BooleanField(default=False)),
                ('url', models.URLField()),
                ('html_url', models.URLField()),
                ('git_url', models.URLField()),
                ('ssh_url', models.URLField()),
                ('clone_url', models.URLField()),
                ('svn_url', models.URLField()),
                ('homepage', models.URLField(blank=True, null=True)),
                ('size', models.BigIntegerField(default=0)),
                ('stargazers_count', models.IntegerField(default=0)),
                ('watchers_count', models.IntegerField(default=0)),
                ('language', models.CharField(blank=True, max_length=100, null=True)),
                ('has_issues', models.BooleanField(default=True)),
                ('has_projects', models.BooleanField(default=True)),
                ('has_downloads', models.BooleanField(default=True)),
                ('has_wiki', models.BooleanField(default=True)),
                ('has_pages', models.BooleanField(default=False)),
                ('has_discussions', models.BooleanField(default=False)),
                ('forks_count', models.IntegerField(default=0)),
                ('mirror_url', models.URLField(blank=True, null=True)),
                ('archived', models.BooleanField(default=False)),
                ('disabled', models.BooleanField(default=False)),
                ('open_issues_count', models.IntegerField(default=0)),
                ('allow_forking', models.BooleanField(default=True)),
                ('is_template', models.BooleanField(default=False)),
                ('web_commit_signoff_required', models.BooleanField(default=False)),
                ('visibility', models.CharField(choices=[('public', 'Public'), ('private', 'Private')], default='public', max_length=10)),
                ('default_branch', models.CharField(max_length=100)),
                ('created_at', models.DateTimeField()),
                ('updated_at', models.DateTimeField()),
                ('pushed_at', models.DateTimeField()),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='repositories', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name_plural': 'Repositories',
                'ordering': ['-pushed_at'],
            },
        ),
        migrations.CreateModel(
            name='License',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('key', models.CharField(max_length=100)),
                ('name', models.CharField(max_length=255)),
                ('spdx_id', models.CharField(max_length=100)),
                ('url', models.URLField(blank=True, null=True)),
                ('node_id', models.CharField(max_length=50)),
                ('repository', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='license', to='accounts.repository')),
            ],
        ),
        migrations.CreateModel(
            name='RepositoryPermission',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('admin', models.BooleanField(default=False)),
                ('maintain', models.BooleanField(default=False)),
                ('push', models.BooleanField(default=False)),
                ('triage', models.BooleanField(default=False)),
                ('pull', models.BooleanField(default=True)),
                ('repository', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='permissions', to='accounts.repository')),
            ],
        ),
        migrations.CreateModel(
            name='Topic',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
                ('repositories', models.ManyToManyField(related_name='topics', to='accounts.repository')),
            ],
        ),
        migrations.CreateModel(
            name='Branch',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('protected', models.BooleanField(default=False)),
                ('last_commit_sha', models.CharField(max_length=40)),
                ('last_commit_url', models.URLField()),
                ('repository', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='branches', to='accounts.repository')),
            ],
            options={
                'verbose_name_plural': 'Branches',
                'unique_together': {('repository', 'name')},
            },
        ),
    ]
