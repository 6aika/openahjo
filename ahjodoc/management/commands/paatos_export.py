# -*- coding: utf-8 -*-
import os
import logging
import json

from optparse import make_option
from django.core.management.base import BaseCommand
from django.db.models import FileField, ForeignKey, OneToOneField, ManyToManyField
from mptt.models import TreeForeignKey
from ahjodoc.models import *
from decisions.models import *


class Command(BaseCommand):
    help = "Export OpenAHJO data"
    option_list = BaseCommand.option_list + (
        make_option('--output', dest='output', help='output filename'),
        make_option('--prefetch', dest='prefetch', default=False, help='prefetch related models'),
    )

    def serialize_model(self, model, exclude_fields=None):
        self.logger.info('serializing %s (%d objects)... ' % (model.__name__, model.objects.count()))

        exclude_fields = exclude_fields or []
        all_fields = model._meta.fields + model._meta.many_to_many
        fields = [field for field in all_fields if field.name not in exclude_fields]
        objects = []

        if self.options['prefetch']:
            obj_qs = model.objects.prefetch_related(*(field.name for field in model._meta.many_to_many))
        else:
            obj_qs = model.objects.all()

        for obj in obj_qs:
            obj_data = {}

            for field in fields:
                if type(field) == FileField:
                    f = getattr(obj, field.name)
                    obj_data['url'] = f.url if f else ''
                    continue
                if type(field) in (ForeignKey, OneToOneField, TreeForeignKey):
                    value = getattr(obj, '%s_id' % field.name)
                    if value is not None:
                        value = unicode(value)
                elif type(field) == ManyToManyField:
                    value = [i.id for i in getattr(obj, field.name).all()]
                else:
                    value = getattr(obj, field.name)
                    if value is not None:
                        value = unicode(value)

                obj_data[field.name] = value
            objects.append(obj_data)

        return objects

    def handle(self, *args, **options):
        self.logger = logging.getLogger(__name__)
        self.data_path = os.path.join(settings.PROJECT_ROOT, 'data')

        self.options = options
        objects = {}

        self.logger.info('starting paatos export')

        objects['meetings'] = self.serialize_model(Meeting)
        objects['issue_geometries'] = self.serialize_model(IssueGeometry)
        objects['issues'] = self.serialize_model(Issue)
        objects['agenda_items'] = self.serialize_model(AgendaItem)
        objects['categories'] = self.serialize_model(Category, exclude_fields=['lft', 'rght', 'tree_id', 'level'])
        objects['content_sections'] = self.serialize_model(ContentSection)
        objects['policymakers'] = self.serialize_model(Policymaker)
        objects['organizations'] = self.serialize_model(Organization)
        objects['attachments'] = self.serialize_model(Attachment, exclude_fields=['hash'])

        self.logger.info('saving the file...')

        with open(self.options['output'], 'w') as f:
            f.write(json.dumps(objects))

        self.logger.info('paatos export done!')
