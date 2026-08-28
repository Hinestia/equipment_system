from django.contrib import admin
from .models import DocumentType, Document, DocumentEquipment


@admin.register(DocumentType)
class DocumentTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "template_filename", "number_prefix")


class DocumentEquipmentInline(admin.TabularInline):
    model = DocumentEquipment
    extra = 0


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("document_type", "number", "date_created")
    list_filter = ("document_type",)
    inlines = [DocumentEquipmentInline]
