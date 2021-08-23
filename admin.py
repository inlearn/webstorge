from django.contrib import admin
from django.contrib.admin import register
from webstroge.models import FileInfo, FolderInfo


@register(FileInfo)
class FileInfoAdmin(admin.ModelAdmin):
    list_display = ['file_name', 'file_path']


@register(FolderInfo)
class FolderInfoAdmin(admin.ModelAdmin):
    list_display = ['belong_folder', 'folder_name']
