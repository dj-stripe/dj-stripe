# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

try:
    from django.contrib.auth import get_user_model
except ImportError:  # django < 1.5
    from django.contrib.auth.models import User
else:
    User = get_user_model()


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'EventProcessingException'
        db.create_table(u'djstripe_eventprocessingexception', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('model_utils.fields.AutoCreatedField')(default=datetime.datetime.now)),
            ('modified', self.gf('model_utils.fields.AutoLastModifiedField')(default=datetime.datetime.now)),
            ('event', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['djstripe.Event'], null=True)),
            ('data', self.gf('django.db.models.fields.TextField')()),
            ('message', self.gf('django.db.models.fields.CharField')(max_length=500)),
            ('traceback', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal(u'djstripe', ['EventProcessingException'])

        # Adding model 'Event'
        db.create_table(u'djstripe_event', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('model_utils.fields.AutoCreatedField')(default=datetime.datetime.now)),
            ('modified', self.gf('model_utils.fields.AutoLastModifiedField')(default=datetime.datetime.now)),
            ('stripe_id', self.gf('django.db.models.fields.CharField')(unique=True, max_length=50)),
            ('kind', self.gf('django.db.models.fields.CharField')(max_length=250)),
            ('livemode', self.gf('django.db.models.fields.BooleanField')()),
            ('customer', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['djstripe.Customer'], null=True)),
            ('webhook_message', self.gf('jsonfield.fields.JSONField')(default={})),
            ('validated_message', self.gf('jsonfield.fields.JSONField')(null=True)),
            ('valid', self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True)),
            ('processed', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal(u'djstripe', ['Event'])

        # Adding model 'Transfer'
        db.create_table(u'djstripe_transfer', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('model_utils.fields.AutoCreatedField')(default=datetime.datetime.now)),
            ('modified', self.gf('model_utils.fields.AutoLastModifiedField')(default=datetime.datetime.now)),
            ('stripe_id', self.gf('django.db.models.fields.CharField')(unique=True, max_length=50)),
            ('event', self.gf('django.db.models.fields.related.ForeignKey')(related_name=u'transfers', to=orm['djstripe.Event'])),
            ('amount', self.gf('django.db.models.fields.DecimalField')(max_digits=7, decimal_places=2)),
            ('status', self.gf('django.db.models.fields.CharField')(max_length=25)),
            ('date', self.gf('django.db.models.fields.DateTimeField')()),
            ('description', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('adjustment_count', self.gf('django.db.models.fields.IntegerField')()),
            ('adjustment_fees', self.gf('django.db.models.fields.DecimalField')(max_digits=7, decimal_places=2)),
            ('adjustment_gross', self.gf('django.db.models.fields.DecimalField')(max_digits=7, decimal_places=2)),
            ('charge_count', self.gf('django.db.models.fields.IntegerField')()),
            ('charge_fees', self.gf('django.db.models.fields.DecimalField')(max_digits=7, decimal_places=2)),
            ('charge_gross', self.gf('django.db.models.fields.DecimalField')(max_digits=7, decimal_places=2)),
            ('collected_fee_count', self.gf('django.db.models.fields.IntegerField')()),
            ('collected_fee_gross', self.gf('django.db.models.fields.DecimalField')(max_digits=7, decimal_places=2)),
            ('net', self.gf('django.db.models.fields.DecimalField')(max_digits=7, decimal_places=2)),
            ('refund_count', self.gf('django.db.models.fields.IntegerField')()),
            ('refund_fees', self.gf('django.db.models.fields.DecimalField')(max_digits=7, decimal_places=2)),
            ('refund_gross', self.gf('django.db.models.fields.DecimalField')(max_digits=7, decimal_places=2)),
            ('validation_count', self.gf('django.db.models.fields.IntegerField')()),
            ('validation_fees', self.gf('django.db.models.fields.DecimalField')(max_digits=7, decimal_places=2)),
        ))
        db.send_create_signal(u'djstripe', ['Transfer'])

        # Adding model 'TransferChargeFee'
        db.create_table(u'djstripe_transferchargefee', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('model_utils.fields.AutoCreatedField')(default=datetime.datetime.now)),
            ('modified', self.gf('model_utils.fields.AutoLastModifiedField')(default=datetime.datetime.now)),
            ('transfer', self.gf('django.db.models.fields.related.ForeignKey')(related_name=u'charge_fee_details', to=orm['djstripe.Transfer'])),
            ('amount', self.gf('django.db.models.fields.DecimalField')(max_digits=7, decimal_places=2)),
            ('application', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('description', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('kind', self.gf('django.db.models.fields.CharField')(max_length=150)),
        ))
        db.send_create_signal(u'djstripe', ['TransferChargeFee'])

        # Adding model 'Customer'
        db.create_table(u'djstripe_customer', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('model_utils.fields.AutoCreatedField')(default=datetime.datetime.now)),
            ('modified', self.gf('model_utils.fields.AutoLastModifiedField')(default=datetime.datetime.now)),
            ('stripe_id', self.gf('django.db.models.fields.CharField')(unique=True, max_length=50)),
            ('user', self.gf('django.db.models.fields.related.OneToOneField')(to=User, unique=True, null=True)),
            ('card_fingerprint', self.gf('django.db.models.fields.CharField')(max_length=200, blank=True)),
            ('card_last_4', self.gf('django.db.models.fields.CharField')(max_length=4, blank=True)),
            ('card_kind', self.gf('django.db.models.fields.CharField')(max_length=50, blank=True)),
            ('date_purged', self.gf('django.db.models.fields.DateTimeField')(null=True)),
        ))
        db.send_create_signal(u'djstripe', ['Customer'])

        # Adding model 'CurrentSubscription'
        db.create_table(u'djstripe_currentsubscription', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('model_utils.fields.AutoCreatedField')(default=datetime.datetime.now)),
            ('modified', self.gf('model_utils.fields.AutoLastModifiedField')(default=datetime.datetime.now)),
            ('customer', self.gf('django.db.models.fields.related.OneToOneField')(related_name=u'current_subscription', unique=True, null=True, to=orm['djstripe.Customer'])),
            ('plan', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('quantity', self.gf('django.db.models.fields.IntegerField')()),
            ('start', self.gf('django.db.models.fields.DateTimeField')()),
            ('status', self.gf('django.db.models.fields.CharField')(max_length=25)),
            ('canceled_at', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('current_period_end', self.gf('django.db.models.fields.DateTimeField')(null=True)),
            ('current_period_start', self.gf('django.db.models.fields.DateTimeField')(null=True)),
            ('ended_at', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('trial_end', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('trial_start', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('amount', self.gf('django.db.models.fields.DecimalField')(max_digits=7, decimal_places=2)),
        ))
        db.send_create_signal(u'djstripe', ['CurrentSubscription'])

        # Adding model 'Invoice'
        db.create_table(u'djstripe_invoice', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('model_utils.fields.AutoCreatedField')(default=datetime.datetime.now)),
            ('modified', self.gf('model_utils.fields.AutoLastModifiedField')(default=datetime.datetime.now)),
            ('stripe_id', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('customer', self.gf('django.db.models.fields.related.ForeignKey')(related_name=u'invoices', to=orm['djstripe.Customer'])),
            ('attempted', self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True)),
            ('attempts', self.gf('django.db.models.fields.PositiveIntegerField')(null=True)),
            ('closed', self.gf('django.db.models.fields.BooleanField')()),
            ('paid', self.gf('django.db.models.fields.BooleanField')()),
            ('period_end', self.gf('django.db.models.fields.DateTimeField')()),
            ('period_start', self.gf('django.db.models.fields.DateTimeField')()),
            ('subtotal', self.gf('django.db.models.fields.DecimalField')(max_digits=7, decimal_places=2)),
            ('total', self.gf('django.db.models.fields.DecimalField')(max_digits=7, decimal_places=2)),
            ('date', self.gf('django.db.models.fields.DateTimeField')()),
            ('charge', self.gf('django.db.models.fields.CharField')(max_length=50, blank=True)),
        ))
        db.send_create_signal(u'djstripe', ['Invoice'])

        # Adding model 'InvoiceItem'
        db.create_table(u'djstripe_invoiceitem', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('model_utils.fields.AutoCreatedField')(default=datetime.datetime.now)),
            ('modified', self.gf('model_utils.fields.AutoLastModifiedField')(default=datetime.datetime.now)),
            ('stripe_id', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('invoice', self.gf('django.db.models.fields.related.ForeignKey')(related_name=u'items', to=orm['djstripe.Invoice'])),
            ('amount', self.gf('django.db.models.fields.DecimalField')(max_digits=7, decimal_places=2)),
            ('currency', self.gf('django.db.models.fields.CharField')(max_length=10)),
            ('period_start', self.gf('django.db.models.fields.DateTimeField')()),
            ('period_end', self.gf('django.db.models.fields.DateTimeField')()),
            ('proration', self.gf('django.db.models.fields.BooleanField')()),
            ('line_type', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('description', self.gf('django.db.models.fields.CharField')(max_length=200, blank=True)),
            ('plan', self.gf('django.db.models.fields.CharField')(max_length=100, blank=True)),
            ('quantity', self.gf('django.db.models.fields.IntegerField')(null=True)),
        ))
        db.send_create_signal(u'djstripe', ['InvoiceItem'])

        # Adding model 'Charge'
        db.create_table(u'djstripe_charge', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('model_utils.fields.AutoCreatedField')(default=datetime.datetime.now)),
            ('modified', self.gf('model_utils.fields.AutoLastModifiedField')(default=datetime.datetime.now)),
            ('stripe_id', self.gf('django.db.models.fields.CharField')(unique=True, max_length=50)),
            ('customer', self.gf('django.db.models.fields.related.ForeignKey')(related_name=u'charges', to=orm['djstripe.Customer'])),
            ('invoice', self.gf('django.db.models.fields.related.ForeignKey')(related_name=u'charges', null=True, to=orm['djstripe.Invoice'])),
            ('card_last_4', self.gf('django.db.models.fields.CharField')(max_length=4, blank=True)),
            ('card_kind', self.gf('django.db.models.fields.CharField')(max_length=50, blank=True)),
            ('amount', self.gf('django.db.models.fields.DecimalField')(null=True, max_digits=7, decimal_places=2)),
            ('amount_refunded', self.gf('django.db.models.fields.DecimalField')(null=True, max_digits=7, decimal_places=2)),
            ('description', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('paid', self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True)),
            ('disputed', self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True)),
            ('refunded', self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True)),
            ('fee', self.gf('django.db.models.fields.DecimalField')(null=True, max_digits=7, decimal_places=2)),
            ('receipt_sent', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('charge_created', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
        ))
        db.send_create_signal(u'djstripe', ['Charge'])


    def backwards(self, orm):
        # Deleting model 'EventProcessingException'
        db.delete_table(u'djstripe_eventprocessingexception')

        # Deleting model 'Event'
        db.delete_table(u'djstripe_event')

        # Deleting model 'Transfer'
        db.delete_table(u'djstripe_transfer')

        # Deleting model 'TransferChargeFee'
        db.delete_table(u'djstripe_transferchargefee')

        # Deleting model 'Customer'
        db.delete_table(u'djstripe_customer')

        # Deleting model 'CurrentSubscription'
        db.delete_table(u'djstripe_currentsubscription')

        # Deleting model 'Invoice'
        db.delete_table(u'djstripe_invoice')

        # Deleting model 'InvoiceItem'
        db.delete_table(u'djstripe_invoiceitem')

        # Deleting model 'Charge'
        db.delete_table(u'djstripe_charge')


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
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'djstripe.charge': {
            'Meta': {'object_name': 'Charge'},
            'amount': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '7', 'decimal_places': '2'}),
            'amount_refunded': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '7', 'decimal_places': '2'}),
            'card_kind': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'card_last_4': ('django.db.models.fields.CharField', [], {'max_length': '4', 'blank': 'True'}),
            'charge_created': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'customer': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "u'charges'", 'to': u"orm['djstripe.Customer']"}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'disputed': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'fee': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '7', 'decimal_places': '2'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'invoice': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "u'charges'", 'null': 'True', 'to': u"orm['djstripe.Invoice']"}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'paid': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'receipt_sent': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'refunded': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'stripe_id': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '50'})
        },
        u'djstripe.currentsubscription': {
            'Meta': {'object_name': 'CurrentSubscription'},
            'amount': ('django.db.models.fields.DecimalField', [], {'max_digits': '7', 'decimal_places': '2'}),
            'canceled_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'current_period_end': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'current_period_start': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'customer': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "u'current_subscription'", 'unique': 'True', 'null': 'True', 'to': u"orm['djstripe.Customer']"}),
            'ended_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'plan': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'quantity': ('django.db.models.fields.IntegerField', [], {}),
            'start': ('django.db.models.fields.DateTimeField', [], {}),
            'status': ('django.db.models.fields.CharField', [], {'max_length': '25'}),
            'trial_end': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'trial_start': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'})
        },
        u'djstripe.customer': {
            'Meta': {'object_name': 'Customer'},
            'card_fingerprint': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'card_kind': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'card_last_4': ('django.db.models.fields.CharField', [], {'max_length': '4', 'blank': 'True'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'date_purged': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'stripe_id': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '50'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['users.User']", 'unique': 'True', 'null': 'True'})
        },
        u'djstripe.event': {
            'Meta': {'object_name': 'Event'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'customer': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['djstripe.Customer']", 'null': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '250'}),
            'livemode': ('django.db.models.fields.BooleanField', [], {}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'processed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'stripe_id': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '50'}),
            'valid': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'validated_message': ('jsonfield.fields.JSONField', [], {'null': 'True'}),
            'webhook_message': ('jsonfield.fields.JSONField', [], {'default': '{}'})
        },
        u'djstripe.eventprocessingexception': {
            'Meta': {'object_name': 'EventProcessingException'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'data': ('django.db.models.fields.TextField', [], {}),
            'event': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['djstripe.Event']", 'null': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'message': ('django.db.models.fields.CharField', [], {'max_length': '500'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'traceback': ('django.db.models.fields.TextField', [], {})
        },
        u'djstripe.invoice': {
            'Meta': {'ordering': "[u'-date']", 'object_name': 'Invoice'},
            'attempted': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'attempts': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True'}),
            'charge': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'closed': ('django.db.models.fields.BooleanField', [], {}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'customer': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "u'invoices'", 'to': u"orm['djstripe.Customer']"}),
            'date': ('django.db.models.fields.DateTimeField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'paid': ('django.db.models.fields.BooleanField', [], {}),
            'period_end': ('django.db.models.fields.DateTimeField', [], {}),
            'period_start': ('django.db.models.fields.DateTimeField', [], {}),
            'stripe_id': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'subtotal': ('django.db.models.fields.DecimalField', [], {'max_digits': '7', 'decimal_places': '2'}),
            'total': ('django.db.models.fields.DecimalField', [], {'max_digits': '7', 'decimal_places': '2'})
        },
        u'djstripe.invoiceitem': {
            'Meta': {'object_name': 'InvoiceItem'},
            'amount': ('django.db.models.fields.DecimalField', [], {'max_digits': '7', 'decimal_places': '2'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'currency': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'invoice': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "u'items'", 'to': u"orm['djstripe.Invoice']"}),
            'line_type': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'period_end': ('django.db.models.fields.DateTimeField', [], {}),
            'period_start': ('django.db.models.fields.DateTimeField', [], {}),
            'plan': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'proration': ('django.db.models.fields.BooleanField', [], {}),
            'quantity': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'stripe_id': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'djstripe.transfer': {
            'Meta': {'object_name': 'Transfer'},
            'adjustment_count': ('django.db.models.fields.IntegerField', [], {}),
            'adjustment_fees': ('django.db.models.fields.DecimalField', [], {'max_digits': '7', 'decimal_places': '2'}),
            'adjustment_gross': ('django.db.models.fields.DecimalField', [], {'max_digits': '7', 'decimal_places': '2'}),
            'amount': ('django.db.models.fields.DecimalField', [], {'max_digits': '7', 'decimal_places': '2'}),
            'charge_count': ('django.db.models.fields.IntegerField', [], {}),
            'charge_fees': ('django.db.models.fields.DecimalField', [], {'max_digits': '7', 'decimal_places': '2'}),
            'charge_gross': ('django.db.models.fields.DecimalField', [], {'max_digits': '7', 'decimal_places': '2'}),
            'collected_fee_count': ('django.db.models.fields.IntegerField', [], {}),
            'collected_fee_gross': ('django.db.models.fields.DecimalField', [], {'max_digits': '7', 'decimal_places': '2'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'date': ('django.db.models.fields.DateTimeField', [], {}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'event': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "u'transfers'", 'to': u"orm['djstripe.Event']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'net': ('django.db.models.fields.DecimalField', [], {'max_digits': '7', 'decimal_places': '2'}),
            'refund_count': ('django.db.models.fields.IntegerField', [], {}),
            'refund_fees': ('django.db.models.fields.DecimalField', [], {'max_digits': '7', 'decimal_places': '2'}),
            'refund_gross': ('django.db.models.fields.DecimalField', [], {'max_digits': '7', 'decimal_places': '2'}),
            'status': ('django.db.models.fields.CharField', [], {'max_length': '25'}),
            'stripe_id': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '50'}),
            'validation_count': ('django.db.models.fields.IntegerField', [], {}),
            'validation_fees': ('django.db.models.fields.DecimalField', [], {'max_digits': '7', 'decimal_places': '2'})
        },
        u'djstripe.transferchargefee': {
            'Meta': {'object_name': 'TransferChargeFee'},
            'amount': ('django.db.models.fields.DecimalField', [], {'max_digits': '7', 'decimal_places': '2'}),
            'application': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'kind': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'transfer': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "u'charge_fee_details'", 'to': u"orm['djstripe.Transfer']"})
        },
        u'users.user': {
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
            'location': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'tagline': ('django.db.models.fields.CharField', [], {'max_length': '176', 'blank': 'True'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Permission']"}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        }
    }

    complete_apps = ['djstripe']